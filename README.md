# IP Address Tracker

A Flask application that records visitor metadata, performs GeoIP lookups, classifies bots vs human traffic, and redirects requests to a configured destination. A local dashboard (`/dashboard`) provides searchable visibility into collected logs.

## Features

- Captures IP, timestamp, referrer, user agent, and screen resolution
- Enriches logs with GeoLite2 city and ASN data (country, city, coordinates, ASN, organization)
- Classifies visitors as `human` or `crawler`
- Stores logs in `visitor_logs.json`
- Exposes a local dashboard and JSON API (`/api/logs`) for analysis
- Uses ngrok for public tunnel access during testing

## Tech Stack

- Python 3
- Flask
- pyngrok
- geoip2
- python-dotenv
- user-agents

## Quick Start

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Copy `.env.example` to `.env` and fill in required values.
4. Run the app:

```bash
python ip_tracker.py
```

5. Open `http://localhost:5000/dashboard` locally to view logs.

## Configuration

Environment variables used by the application:

- `NGROK_AUTH_TOKEN` (required): ngrok auth token
- `GOOGLE_MAPS_API_KEY` (optional): dashboard map rendering
- `REDIRECT_URL` (optional, default `https://www.google.com/`): destination for tracked traffic
- `PORT` (optional, default `5000`): Flask/ngrok port
- `REQUEST_LOGGING_ENABLED` (optional, default `false`): emits minimal request metadata logs
- `DATA_DIR` (optional, default `.`): directory where `visitor_logs.json` is stored
- `GEOIP_DIR` (optional, default `GeoLite2-City_20250528`): directory containing GeoLite2 databases

## Included Data Files

This repository currently includes a GeoLite2 database directory:

- `GeoLite2-City_20250528/GeoLite2-City.mmdb`
- `GeoLite2-City_20250528/GeoLite2-ASN.mmdb`

Related license and attribution files are included:

- `GeoLite2-City_20250528/LICENSE.txt`
- `GeoLite2-City_20250528/COPYRIGHT.txt`
- `GeoLite2-City_20250528/README.txt`

## Utilities

- `update_logs.py`: backfill structured user-agent fields in existing logs
  - Example: `python update_logs.py --log-file visitor_logs.json`
- `geoip_lookup.py`: run a one-off GeoLite2 city lookup for an IP
  - Example: `python geoip_lookup.py --ip 8.8.8.8`

## Security and Privacy Notes

- Do not commit `.env` files, credentials, or raw visitor logs.
- The dashboard and logs API are restricted to localhost access.
- This project processes request metadata; ensure your use complies with applicable laws, policies, and consent requirements.

## Suggested Public Release Checklist

- Review commit history for previously committed secrets
- Confirm `.env`, local logs, and temporary files are excluded by `.gitignore`
- Verify any deployed redirect target is legitimate and expected
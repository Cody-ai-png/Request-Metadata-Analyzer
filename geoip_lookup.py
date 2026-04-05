import argparse
from pathlib import Path

import geoip2.database


def lookup_ip(db_path: Path, ip_address: str):
    with geoip2.database.Reader(str(db_path)) as reader:
        response = reader.city(ip_address)

    print(f"IP: {ip_address}")
    print(f"Country: {response.country.name}")
    print(f"City: {response.city.name}")
    print(f"Latitude: {response.location.latitude}")
    print(f"Longitude: {response.location.longitude}")


def main():
    parser = argparse.ArgumentParser(description='Run a quick GeoLite2 city lookup for a single IP address.')
    parser.add_argument('--ip', default='103.100.225.138', help='IP address to query.')
    parser.add_argument(
        '--db-path',
        default='GeoLite2-City_20250528/GeoLite2-City.mmdb',
        help='Path to GeoLite2 City database file.'
    )
    args = parser.parse_args()

    db_path = Path(args.db_path)
    if not db_path.exists():
        raise FileNotFoundError(f"GeoIP database file not found: {db_path}")

    lookup_ip(db_path, args.ip)


if __name__ == '__main__':
    main()

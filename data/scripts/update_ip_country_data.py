#!/usr/bin/env python3
# COPYRIGHT (C) 2024 Nicotine+ Contributors
#
# GNU GENERAL PUBLIC LICENSE
#    Version 3, 29 June 2007
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import csv
import io
import os
import time
import urllib.request
import zipfile

COUNTRY_DATA_URL = "https://download.ip2location.com/lite/IP2LOCATION-LITE-DB1.CSV.ZIP"
COPYRIGHT_PREFIX = b"Copyright (c)"
PRODUCT_NAME = "IP2Location LITE"
EXPECTED_COPYRIGHT_AUTHOR = b"Hexasoft Development"
EXPECTED_LICENSE = b"Creative Commons Attribution-ShareAlike 4.0 International"
MAX_IPV4_RANGE = 4294967295
MAX_RESPONSE_BYTES = 5000000
BASE_PATH = os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", ".."))
DATA_PATH = os.path.join(BASE_PATH, "pynicotine", "external", "data")


def parse_ip_country_data():
    """Download and parse country data."""

    file_path, headers = urllib.request.urlretrieve(COUNTRY_DATA_URL)

    if int(headers["Content-Length"]) > MAX_RESPONSE_BYTES:
        raise ValueError("Country data response too large")

    ip_range_values = []
    ip_range_countries = []
    copyright_notice = None

    with zipfile.ZipFile(file_path, "r") as zip_file_handle:
        license_file_name, readme_file_name, csv_file_name = zip_file_handle.namelist()

        with zip_file_handle.open(readme_file_name) as readme_file_handle:
            for line in readme_file_handle:
                if COPYRIGHT_PREFIX in line:
                    copyright_notice = line.strip()

        if not copyright_notice:
            raise ValueError("Copyright notice was not found")

        if EXPECTED_COPYRIGHT_AUTHOR not in copyright_notice:
            raise ValueError(f"Missing author '{EXPECTED_COPYRIGHT_AUTHOR}' in copyright notice '{copyright_notice}'")

        with zip_file_handle.open(license_file_name) as license_file_handle:
            if EXPECTED_LICENSE not in license_file_handle.read():
                raise ValueError("Wrong country data license")

        with zip_file_handle.open(csv_file_name) as csv_file_handle:
            for row in csv.reader(io.TextIOWrapper(csv_file_handle)):
                _address_from, address_to, country_code, _country_name = list(row)
                address_to = int(address_to)

                if (len(country_code) != 2 or not country_code.isupper()) and country_code != "-":
                    raise ValueError("Invalid country code")

                if address_to < 0 or address_to > MAX_IPV4_RANGE:
                    raise ValueError("Invalid IP address")

                ip_range_values.append(address_to)
                ip_range_countries.append(country_code)

    return ip_range_values, ip_range_countries, copyright_notice


def update_ip_country_data():
    """Update country data file."""

    timestamp_updated = int(time.time())
    h_timestamp_updated = time.strftime("%Y-%m-%d", time.localtime(timestamp_updated))
    ip_range_values, ip_range_countries, copyright_notice = parse_ip_country_data()

    # File header
    output = bytearray(f"""# {PRODUCT_NAME} is licensed under
# {EXPECTED_LICENSE.decode()}.
# {copyright_notice.decode()}

# Generated on {h_timestamp_updated}

""".encode())

    # IP range data
    for ip_address in ip_range_values:
        output += f"{ip_address},".encode()

    del output[-1]
    output += b"\n"

    # IP range countries
    for country_code in ip_range_countries:
        output += f'{country_code.replace("-", "")},'.encode()

    del output[-1]

    # Write data to file
    with open(os.path.join(DATA_PATH, "ip_country_data.csv"), "wb") as file_handle:
        file_handle.write(output)


if __name__ == "__main__":
    update_ip_country_data()

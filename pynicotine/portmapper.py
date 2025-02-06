# COPYRIGHT (C) 2020-2024 Nicotine+ Contributors
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

import re
import socket
import struct
import sys
import time

from threading import Thread
from urllib.parse import urlsplit

import pynicotine

from pynicotine.config import config
from pynicotine.events import events
from pynicotine.logfacility import log
from pynicotine.utils import execute_command


class PortmapError(Exception):
    pass


class BaseImplementation:
    __slots__ = ("port", "local_ip_address")

    def __init__(self):
        self.port = None
        self.local_ip_address = None

    def set_port(self, port, local_ip_address):
        self.port = port
        self.local_ip_address = local_ip_address


class NATPMP(BaseImplementation):
    """Implementation of the NAT-PMP protocol.

    https://www.rfc-editor.org/rfc/rfc6886.
    """

    __slots__ = ("_gateway_address",)

    NAME = "NAT-PMP"
    REQUEST_PORT = 5351
    REQUEST_ATTEMPTS = 2  # spec says 9, but 2 should be enough
    REQUEST_INIT_TIMEOUT = 0.250  # seconds
    SUCCESS_RESULT = 0

    class PortmapResponse:
        __slots__ = ("message", "result")

        def __init__(self, message):

            self.message = message
            (
                _version,
                _op_code,
                self.result,
                _sec_since_epoch,
                _private_port,
                _public_port,
                _lease_duration
            ) = struct.unpack('!BBHIHHI', message)

        def __bytes__(self):
            return self.message

    class PortmapRequest:
        __slots__ = ("_public_port", "_private_port", "_lease_duration")

        RESERVED_VALUE = 0
        TCP_OP_CODE = 2
        VERSION = 0

        def __init__(self, public_port, private_port, lease_duration):

            self._public_port = public_port
            self._private_port = private_port
            self._lease_duration = lease_duration

        def sendto(self, sock, addr, num_attempt):

            msg = bytes(self)
            ip_address, port = addr
            sock.sendto(msg, addr)

            log.add_debug(
                "NAT-PMP: Portmap request attempt %s of %s to gateway %s, port %s: %s",
                (num_attempt, NATPMP.REQUEST_ATTEMPTS, ip_address, port, msg)
            )

        def __bytes__(self):

            return struct.pack(
                '!BBHHHI',
                self.VERSION,
                self.TCP_OP_CODE,
                self.RESERVED_VALUE,
                self._private_port,
                self._public_port,
                self._lease_duration
            )

    def __init__(self):
        super().__init__()
        self._gateway_address = None

    @staticmethod
    def _get_gateway_address():

        if sys.platform == "linux":
            gateway_address = None

            with open("/proc/net/route", encoding="utf-8") as file_handle:
                next(file_handle)  # Skip header

                for line in file_handle:
                    routes = line.strip().split()
                    destination_address = socket.inet_ntoa(struct.pack("<L", int(routes[1], 16)))

                    if destination_address != "0.0.0.0":
                        continue

                    gateway_address = socket.inet_ntoa(struct.pack("<L", int(routes[2], 16)))
                    break

            return gateway_address

        if sys.platform == "win32":
            gateway_pattern = re.compile(b".*?0.0.0.0 +0.0.0.0 +(.*?) +?[^\n]*\n")
        else:
            gateway_pattern = re.compile(b"(?:default|0\\.0\\.0\\.0|::/0)\\s+([\\w\\.:]+)\\s+.*UG")

        output = execute_command("netstat -rn", returnoutput=True, hidden=True)
        return gateway_pattern.search(output).group(1)

    def _request_port_mapping(self, public_port, private_port, lease_duration):

        with socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP) as sock:
            log.add_debug("NAT-PMP: Binding socket to local IP address %s", self.local_ip_address)

            sock.bind((self.local_ip_address, 0))
            request = self.PortmapRequest(public_port, private_port, lease_duration)
            timeout = self.REQUEST_INIT_TIMEOUT

            for i in range(1, self.REQUEST_ATTEMPTS + 1):
                sock.settimeout(timeout)
                request.sendto(sock, (self._gateway_address, self.REQUEST_PORT), i)

                try:
                    response = self.PortmapResponse(message=sock.recv(16))
                    return response.result

                except socket.timeout:
                    timeout *= 2

        log.add_debug("NAT-PMP: Giving up, all %s portmap requests timed out", self.REQUEST_ATTEMPTS)

        return None

    def add_port_mapping(self, lease_duration):

        self._gateway_address = self._get_gateway_address()
        result = self._request_port_mapping(
            public_port=self.port,
            private_port=self.port,
            lease_duration=lease_duration
        )

        if result != self.SUCCESS_RESULT:
            raise PortmapError(f"NAT-PMP error code {result}")

    def remove_port_mapping(self):

        result = self._request_port_mapping(
            public_port=0,
            private_port=self.port,
            lease_duration=0
        )
        self._gateway_address = None

        if result != self.SUCCESS_RESULT:
            raise PortmapError(f"NAT-PMP error code {result}")


class UPnP(BaseImplementation):
    """Implementation of the UPnP protocol."""

    __slots__ = ("_service",)

    NAME = "UPnP"
    USER_AGENT = (
        f"Python/{sys.version.split()[0]} "
        "UPnP/2.0 "
        f"{pynicotine.__application_name__}/{pynicotine.__version__}"
    )
    MULTICAST_HOST = "239.255.255.250"
    MULTICAST_PORT = 1900
    MULTICAST_TTL = 2         # Should default to 2 according to UPnP specification
    MX_RESPONSE_DELAY = 1     # At least 1 second is sufficient according to UPnP specification
    HTTP_REQUEST_TIMEOUT = 5

    class Service:
        __slots__ = ("service_type", "control_url")

        def __init__(self, service_type, control_url):
            self.service_type = service_type
            self.control_url = control_url

    class SSDPResponse:
        """Simple Service Discovery Protocol (SSDP) response."""

        __slots__ = ("message", "headers")

        def __init__(self, message):

            import email.parser

            self.message = message
            self.headers = list(email.parser.Parser().parsestr("\r\n".join(message.splitlines()[1:])).items())

        def __bytes__(self):
            return self.message.encode("utf-8")

    class SSDPRequest:
        """Simple Service Discovery Protocol (SSDP) request."""

        __slots__ = ("headers",)

        def __init__(self, search_target):

            self.headers = {
                "HOST": f"{UPnP.MULTICAST_HOST}:{UPnP.MULTICAST_PORT}",
                "ST": search_target,
                "MAN": '"ssdp:discover"',
                "MX": str(UPnP.MX_RESPONSE_DELAY),
                "USER-AGENT": UPnP.USER_AGENT
            }

        def sendto(self, sock, addr):

            msg = bytes(self)
            sock.sendto(msg, addr)

            log.add_debug("UPnP: SSDP request sent: %s", msg)

        def __bytes__(self):

            headers = ["M-SEARCH * HTTP/1.1"]

            for header_name, header_value in self.headers.items():
                headers.append(f"{header_name}: {header_value}")

            return "\r\n".join(headers).encode("utf-8") + b"\r\n\r\n"

    class SSDP:

        @staticmethod
        def get_service_control_url(location_url):

            service_type = None
            control_url = None

            try:
                from urllib.error import HTTPError
                from urllib.request import urlopen
                from xml.etree import ElementTree

                try:
                    with urlopen(location_url, timeout=UPnP.HTTP_REQUEST_TIMEOUT) as response:
                        response_body = response.read()

                except HTTPError as error:
                    # Received HTTP error, check what the response body says
                    response_body = error.read()

                log.add_debug("UPnP: Device description response from %s: %s", (location_url, response_body))

                xml = ElementTree.fromstring(response_body.decode("utf-8", "replace"))

                for service in xml.findall(".//{urn:schemas-upnp-org:device-1-0}service"):
                    found_service_type = service.find(".//{urn:schemas-upnp-org:device-1-0}serviceType").text

                    if found_service_type in {
                        "urn:schemas-upnp-org:service:WANIPConnection:2",
                        "urn:schemas-upnp-org:service:WANIPConnection:1",
                        "urn:schemas-upnp-org:service:WANPPPConnection:1"
                    }:
                        # We found a router with UPnP enabled
                        location_url_parts = urlsplit(location_url)
                        location_url_base = f"{location_url_parts.scheme}://{location_url_parts.netloc}/"
                        control_url = service.find(".//{urn:schemas-upnp-org:device-1-0}controlURL").text

                        # Relative URL
                        if control_url.startswith("/"):
                            control_url = location_url_base + control_url.lstrip("/")

                        # Absolute URL (allowed in UPnP 1.0)
                        elif not control_url.startswith(location_url_base):
                            log.add_debug(
                                "UPnP: Invalid control URL %s for service %s, ignoring",
                                (control_url, found_service_type)
                            )
                            control_url = None
                            continue

                        service_type = found_service_type
                        break

            except Exception as error:
                # Invalid response
                log.add_debug("UPnP: Invalid device description response from %s: %s", (location_url, error))

            return service_type, control_url

        @staticmethod
        def add_service(services, locations, ssdp_response):

            response_headers = {k.upper(): v for k, v in ssdp_response.headers}
            log.add_debug("UPnP: Device search response: %s", bytes(ssdp_response))

            if "LOCATION" not in response_headers:
                log.add_debug("UPnP: M-SEARCH response did not contain a LOCATION header: %s", ssdp_response.headers)
                return

            location = response_headers["LOCATION"]

            if location in locations:
                log.add_debug("UPnP: Device location was previously processed, ignoring")
                return

            locations.add(location)

            service_type, control_url = UPnP.SSDP.get_service_control_url(location)

            if service_type is None or control_url is None:
                log.add_debug("UPnP: No router with UPnP enabled in device search response, ignoring")
                return

            log.add_debug("UPnP: Device details: service_type '%s'; control_url '%s'", (service_type, control_url))

            if service_type in services:
                log.add_debug("UPnP: Service was previously added, ignoring")
                return

            services[service_type] = UPnP.Service(service_type=service_type, control_url=control_url)

            log.add_debug("UPnP: Added service to list")

        @staticmethod
        def get_services(private_ip):

            log.add_debug("UPnP: Discovering... delay=%s seconds", UPnP.MX_RESPONSE_DELAY)

            # Create a UDP socket and set its timeout
            with socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP) as sock:
                log.add_debug("UPnP: Binding socket to local IP address %s", private_ip)

                sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(private_ip))
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, struct.pack("B", UPnP.MULTICAST_TTL))
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                sock.settimeout(UPnP.MX_RESPONSE_DELAY + 0.1)  # Larger timeout in case data arrives at the last moment
                sock.bind((private_ip, 0))

                # Protocol 2
                wan_igd2 = UPnP.SSDPRequest("urn:schemas-upnp-org:device:InternetGatewayDevice:2")
                wan_ip2 = UPnP.SSDPRequest("urn:schemas-upnp-org:service:WANIPConnection:2")

                wan_igd2.sendto(sock, (UPnP.MULTICAST_HOST, UPnP.MULTICAST_PORT))
                wan_ip2.sendto(sock, (UPnP.MULTICAST_HOST, UPnP.MULTICAST_PORT))

                # Protocol 1
                wan_igd1 = UPnP.SSDPRequest("urn:schemas-upnp-org:device:InternetGatewayDevice:1")
                wan_ip1 = UPnP.SSDPRequest("urn:schemas-upnp-org:service:WANIPConnection:1")
                wan_ppp1 = UPnP.SSDPRequest("urn:schemas-upnp-org:service:WANPPPConnection:1")

                wan_igd1.sendto(sock, (UPnP.MULTICAST_HOST, UPnP.MULTICAST_PORT))
                wan_ip1.sendto(sock, (UPnP.MULTICAST_HOST, UPnP.MULTICAST_PORT))
                wan_ppp1.sendto(sock, (UPnP.MULTICAST_HOST, UPnP.MULTICAST_PORT))

                locations = set()
                services = {}

                while True:
                    try:
                        message = sock.recv(65507)  # Maximum size of UDP message
                        UPnP.SSDP.add_service(
                            services, locations, UPnP.SSDPResponse(message.decode("utf-8", "replace")))

                    except socket.timeout:
                        break

                log.add_debug("UPnP: %s service(s) detected", len(services))

            return services

    def __init__(self):
        super().__init__()
        self._service = None

    @staticmethod
    def _find_service(private_ip):

        services = UPnP.SSDP.get_services(private_ip)
        service = services.get("urn:schemas-upnp-org:service:WANIPConnection:2")

        if not service:
            service = services.get("urn:schemas-upnp-org:service:WANIPConnection:1")

        if not service:
            service = services.get("urn:schemas-upnp-org:service:WANPPPConnection:1")

        return service

    def _request_port_mapping(self, public_port, private_ip, private_port, mapping_description, lease_duration):
        """Function that adds a port mapping to the router.

        If a port mapping already exists, it is updated with a lease
        period of 12 hours.
        """

        from urllib.error import HTTPError
        from urllib.request import Request
        from urllib.request import urlopen
        from xml.etree import ElementTree

        service_type = self._service.service_type
        control_url = self._service.control_url

        log.add_debug("UPnP: Adding port mapping (%s %s, %s) at url '%s'",
                      (private_ip, private_port, service_type, control_url))

        headers = {
            "Host": urlsplit(control_url).netloc,
            "Content-Type": "text/xml; charset=utf-8",
            "USER-AGENT": self.USER_AGENT,
            "SOAPACTION": f'"{service_type}#AddPortMapping"'
        }

        body = (
            ('<?xml version="1.0"?>\r\n'
             + '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
             + 's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
             + "<s:Body>"
             + '<u:AddPortMapping xmlns:u="%s">'
             + "<NewRemoteHost></NewRemoteHost>"
             + "<NewExternalPort>%s</NewExternalPort>"
             + "<NewProtocol>TCP</NewProtocol>"
             + "<NewInternalPort>%s</NewInternalPort>"
             + "<NewInternalClient>%s</NewInternalClient>"
             + "<NewEnabled>1</NewEnabled>"
             + "<NewPortMappingDescription>%s</NewPortMappingDescription>"
             + "<NewLeaseDuration>%s</NewLeaseDuration>"
             + "</u:AddPortMapping>"
             + "</s:Body>"
             + "</s:Envelope>\r\n") %
            (service_type, public_port, private_port, private_ip, mapping_description, lease_duration)
        ).encode("utf-8")

        log.add_debug("UPnP: Add port mapping request headers: %s", headers)
        log.add_debug("UPnP: Add port mapping request contents: %s", body)

        try:
            request = Request(control_url, data=body, headers=headers)
            with urlopen(request, timeout=self.HTTP_REQUEST_TIMEOUT) as response:
                response_body = response.read()

        except HTTPError as error:
            # Received HTTP error, but response might also contain UPnP error code.
            # E.g. MikroTik routers that send UPnP error 725 (OnlyPermanentLeasesSupported).
            response_body = error.read()

        xml = ElementTree.fromstring(response_body.decode("utf-8", "replace"))

        if xml.find(".//{http://schemas.xmlsoap.org/soap/envelope/}Body") is None:
            raise PortmapError(f"Invalid response: {response_body}")

        log.add_debug("UPnP: Add port mapping response: %s", response_body)

        error_code = xml.findtext(".//{urn:schemas-upnp-org:control-1-0}errorCode")
        error_description = xml.findtext(".//{urn:schemas-upnp-org:control-1-0}errorDescription")

        return error_code, error_description

    def add_port_mapping(self, lease_duration):
        """This function supports creating a Port Mapping via the UPnP IGDv1
        and IGDv2 protocol.

        Any UPnP port mapping done with IGDv2 will expire after a
        maximum of 7 days (lease period), according to the protocol. We
        set the lease period to a shorter 12 hours, and regularly renew
        the port mapping.
        """

        # Find router
        self._service = self._find_service(self.local_ip_address)

        if not self._service:
            raise PortmapError(_("No UPnP devices found"))

        # Perform the port mapping
        log.add_debug("UPnP: Trying to redirect external WAN port %s TCP => %s port %s TCP",
                      (self.port, self.local_ip_address, self.port))

        error_code, error_description = self._request_port_mapping(
            public_port=self.port,
            private_ip=self.local_ip_address,
            private_port=self.port,
            mapping_description="NicotinePlus",
            lease_duration=lease_duration
        )

        if error_code == "725" and lease_duration > 0:
            log.add_debug("UPnP: Router requested permanent lease duration")
            self.add_port_mapping(lease_duration=0)
            return

        if error_code or error_description:
            raise PortmapError(f"Error code {error_code}: {error_description}")

    def remove_port_mapping(self):

        if not self._service:
            return

        from urllib.error import HTTPError
        from urllib.request import Request
        from urllib.request import urlopen

        service_type = self._service.service_type
        control_url = self._service.control_url
        self._service = None

        headers = {
            "Host": urlsplit(control_url).netloc,
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPACTION": f'"{service_type}#DeletePortMapping"'
        }

        body = (
            ('<?xml version="1.0"?>\r\n'
             + '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
             + 's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
             + "<s:Body>"
             + '<u:DeletePortMapping xmlns:u="%s">'
             + "<NewRemoteHost></NewRemoteHost>"
             + "<NewExternalPort>%s</NewExternalPort>"
             + "<NewProtocol>TCP</NewProtocol>"
             + "</u:DeletePortMapping>"
             + "</s:Body>"
             + "</s:Envelope>\r\n") %
            (service_type, self.port)
        ).encode("utf-8")

        log.add_debug("UPnP: Remove port mapping request headers: %s", headers)
        log.add_debug("UPnP: Remove port mapping request contents: %s", body)

        try:
            request = Request(control_url, data=body, headers=headers)
            with urlopen(request, timeout=self.HTTP_REQUEST_TIMEOUT) as response:
                response_body = response.read()

        except HTTPError as error:
            # Received HTTP error, but response body might contain useful information
            response_body = error.read()

        log.add_debug("UPnP: Remove port mapping response: %s", response_body)


class PortMapper:
    """Class that handles Port Mapping."""

    __slots__ = ("_active_implementation", "_has_port", "_is_mapping_port", "_timer",
                 "_natpmp", "_upnp")

    RENEWAL_INTERVAL = 7200   # 2 hours
    LEASE_DURATION = 43200    # 12 hours

    def __init__(self):

        self._active_implementation = None
        self._has_port = False
        self._is_mapping_port = False
        self._timer = None
        self._natpmp = NATPMP()
        self._upnp = UPnP()

    def _wait_until_ready(self):

        while self._is_mapping_port:
            # Port mapping in progress, wait until it's finished
            time.sleep(0.1)

    def _add_port_mapping(self):

        self._wait_until_ready()

        if not config.sections["server"]["upnp"]:
            return

        self._is_mapping_port = True
        log.add_debug("Creating Port Mapping rule...")

        try:
            self._active_implementation = self._natpmp
            self._natpmp.add_port_mapping(self.LEASE_DURATION)

        except Exception as natpmp_error:
            log.add_debug("NAT-PMP not available, falling back to UPnP: %s", natpmp_error)

            try:
                self._active_implementation = self._upnp
                self._upnp.add_port_mapping(self.LEASE_DURATION)

            except Exception as upnp_error:
                log.add(_("%(protocol)s: Failed to forward external port %(external_port)s: %(error)s"), {
                    "protocol": self._active_implementation.NAME,
                    "external_port": self._active_implementation.port,
                    "error": upnp_error
                })

                if str(upnp_error) != _("No UPnP devices found"):
                    from traceback import format_exc
                    log.add_debug(format_exc())

                self._active_implementation = None
                self._is_mapping_port = False
                return

        log.add(_("%(protocol)s: External port %(external_port)s successfully forwarded to local "
                  "IP address %(ip_address)s port %(local_port)s"), {
            "protocol": self._active_implementation.NAME,
            "external_port": self._active_implementation.port,
            "ip_address": self._active_implementation.local_ip_address,
            "local_port": self._active_implementation.port
        })
        self._is_mapping_port = False

    def _remove_port_mapping(self):

        self._wait_until_ready()

        if not self._active_implementation:
            return

        self._is_mapping_port = True

        try:
            self._active_implementation.remove_port_mapping()

        except Exception as error:
            log.add_debug("%s: Failed to remove port mapping: %s", (self._active_implementation.NAME, error))

        self._active_implementation = None
        self._is_mapping_port = False

    def _start_renewal_timer(self):
        self._cancel_renewal_timer()
        self._timer = events.schedule(delay=self.RENEWAL_INTERVAL, callback=self.add_port_mapping)

    def _cancel_renewal_timer(self):
        events.cancel_scheduled(self._timer)

    def set_port(self, port, local_ip_address):

        self._natpmp.set_port(port, local_ip_address)
        self._upnp.set_port(port, local_ip_address)

        self._has_port = (port is not None)

    def add_port_mapping(self, blocking=False):

        # Check if we want to do a port mapping
        if not config.sections["server"]["upnp"]:
            return

        if not self._has_port:
            return

        # Do the port mapping
        if blocking:
            self._add_port_mapping()
        else:
            Thread(target=self._add_port_mapping, name="AddPortmapping", daemon=True).start()

        # Renew port mapping entry regularly
        self._start_renewal_timer()

    def remove_port_mapping(self, blocking=False):

        self._cancel_renewal_timer()

        if blocking:
            self._remove_port_mapping()
            return

        Thread(target=self._remove_port_mapping, name="RemovePortmapping", daemon=True).start()

# COPYRIGHT (C) 2020-2022 Nicotine+ Contributors
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

import socket

from threading import Thread
from urllib.parse import urlsplit

from pynicotine.config import config
from pynicotine.events import events
from pynicotine.logfacility import log


class UPnP:

    MULTICAST_HOST = "239.255.255.250"
    MULTICAST_PORT = 1900
    MULTICAST_TTL = 2         # Should default to 2 according to UPnP specification
    MX_RESPONSE_DELAY = 1     # At least 1 second is sufficient according to UPnP specification
    HTTP_REQUEST_TIMEOUT = 5

    class Service:
        def __init__(self, service_type, control_url):
            self.service_type = service_type
            self.control_url = control_url

    class SSDPResponse:
        """ Simple Service Discovery Protocol (SSDP) response """

        def __init__(self, message):

            import email.parser

            self.message = message
            self.headers = list(email.parser.Parser().parsestr("\r\n".join(message.splitlines()[1:])).items())

        def __bytes__(self):
            """ Return complete SSDP response """

            return self.message.encode("utf-8")

    class SSDPRequest:
        """ Simple Service Discovery Protocol (SSDP) request """

        def __init__(self, search_target):

            self.headers = {
                "HOST": f"{UPnP.MULTICAST_HOST}:{UPnP.MULTICAST_PORT}",
                "ST": search_target,
                "MAN": '"ssdp:discover"',
                "MX": str(UPnP.MX_RESPONSE_DELAY)
            }

        def sendto(self, sock, addr):

            msg = bytes(self)
            sock.sendto(msg, addr)

            log.add_debug("UPnP: SSDP request: %s", msg)

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
                from urllib.request import urlopen
                from xml.etree import ElementTree

                with urlopen(location_url, timeout=UPnP.HTTP_REQUEST_TIMEOUT) as response:
                    response_body = response.read()

                log.add_debug("UPnP: Device description response from %s: %s", (location_url, response_body))

                xml = ElementTree.fromstring(response_body.decode("utf-8"))

                for service in xml.findall(".//{urn:schemas-upnp-org:device-1-0}service"):
                    found_service_type = service.find(".//{urn:schemas-upnp-org:device-1-0}serviceType").text

                    if found_service_type in ("urn:schemas-upnp-org:service:WANIPConnection:1",
                                              "urn:schemas-upnp-org:service:WANPPPConnection:1",
                                              "urn:schemas-upnp-org:service:WANIPConnection:2"):
                        # We found a router with UPnP enabled
                        service_type = found_service_type
                        control_url = service.find(".//{urn:schemas-upnp-org:device-1-0}controlURL").text
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

            url_parts = urlsplit(location)
            service_type, control_url = UPnP.SSDP.get_service_control_url(location)
            control_url = f"{url_parts.scheme}://{url_parts.netloc}{control_url}"

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
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(private_ip))
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, UPnP.MULTICAST_TTL)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                sock.settimeout(UPnP.MX_RESPONSE_DELAY + 0.1)  # Larger timeout in case data arrives at the last moment
                sock.bind((private_ip, 0))

                # Protocol 1
                wan_ip1 = UPnP.SSDPRequest("urn:schemas-upnp-org:service:WANIPConnection:1")
                wan_ppp1 = UPnP.SSDPRequest("urn:schemas-upnp-org:service:WANPPPConnection:1")
                wan_igd1 = UPnP.SSDPRequest("urn:schemas-upnp-org:device:InternetGatewayDevice:1")

                wan_ip1.sendto(sock, (UPnP.MULTICAST_HOST, UPnP.MULTICAST_PORT))
                log.add_debug("UPnP: Sent M-SEARCH IP request 1")

                wan_ppp1.sendto(sock, (UPnP.MULTICAST_HOST, UPnP.MULTICAST_PORT))
                log.add_debug("UPnP: Sent M-SEARCH PPP request 1")

                wan_igd1.sendto(sock, (UPnP.MULTICAST_HOST, UPnP.MULTICAST_PORT))
                log.add_debug("UPnP: Sent M-SEARCH IGD request 1")

                # Protocol 2
                wan_ip2 = UPnP.SSDPRequest("urn:schemas-upnp-org:service:WANIPConnection:2")
                wan_igd2 = UPnP.SSDPRequest("urn:schemas-upnp-org:device:InternetGatewayDevice:2")

                wan_ip2.sendto(sock, (UPnP.MULTICAST_HOST, UPnP.MULTICAST_PORT))
                log.add_debug("UPnP: Sent M-SEARCH IP request 2")

                wan_igd2.sendto(sock, (UPnP.MULTICAST_HOST, UPnP.MULTICAST_PORT))
                log.add_debug("UPnP: Sent M-SEARCH IGD request 2")

                locations = set()
                services = {}

                while True:
                    try:
                        message = sock.recv(65507)  # Maximum size of UDP message
                        UPnP.SSDP.add_service(services, locations, UPnP.SSDPResponse(message.decode("utf-8")))

                    except socket.timeout:
                        break

                log.add_debug("UPnP: %s service(s) detected", str(len(services)))

            return services

    def __init__(self):

        self.port = None
        self.local_ip_address = None
        self._service = None

    def set_port(self, port, local_ip_address):
        self.port = port
        self.local_ip_address = local_ip_address

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
        """
        Function that adds a port mapping to the router.
        If a port mapping already exists, it is updated with a lease period of 12 hours.
        """

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

        with urlopen(Request(control_url, data=body, headers=headers), timeout=self.HTTP_REQUEST_TIMEOUT) as response:
            response_body = response.read()

        xml = ElementTree.fromstring(response_body.decode("utf-8"))

        if xml.find(".//{http://schemas.xmlsoap.org/soap/envelope/}Body") is None:
            raise RuntimeError(f"Invalid response: {response_body}")

        log.add_debug("UPnP: Add port mapping response: %s", response_body)

        error_code = xml.findtext(".//{urn:schemas-upnp-org:control-1-0}errorCode")
        error_description = xml.findtext(".//{urn:schemas-upnp-org:control-1-0}errorDescription")

        return error_code, error_description

    def add_port_mapping(self, lease_duration):
        """
        This function supports creating a Port Mapping via the UPnP
        IGDv1 and IGDv2 protocol.

        Any UPnP port mapping done with IGDv2 will expire after a
        maximum of 7 days (lease period), according to the protocol.
        We set the lease period to a shorter 12 hours, and regularly
        renew the port mapping.
        """

        try:
            log.add_debug("UPnP: Creating Port Mapping rule...")

            # Find router
            self._service = self._find_service(self.local_ip_address)

            if not self._service:
                raise RuntimeError(_("No UPnP devices found"))

            # Perform the port mapping
            log.add_debug("UPnP: Trying to redirect external WAN port %s TCP => %s port %s TCP", (
                self.port,
                self.local_ip_address,
                self.port
            ))

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
                raise RuntimeError(f"Error code {error_code}: {error_description}")

        except Exception as error:
            from traceback import format_exc
            log.add(_("UPnP: Failed to forward external port %(external_port)s: %(error)s"), {
                "external_port": self.port,
                "error": error
            })
            log.add_debug(format_exc())
            return

        log.add(_("UPnP: External port %(external_port)s successfully forwarded to local "
                  "IP address %(ip_address)s port %(local_port)s"), {
            "external_port": self.port,
            "ip_address": self.local_ip_address,
            "local_port": self.port
        })

    def remove_port_mapping(self):

        if not self._service:
            return

        from urllib.request import Request
        from urllib.request import urlopen

        service_type = self._service.service_type
        control_url = self._service.control_url

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
            with urlopen(
                    Request(control_url, data=body, headers=headers), timeout=self.HTTP_REQUEST_TIMEOUT) as response:
                log.add_debug("UPnP: Remove port mapping response: %s", response.read())

        except Exception as error:
            log.add_debug("UPnP: Failed to remove port mapping: %s", error)

        self._service = None


class PortMapper:
    """ Class that handles Port Mapping """

    RENEWAL_INTERVAL = 14400  # 4 hours
    LEASE_DURATION = 43200    # 12 hours

    def __init__(self):
        self._timer = None
        self._upnp = UPnP()

    def set_port(self, port, local_ip_address):
        self._upnp.set_port(port, local_ip_address)

    def _add_port_mapping(self):
        self._upnp.add_port_mapping(self.LEASE_DURATION)

    def _remove_port_mapping(self):
        self._upnp.remove_port_mapping()

    def add_port_mapping(self, blocking=False):

        # Check if we want to do a port mapping
        if not config.sections["server"]["upnp"]:
            return

        # Do the port mapping
        if blocking:
            self._add_port_mapping()
        else:
            Thread(target=self._add_port_mapping, name="AddPortmapping", daemon=True).start()

        self._start_timer()

    def remove_port_mapping(self, blocking=False):

        self._cancel_timer()

        if blocking:
            self._remove_port_mapping()
            return

        Thread(target=self._remove_port_mapping, name="RemovePortmapping", daemon=True).start()

    def _start_timer(self):
        """ Port mapping entries last 12 hours, we need to regularly renew them.
        The default interval is 4 hours. """

        self._cancel_timer()
        self._timer = events.schedule(delay=self.RENEWAL_INTERVAL, callback=self.add_port_mapping)

    def _cancel_timer(self):
        events.cancel_scheduled(self._timer)

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

import threading
import socket

from pynicotine.config import config
from pynicotine.logfacility import log
from pynicotine.utils import http_request


MULTICAST_HOST = "239.255.255.250"
MULTICAST_PORT = 1900
MULTICAST_TTL = 2  # Should default to 2 according to UPnP specification
MX_RESPONSE_DELAY = 1  # At least 1 second is sufficient according to UPnP specification
HTTP_REQUEST_TIMEOUT = 5


class Service:
    def __init__(self, service_type, url_scheme, base_url, root_url, control_url):
        self.service_type = service_type
        self.url_scheme = url_scheme
        self.base_url = base_url
        self.root_url = root_url
        self.control_url = control_url


class SSDPResponse:
    """ Simple Service Discovery Protocol (SSDP) response """

    def __init__(self, message):

        import email.parser

        self.message = message
        self.headers = list(email.parser.Parser().parsestr('\r\n'.join(message.splitlines()[1:])).items())

    def __bytes__(self):
        """ Return complete SSDP response """

        return self.message.encode('utf-8')


class SSDPRequest:
    """ Simple Service Discovery Protocol (SSDP) request """

    def __init__(self, search_target):

        self.headers = {
            "HOST": "%s:%s" % (MULTICAST_HOST, MULTICAST_PORT),
            "ST": search_target,
            "MAN": '"ssdp:discover"',
            "MX": str(MX_RESPONSE_DELAY)
        }

    def sendto(self, sock, addr):

        msg = bytes(self)
        sock.sendto(msg, addr)

        log.add_debug("UPnP: SSDP request: %s", msg)

    def __bytes__(self):

        headers = ["M-SEARCH * HTTP/1.1"]

        for header in self.headers.items():
            headers.append("%s: %s" % header)

        return '\r\n'.join(headers).encode('utf-8') + b'\r\n\r\n'


class SSDP:

    @staticmethod
    def get_service_control_url(url_scheme, base_url, root_url):

        service_type = None
        control_url = None

        try:
            from xml.etree import ElementTree

            response = http_request(url_scheme, base_url, root_url, timeout=HTTP_REQUEST_TIMEOUT)
            log.add_debug("UPnP: Device description response from %s://%s%s: %s",
                          (url_scheme, base_url, root_url, response.encode('utf-8')))

            xml = ElementTree.fromstring(response)

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
            log.add_debug("UPnP: Invalid device description response from %s://%s%s: %s",
                          (url_scheme, base_url, root_url, error))

        return service_type, control_url

    @staticmethod
    def add_service(services, locations, ssdp_response):

        from urllib.parse import urlsplit
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
        service_type, control_url = SSDP.get_service_control_url(url_parts.scheme, url_parts.netloc, url_parts.path)

        if service_type is None or control_url is None:
            log.add_debug("UPnP: No router with UPnP enabled in device search response, ignoring")
            return

        log.add_debug("UPnP: Device details: service_type '%s'; control_url '%s'", (service_type, control_url))

        if service_type in services:
            log.add_debug("UPnP: Service was previously added, ignoring")
            return

        services[service_type] = Service(service_type=service_type, url_scheme=url_parts.scheme,
                                         base_url=url_parts.netloc, root_url=url_parts.path, control_url=control_url)

        log.add_debug("UPnP: Added service to list")

    @staticmethod
    def get_services(private_ip):

        log.add_debug("UPnP: Discovering... delay=%s seconds", MX_RESPONSE_DELAY)

        # Create a UDP socket and set its timeout
        with socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP) as sock:
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(private_ip))
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, MULTICAST_TTL)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.settimeout(MX_RESPONSE_DELAY + 0.1)  # Larger timeout in case data arrives at the last moment
            sock.bind((private_ip, 0))

            # Protocol 1
            wan_ip1 = SSDPRequest("urn:schemas-upnp-org:service:WANIPConnection:1")
            wan_ppp1 = SSDPRequest("urn:schemas-upnp-org:service:WANPPPConnection:1")
            wan_igd1 = SSDPRequest("urn:schemas-upnp-org:device:InternetGatewayDevice:1")

            wan_ip1.sendto(sock, (MULTICAST_HOST, MULTICAST_PORT))
            log.add_debug("UPnP: Sent M-SEARCH IP request 1")

            wan_ppp1.sendto(sock, (MULTICAST_HOST, MULTICAST_PORT))
            log.add_debug("UPnP: Sent M-SEARCH PPP request 1")

            wan_igd1.sendto(sock, (MULTICAST_HOST, MULTICAST_PORT))
            log.add_debug("UPnP: Sent M-SEARCH IGD request 1")

            # Protocol 2
            wan_ip2 = SSDPRequest("urn:schemas-upnp-org:service:WANIPConnection:2")
            wan_igd2 = SSDPRequest("urn:schemas-upnp-org:device:InternetGatewayDevice:2")

            wan_ip2.sendto(sock, (MULTICAST_HOST, MULTICAST_PORT))
            log.add_debug("UPnP: Sent M-SEARCH IP request 2")

            wan_igd2.sendto(sock, (MULTICAST_HOST, MULTICAST_PORT))
            log.add_debug("UPnP: Sent M-SEARCH IGD request 2")

            locations = set()
            services = {}

            while True:
                try:
                    message = sock.recv(65507)  # Maximum size of UDP message
                    SSDP.add_service(services, locations, SSDPResponse(message.decode('utf-8')))

                except socket.timeout:
                    break

            log.add_debug("UPnP: %s service(s) detected", str(len(services)))

        return services


class UPnP:
    """ Class that handles UPnP Port Mapping """

    def __init__(self, port, local_ip_address):

        self.port = port
        self.local_ip_address = local_ip_address
        self.timer = None

    @staticmethod
    def _request_port_mapping(service, protocol, public_port, private_ip, private_port,
                              mapping_description, lease_duration):
        """
        Function that adds a port mapping to the router.
        If a port mapping already exists, it is updated with a lease period of 24 hours.
        """

        from xml.etree import ElementTree

        url = '%s%s' % (service.base_url, service.control_url)
        log.add_debug("UPnP: Adding port mapping (%s %s/%s, %s) at url '%s'",
                      (private_ip, private_port, protocol, service.service_type, url))

        headers = {
            "Host": service.base_url,
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPACTION": '"%s#AddPortMapping"' % service.service_type
        }

        body = (
            ('<?xml version="1.0"?>\r\n'
             + '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
             + 's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
             + '<s:Body>'
             + '<u:AddPortMapping xmlns:u="%s">'
             + '<NewRemoteHost></NewRemoteHost>'
             + '<NewExternalPort>%s</NewExternalPort>'
             + '<NewProtocol>%s</NewProtocol>'
             + '<NewInternalPort>%s</NewInternalPort>'
             + '<NewInternalClient>%s</NewInternalClient>'
             + '<NewEnabled>1</NewEnabled>'
             + '<NewPortMappingDescription>%s</NewPortMappingDescription>'
             + '<NewLeaseDuration>%s</NewLeaseDuration>'
             + '</u:AddPortMapping>'
             + '</s:Body>'
             + '</s:Envelope>\r\n') %
            (service.service_type, public_port, protocol, private_port, private_ip,
             mapping_description, lease_duration)
        ).encode('utf-8')

        log.add_debug("UPnP: Add port mapping request headers: %s", headers)
        log.add_debug("UPnP: Add port mapping request contents: %s", body)

        response = http_request(
            service.url_scheme, service.base_url, service.control_url,
            request_type="POST", body=body, headers=headers, timeout=HTTP_REQUEST_TIMEOUT)

        xml = ElementTree.fromstring(response)

        if xml.find(".//{http://schemas.xmlsoap.org/soap/envelope/}Body") is None:
            raise Exception(_("Invalid response: %s") % response.encode('utf-8'))

        log.add_debug("UPnP: Add port mapping response: %s", response.encode('utf-8'))

        error_code = xml.findtext(".//{urn:schemas-upnp-org:control-1-0}errorCode")
        error_description = xml.findtext(".//{urn:schemas-upnp-org:control-1-0}errorDescription")

        return error_code, error_description

    @staticmethod
    def find_service(private_ip):

        services = SSDP.get_services(private_ip)
        service = services.get("urn:schemas-upnp-org:service:WANIPConnection:2")

        if not service:
            service = services.get("urn:schemas-upnp-org:service:WANIPConnection:1")

        if not service:
            service = services.get("urn:schemas-upnp-org:service:WANPPPConnection:1")

        return service

    def _update_port_mapping(self, lease_duration=86400):
        """
        This function supports creating a Port Mapping via the UPnP
        IGDv1 and IGDv2 protocol.

        Any UPnP port mapping done with IGDv2 will expire after a
        maximum of 7 days (lease period), according to the protocol.
        We set the lease period to a shorter 24 hours, and regularly
        renew the port mapping.
        """

        try:
            log.add_debug("UPnP: Creating Port Mapping rule...")

            # Find router
            service = self.find_service(self.local_ip_address)

            if not service:
                raise RuntimeError(_("UPnP is not available on this network"))

            # Perform the port mapping
            log.add_debug("UPnP: Trying to redirect external WAN port %s TCP => %s port %s TCP", (
                self.port,
                self.local_ip_address,
                self.port
            ))

            error_code, error_description = self._request_port_mapping(
                service=service,
                protocol="TCP",
                public_port=self.port,
                private_ip=self.local_ip_address,
                private_port=self.port,
                mapping_description="NicotinePlus",
                lease_duration=lease_duration
            )

            if error_code == "725" and lease_duration > 0:
                log.add_debug("UPnP: Router requested permanent lease duration")
                self._update_port_mapping(lease_duration=0)
                return

            if error_code or error_description:
                raise Exception(_("Error code %(code)s: %(description)s") %
                                {"code": error_code, "description": error_description})

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

    def add_port_mapping(self, blocking=False):

        # Test if we want to do a port mapping
        if not config.sections["server"]["upnp"]:
            return

        # Do the port mapping
        if blocking:
            self._update_port_mapping()
        else:
            thread = threading.Thread(target=self._update_port_mapping)
            thread.name = "UPnPAddPortmapping"
            thread.daemon = True
            thread.start()

        # Repeat
        self._start_timer()

    def _start_timer(self):
        """ Port mapping entries last 24 hours, we need to regularly renew them.
        The default interval is 4 hours. """

        self.cancel_timer()
        upnp_interval = config.sections["server"]["upnp_interval"]

        if upnp_interval < 1:
            return

        upnp_interval_seconds = upnp_interval * 60 * 60

        self.timer = threading.Timer(upnp_interval_seconds, self.add_port_mapping)
        self.timer.name = "UPnPTimer"
        self.timer.daemon = True
        self.timer.start()

    def cancel_timer(self):
        if self.timer:
            self.timer.cancel()

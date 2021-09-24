# COPYRIGHT (C) 2020-2021 Nicotine+ Team
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

import time
import select
import socket

from gettext import gettext as _

from pynicotine.logfacility import log
from pynicotine.utils import http_request


class Router:
    def __init__(self, wan_ip_type, url_scheme, base_url, root_url, service_type, control_url):
        self.search_target = wan_ip_type
        self.url_scheme = url_scheme
        self.base_url = base_url
        self.root_url = root_url
        self.service_type = service_type
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

    def __init__(self, headers):
        self.headers = headers

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
    multicast_host = "239.255.255.250"
    multicast_port = 1900
    response_time_secs = 2

    msearch_headers = {
        "HOST": "%s:%s" % (multicast_host, multicast_port),
        "ST": None,
        "MAN": '"ssdp:discover"',
        "MX": str(response_time_secs)
    }

    @staticmethod
    def get_router_control_url(url_scheme, base_url, root_url):

        service_type = None
        control_url = None

        try:
            # Parse the returned XML and find the <URLBase> and <controlURL> elements
            from xml.etree import ElementTree

            response = http_request(url_scheme, base_url, root_url, timeout=2)
            xml = ElementTree.fromstring(response)

            for service in xml.findall(".//{urn:schemas-upnp-org:device-1-0}service"):
                service_type = service.find(".//{urn:schemas-upnp-org:device-1-0}serviceType").text
                control_url = service.find(".//{urn:schemas-upnp-org:device-1-0}controlURL").text

        except Exception as error:
            # Invalid response
            log.add_debug("UPnP: Invalid router description response from %s://%s%s: %s",
                          (url_scheme, base_url, root_url, error))

        return service_type, control_url

    @staticmethod
    def add_router(routers, ssdp_response):

        from urllib.parse import urlsplit
        response_headers = {k.upper(): v for k, v in ssdp_response.headers}

        if "LOCATION" not in response_headers:
            log.add_debug("UPnP: M-SEARCH response did not contain a LOCATION header: %s", ssdp_response.headers)
            return

        url_parts = urlsplit(response_headers["LOCATION"])
        service_type, control_url = SSDP.get_router_control_url(url_parts.scheme, url_parts.netloc, url_parts.path)

        if service_type not in ("urn:schemas-upnp-org:service:WANIPConnection:1",
                                "urn:schemas-upnp-org:service:WANPPPConnection:1",
                                "urn:schemas-upnp-org:service:WANIPConnection:2"):
            # Invalid service type, don't add router
            return

        routers.append(
            Router(wan_ip_type=response_headers['ST'], url_scheme=url_parts.scheme,
                   base_url=url_parts.netloc, root_url=url_parts.path,
                   service_type=service_type, control_url=control_url))

    @staticmethod
    def get_routers(private_ip=None):

        log.add_debug("UPnP: Discovering... delay=%s seconds", SSDP.response_time_secs)

        # Create a UDP socket and set its timeout
        sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, SSDP.response_time_secs)
        sock.setblocking(False)

        if private_ip:
            sock.bind((private_ip, 0))

        # Protocol 1
        wan_ip1_sent = False
        SSDP.msearch_headers["ST"] = "urn:schemas-upnp-org:service:WANIPConnection:1"
        wan_ip1 = SSDPRequest(SSDP.msearch_headers)

        wan_ppp1_sent = False
        SSDP.msearch_headers["ST"] = "urn:schemas-upnp-org:service:WANPPPConnection:1"
        wan_ppp1 = SSDPRequest(SSDP.msearch_headers)

        wan_igd1_sent = False
        SSDP.msearch_headers["ST"] = "urn:schemas-upnp-org:device:InternetGatewayDevice:1"
        wan_igd1 = SSDPRequest(SSDP.msearch_headers)

        # Protocol 2
        wan_ip2_sent = False
        SSDP.msearch_headers["ST"] = "urn:schemas-upnp-org:service:WANIPConnection:2"
        wan_ip2 = SSDPRequest(SSDP.msearch_headers)

        wan_igd2_sent = False
        SSDP.msearch_headers["ST"] = "urn:schemas-upnp-org:device:InternetGatewayDevice:2"
        wan_igd2 = SSDPRequest(SSDP.msearch_headers)

        routers = []
        time_end = time.time() + SSDP.response_time_secs

        while time.time() < time_end:
            readable, writable, _ = select.select([sock], [sock], [sock], 0)

            for sock in readable:
                msg, _sender = sock.recvfrom(4096)
                ssdp_response = SSDPResponse(msg.decode('utf-8'))
                log.add_debug("UPnP: Device search response: %s", bytes(ssdp_response))

                SSDP.add_router(routers, ssdp_response)

            for sock in writable:
                if not wan_ip1_sent:
                    wan_ip1.sendto(sock, (SSDP.multicast_host, SSDP.multicast_port))
                    log.add_debug("UPnP: Sent M-SEARCH IP request 1")
                    time_end = time.time() + SSDP.response_time_secs
                    wan_ip1_sent = True

                if not wan_ppp1_sent:
                    wan_ppp1.sendto(sock, (SSDP.multicast_host, SSDP.multicast_port))
                    log.add_debug("UPnP: Sent M-SEARCH PPP request 1")
                    time_end = time.time() + SSDP.response_time_secs
                    wan_ppp1_sent = True

                if not wan_igd1_sent:
                    wan_igd1.sendto(sock, (SSDP.multicast_host, SSDP.multicast_port))
                    log.add_debug("UPnP: Sent M-SEARCH IGD request 1")
                    time_end = time.time() + SSDP.response_time_secs
                    wan_igd1_sent = True

                if not wan_ip2_sent:
                    wan_ip2.sendto(sock, (SSDP.multicast_host, SSDP.multicast_port))
                    log.add_debug("UPnP: Sent M-SEARCH IP request 2")
                    time_end = time.time() + SSDP.response_time_secs
                    wan_ip2_sent = True

                if not wan_igd2_sent:
                    wan_igd2.sendto(sock, (SSDP.multicast_host, SSDP.multicast_port))
                    log.add_debug("UPnP: Sent M-SEARCH IGD request 2")
                    time_end = time.time() + SSDP.response_time_secs
                    wan_igd2_sent = True

            # Cooldown
            time.sleep(0.01)

        log.add_debug("UPnP: %s device(s) detected", len(routers))

        sock.close()
        return routers


class UPnPPortMapping:
    """ Class that handles UPnP Port Mapping """

    request_body = (
        '<?xml version="1.0"?>\r\n'
        '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
        's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"><s:Body><u:AddPortMapping '
        'xmlns:u="%s"><NewRemoteHost></NewRemoteHost>'
        '<NewExternalPort>%s</NewExternalPort><NewProtocol>%s</NewProtocol><NewInternalPort>%s</NewInternalPort>'
        '<NewInternalClient>%s</NewInternalClient><NewEnabled>1</NewEnabled>'
        '<NewPortMappingDescription>%s</NewPortMappingDescription><NewLeaseDuration>%s</NewLeaseDuration>'
        '</u:AddPortMapping></s:Body></s:Envelope>\r\n')

    def add_port_mapping(self, router, protocol, public_port, private_ip, private_port,
                         mapping_description, lease_duration):
        """
        Function that adds a port mapping to the router.
        If a port mapping already exists, it is updated with a lease period of 24 hours.
        """

        from xml.etree import ElementTree

        url = '%s%s' % (router.base_url, router.control_url)
        log.add_debug("UPnP: Adding port mapping (%s %s/%s, %s) at url '%s'",
                      (private_ip, private_port, protocol, router.search_target, url))

        headers = {
            "Host": router.base_url,
            "Content-Type": "text/xml; charset=utf-8",
            "SOAPACTION": '"%s#AddPortMapping"' % router.service_type
        }

        body = (self.request_body % (router.service_type, public_port, protocol, private_port, private_ip,
                                     mapping_description, lease_duration)).encode('utf-8')

        log.add_debug("UPnP: Add port mapping request headers: %s", headers)
        log.add_debug("UPnP: Add port mapping request contents: %s", body)

        response = http_request(
            router.url_scheme, router.base_url, router.control_url,
            request_type="POST", body=body, headers=headers)

        xml = ElementTree.fromstring(response)

        if not xml.find(".//{http://schemas.xmlsoap.org/soap/envelope/}Body"):
            raise Exception("Invalid port mapping response: %s" % response.encode('utf-8'))

        log.add_debug("UPnP: Add port mapping response: %s", response.encode('utf-8'))

        error_code = xml.findtext(".//{urn:schemas-upnp-org:control-1-0}errorCode")
        error_description = xml.findtext(".//{urn:schemas-upnp-org:control-1-0}errorDescription")

        if error_code or error_description:
            raise Exception("Error code %(code)s: %(description)s" %
                            {"code": error_code, "description": error_description})

    @staticmethod
    def find_local_ip_address():

        # Create a UDP socket
        local_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Send a broadcast packet on a local address (doesn't need to be reachable,
        # but MacOS requires port to be non-zero)
        local_socket.connect(("10.255.255.255", 1))

        # This returns the "primary" IP on the local box, even if that IP is a NAT/private/internal IP.
        ip_address = local_socket.getsockname()[0]

        # Close the socket
        local_socket.close()

        return ip_address

    @staticmethod
    def find_router(private_ip=None):

        routers = SSDP.get_routers(private_ip)
        router = next((r for r in routers if r.search_target == "urn:schemas-upnp-org:service:WANIPConnection:2"), None)

        if not router:
            router = next(
                (r for r in routers if r.search_target == "urn:schemas-upnp-org:service:WANIPConnection:1"), None)

        if not router:
            router = next(
                (r for r in routers if r.search_target == "urn:schemas-upnp-org:service:WANPPPConnection:1"), None)

        if not router:
            router = next(
                (r for r in routers if r.search_target == "urn:schemas-upnp-org:device:InternetGatewayDevice:2"), None)

        if not router:
            router = next(
                (r for r in routers if r.search_target == "urn:schemas-upnp-org:device:InternetGatewayDevice:1"), None)

        if not router:
            router = next((r for r in routers), None)

        return router

    def update_port_mapping(self, listening_port):
        """
        This function supports creating a Port Mapping via the UPnP
        IGDv1 and IGDv2 protocol.

        Any UPnP port mapping done with IGDv2 will expire after a
        maximum of 7 days (lease period), according to the protocol.
        We set the lease period to a shorter 24 hours, and regularly
        renew the port mapping (see pynicotine.py).
        """

        try:
            local_ip_address = self._update_port_mapping(listening_port)

        except Exception as error:
            from traceback import format_exc
            log.add(_("UPnP error: %(error)s"), {"error": error})
            log.add_debug(format_exc())
            log.add(_("Failed to automate the creation of UPnP Port Mapping rule."))
            return

        log.add_debug(
            _("Managed to map external WAN port %(externalwanport)s "
              + "to your local host %(internalipaddress)s "
              + "port %(internallanport)s."),
            {
                "externalwanport": listening_port,
                "internalipaddress": local_ip_address,
                "internallanport": listening_port
            }
        )

    def _update_port_mapping(self, listening_port):

        log.add_debug("Creating Port Mapping rule via UPnP...")

        # Find local IP address
        local_ip_address = self.find_local_ip_address()

        # Find router
        router = self.find_router(local_ip_address)

        if not router:
            raise RuntimeError("UPnP does not work on this network")

        # Perform the port mapping
        log.add_debug("Trying to redirect external WAN port %s TCP => %s port %s TCP", (
            listening_port,
            local_ip_address,
            listening_port
        ))

        try:
            self.add_port_mapping(
                router=router,
                protocol="TCP",
                public_port=listening_port,
                private_ip=local_ip_address,
                private_port=listening_port,
                mapping_description="NicotinePlus",
                lease_duration=86400  # Expires in 24 hours
            )

        except Exception as error:
            raise RuntimeError(
                _("Failed to map the external WAN port: %(error)s") % {"error": error}) from error

        return local_ip_address

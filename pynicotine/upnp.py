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
import time
import select
import socket

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

    def __init__(self, search_target):

        self.headers = {
            "HOST": "%s:%s" % (SSDP.multicast_host, SSDP.multicast_port),
            "ST": search_target,
            "MAN": '"ssdp:discover"',
            "MX": str(SSDP.response_time_secs)
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
    multicast_host = "239.255.255.250"
    multicast_port = 1900
    response_time_secs = 2

    @staticmethod
    def get_router_control_url(url_scheme, base_url, root_url):

        service_type = None
        control_url = None

        try:
            from xml.etree import ElementTree

            response = http_request(url_scheme, base_url, root_url, timeout=2)
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
    def add_router(routers, ssdp_response):

        from urllib.parse import urlsplit
        response_headers = {k.upper(): v for k, v in ssdp_response.headers}

        log.add_debug("UPnP: Device search response: %s", bytes(ssdp_response))

        if "LOCATION" not in response_headers:
            log.add_debug("UPnP: M-SEARCH response did not contain a LOCATION header: %s", ssdp_response.headers)
            return

        url_parts = urlsplit(response_headers["LOCATION"])
        service_type, control_url = SSDP.get_router_control_url(url_parts.scheme, url_parts.netloc, url_parts.path)

        if service_type is None or control_url is None:
            log.add_debug("UPnP: No router with UPnP enabled in device search response, ignoring")
            return

        log.add_debug("UPnP: Device details: service_type '%s'; control_url '%s'", (service_type, control_url))

        routers.append(
            Router(wan_ip_type=response_headers['ST'], url_scheme=url_parts.scheme,
                   base_url=url_parts.netloc, root_url=url_parts.path,
                   service_type=service_type, control_url=control_url))

        log.add_debug("UPnP: Added device to list")

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
        wan_ip1 = SSDPRequest("urn:schemas-upnp-org:service:WANIPConnection:1")

        wan_ppp1_sent = False
        wan_ppp1 = SSDPRequest("urn:schemas-upnp-org:service:WANPPPConnection:1")

        wan_igd1_sent = False
        wan_igd1 = SSDPRequest("urn:schemas-upnp-org:device:InternetGatewayDevice:1")

        # Protocol 2
        wan_ip2_sent = False
        wan_ip2 = SSDPRequest("urn:schemas-upnp-org:service:WANIPConnection:2")

        wan_igd2_sent = False
        wan_igd2 = SSDPRequest("urn:schemas-upnp-org:device:InternetGatewayDevice:2")

        routers = []
        time_end = time.time() + SSDP.response_time_secs

        while time.time() < time_end:
            readable, writable, _ = select.select([sock], [sock], [sock], 0)

            for sock in readable:
                msg, _sender = sock.recvfrom(4096)
                SSDP.add_router(routers, SSDPResponse(msg.decode('utf-8')))

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

        log.add_debug("UPnP: %s device(s) detected", str(len(routers)))

        sock.close()
        return routers


class UPnP:
    """ Class that handles UPnP Port Mapping """

    request_body = ('<?xml version="1.0"?>\r\n'
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
                    + '</s:Envelope>\r\n')

    def __init__(self, core, config):

        self.core = core
        self.config = config
        self.timer = None

        self.add_port_mapping()

    def _request_port_mapping(self, router, protocol, public_port, private_ip, private_port,
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

        if xml.find(".//{http://schemas.xmlsoap.org/soap/envelope/}Body") is None:
            raise Exception(_("Invalid response: %s") % response.encode('utf-8'))

        log.add_debug("UPnP: Add port mapping response: %s", response.encode('utf-8'))

        error_code = xml.findtext(".//{urn:schemas-upnp-org:control-1-0}errorCode")
        error_description = xml.findtext(".//{urn:schemas-upnp-org:control-1-0}errorDescription")

        if error_code or error_description:
            raise Exception(_("Error code %(code)s: %(description)s") %
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

    def _update_port_mapping(self, listening_port):
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

            # Find local IP address
            local_ip_address = self.find_local_ip_address()

            # Find router
            router = self.find_router(local_ip_address)

            if not router:
                raise RuntimeError(_("UPnP is not available on this network"))

            # Perform the port mapping
            log.add_debug("UPnP: Trying to redirect external WAN port %s TCP => %s port %s TCP", (
                listening_port,
                local_ip_address,
                listening_port
            ))

            try:
                self._request_port_mapping(
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

        except Exception as error:
            from traceback import format_exc
            log.add(_("UPnP: Failed to forward external port %(external_port)s: %(error)s"), {
                "external_port": listening_port,
                "error": error
            })
            log.add_debug(format_exc())
            return

        log.add(_("UPnP: External port %(external_port)s successfully forwarded to local "
                  "IP address %(ip_address)s port %(local_port)s"), {
            "external_port": listening_port,
            "ip_address": local_ip_address,
            "local_port": listening_port
        })

    def add_port_mapping(self):

        # Test if we want to do a port mapping
        if not self.config.sections["server"]["upnp"]:
            return

        # Do the port mapping
        thread = threading.Thread(target=self._add_port_mapping)
        thread.name = "UPnPAddPortmapping"
        thread.daemon = True
        thread.start()

        # Repeat
        self._start_timer()

    def _add_port_mapping(self):
        self._update_port_mapping(self.core.protothread.listenport)

    def _start_timer(self):
        """ Port mapping entries last 24 hours, we need to regularly renew them.
        The default interval is 4 hours. """

        self.cancel_timer()
        upnp_interval = self.config.sections["server"]["upnp_interval"]

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

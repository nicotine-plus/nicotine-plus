# MIT License
#
# Copyright (C) 2020-2021 Nicotine+ Team
# Copyright (c) 2019 Dave Mulford
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Adapted from the pyupnp project at https://github.com/davemulford/pyupnp
# Uses the ssdp project on GitHub as a reference https://github.com/codingjoe/ssdp

import time
import select
import socket

from pynicotine.logfacility import log
from pynicotine.utils import http_request


class Router:
    def __init__(self, ip_address, port, wan_ip_type, url_scheme, base_url, root_url):
        self.ip_address = ip_address
        self.port = port
        self.search_target = wan_ip_type
        self.url_scheme = url_scheme
        self.base_url = base_url
        self.root_url = root_url
        self.serial_number = ""
        self.uuid = ""
        self.svc_type = ""
        self.control_url = ""

    @classmethod
    def parse_ssdp_response(cls, ssdp_response, sender):
        response_headers = {k.upper(): v for k, v in ssdp_response.headers}

        if 'LOCATION' not in response_headers:
            log.add_debug('The M-SEARCH response from %s:%d did not contain a Location header.', (sender[0], sender[1]))
            log.add_debug(ssdp_response)
            return None

        from urllib.parse import urlsplit
        urlparts = urlsplit(response_headers['LOCATION'])

        return Router(
            ip_address=sender[0],
            port=sender[1],
            wan_ip_type=response_headers['ST'],
            url_scheme=urlparts.scheme,
            base_url=urlparts.netloc,
            root_url=urlparts.path
        )


class SSDP:
    multicast_host = '239.255.255.250'
    multicast_port = 1900
    buffer_size = 4096
    response_time_secs = 2
    sleep_time_secs = 0.01

    @classmethod
    def list(cls, private_ip=None):
        """ list finds all devices responding to an SSDP search """

        log.add_debug('UPnP: Discovering... delay=%s seconds', SSDP.response_time_secs)

        # Create a UDP socket and set its timeout
        sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        sock.setblocking(False)

        if private_ip:
            sock.bind((private_ip, 0))

        # Create the WANIPConnection:1 and WANIPConnection:2 request objects
        headers = {
            'HOST': "{}:{}".format(SSDP.multicast_host, SSDP.multicast_port),
            'ST': None,
            'MAN': '"ssdp:discover"',
            'MX': str(SSDP.response_time_secs)
        }

        # Protocol 1
        wan_ip1_sent = False
        wan_ip1 = SSDP._create_msearch_request('urn:schemas-upnp-org:service:WANIPConnection:1', headers=headers)

        wan_ppp1_sent = False
        wan_ppp1 = SSDP._create_msearch_request('urn:schemas-upnp-org:service:WANPPPConnection:1', headers=headers)

        wan_igd1_sent = False
        wan_igd1 = SSDP._create_msearch_request('urn:schemas-upnp-org:device:InternetGatewayDevice:1', headers=headers)

        # Protocol 2
        wan_ip2_sent = False
        wan_ip2 = SSDP._create_msearch_request('urn:schemas-upnp-org:service:WANIPConnection:2', headers=headers)

        wan_igd2_sent = False
        wan_igd2 = SSDP._create_msearch_request('urn:schemas-upnp-org:device:InternetGatewayDevice:2', headers=headers)

        inputs = [sock]
        outputs = [sock]

        routers = []
        time_end = time.time() + SSDP.response_time_secs

        while time.time() < time_end:
            _timeout = 0
            readable, writable, _ = select.select(inputs, outputs, inputs, _timeout)

            for _sock in readable:
                msg, sender = _sock.recvfrom(SSDP.buffer_size)
                response = SSDPResponse.parse(msg.decode('utf-8'))
                log.add_debug('UPnP: Device search response: %s', bytes(response))

                router = Router.parse_ssdp_response(response, sender)

                if router:
                    routers.append(router)

            for _sock in writable:
                if not wan_ip1_sent:
                    wan_ip1.sendto(_sock, (SSDP.multicast_host, SSDP.multicast_port))
                    log.add_debug('UPnP: Sent M-SEARCH IP request 1')
                    time_end = time.time() + SSDP.response_time_secs
                    wan_ip1_sent = True

                if not wan_ppp1_sent:
                    wan_ppp1.sendto(_sock, (SSDP.multicast_host, SSDP.multicast_port))
                    log.add_debug('UPnP: Sent M-SEARCH PPP request 1')
                    time_end = time.time() + SSDP.response_time_secs
                    wan_ppp1_sent = True

                if not wan_igd1_sent:
                    wan_igd1.sendto(_sock, (SSDP.multicast_host, SSDP.multicast_port))
                    log.add_debug('UPnP: Sent M-SEARCH IGD request 1')
                    time_end = time.time() + SSDP.response_time_secs
                    wan_igd1_sent = True

                if not wan_ip2_sent:
                    wan_ip2.sendto(_sock, (SSDP.multicast_host, SSDP.multicast_port))
                    log.add_debug('UPnP: Sent M-SEARCH IP request 2')
                    time_end = time.time() + SSDP.response_time_secs
                    wan_ip2_sent = True

                if not wan_igd2_sent:
                    wan_igd2.sendto(_sock, (SSDP.multicast_host, SSDP.multicast_port))
                    log.add_debug('UPnP: Sent M-SEARCH IGD request 2')
                    time_end = time.time() + SSDP.response_time_secs
                    wan_igd2_sent = True

            # Cooldown
            time.sleep(cls.sleep_time_secs)

        for router in list(routers):
            serial_number, control_url, uuid, svc_type = SSDP._get_router_service_description(
                router.url_scheme, router.base_url, router.root_url
            )

            if svc_type is None:
                # Invalid entry
                routers.remove(router)
                continue

            router.serial_number = serial_number
            router.control_url = control_url
            router.uuid = uuid
            router.svc_type = svc_type

        sock.close()
        log.add_debug('UPnP: %s device(s) detected', str(len(routers)))

        return routers

    @classmethod
    def _create_msearch_request(cls, service_type, headers=None):
        if headers is None:
            headers = {}

        headers["ST"] = service_type
        return SSDPRequest('M-SEARCH', headers=headers)

    @classmethod
    def _get_router_service_description(cls, url_scheme, base_url, root_url):
        """ Examines the given router to find the control URL, serial number, and UUID """

        from xml.etree import ElementTree

        # Parse the returned XML and find the <URLBase> and <controlURL> elements
        try:
            response = http_request(url_scheme, base_url, root_url, timeout=2)
            xml = ElementTree.fromstring(response)

        except Exception as error:
            # Invalid response
            log.add_debug('UPnP: Invalid router description response from %s://%s%s: %s',
                          (url_scheme, base_url, root_url, error))
            return (None, None, None, None)

        serial_number = next(
            (x.text for x in xml.findall(".//{urn:schemas-upnp-org:device-1-0}serialNumber")),
            None
        )

        # The UUID field contains the text "uuid:" before the actual UUID value. This is removed
        # and just the actual UUID is returned.
        # Example: uuid:11111111-2222-3333-4444-555555555555 becomes 11111111-2222-3333-4444-555555555555
        uuid = next(
            (x.text for x in xml.findall(".//{urn:schemas-upnp-org:device-1-0}UDN")),
            None
        )

        if uuid:
            uuid = uuid.split(":")[1]

        for svc in xml.findall(".//{urn:schemas-upnp-org:device-1-0}service"):
            svc_type = svc.find(".//{urn:schemas-upnp-org:device-1-0}serviceType").text
            control_url = svc.find(".//{urn:schemas-upnp-org:device-1-0}controlURL").text

            if SSDP._is_wanip_service(svc_type):
                return (serial_number, control_url, uuid, svc_type)

        return (None, None, None, None)

    @classmethod
    def _is_wanip_service(cls, svc_type):
        return svc_type in ("urn:schemas-upnp-org:service:WANIPConnection:1",
                            "urn:schemas-upnp-org:service:WANPPPConnection:1",
                            "urn:schemas-upnp-org:service:WANIPConnection:2")


class SSDPMessage:
    """ Simplified HTTP message to serve as a SSDP message """

    def __init__(self, version='HTTP/1.1', headers=None):
        if headers is None:
            headers = []
        elif isinstance(headers, dict):
            headers = headers.items()

        self.version = version
        self.headers = list(headers)

    @classmethod
    def parse_headers(cls, msg):
        """
        Parse HTTP headers.
        Args:
            msg (str): HTTP message.
        Returns:
            (List[Tuple[str, str]): List of header tuples.
        """

        import email.parser

        return list(email.parser.Parser().parsestr(msg).items())

    def __bytes__(self):
        """ Return complete HTTP message as bytes """
        return self.__str__().encode('utf-8').replace(b'\n', b'\r\n')


class SSDPResponse(SSDPMessage):
    """ Simple Service Discovery Protocol (SSDP) response """

    def __init__(self, status_code, reason, **kwargs):
        self.status_code = int(status_code)
        self.reason = reason
        super().__init__(**kwargs)

    @classmethod
    def parse(cls, msg):
        """ Parse message string to response object """
        lines = msg.splitlines()
        version, status_code, reason = lines[0].split()
        headers = cls.parse_headers('\r\n'.join(lines[1:]))

        return cls(version=version, status_code=status_code,
                   reason=reason, headers=headers)

    def __str__(self):
        """ Return complete SSDP response """

        lines = []
        lines.append(' '.join(
            [self.version, str(self.status_code), self.reason]
        ))
        for header in self.headers:
            lines.append('%s: %s' % header)
        return '\n'.join(lines)


class SSDPRequest(SSDPMessage):
    """ Simple Service Discovery Protocol (SSDP) request """

    def __init__(self, method, uri='*', version='HTTP/1.1', headers=None):
        self.method = method
        self.uri = uri
        super().__init__(version=version, headers=headers)

    @classmethod
    def parse(cls, msg):
        """ Parse message string to request object """

        lines = msg.splitlines()
        method, uri, version = lines[0].split()
        headers = cls.parse_headers('\r\n'.join(lines[1:]))

        return cls(version=version, uri=uri, method=method, headers=headers)

    def sendto(self, transport, addr):
        """
        Send request to a given address via given transport.
        Args:
            transport (asyncio.DatagramTransport):
                Write transport to send the message on.
            addr (Tuple[str, int]):
                IP address and port pair to send the message to.
        """
        msg = bytes(self) + b'\r\n\r\n'
        log.add_debug('UPnP: SSDP request: %s', msg)
        transport.sendto(msg, addr)

    def __str__(self):
        """ Return complete SSDP request """

        lines = []
        lines.append(' '.join(
            [self.method, self.uri, self.version]
        ))
        for header in self.headers:
            lines.append('%s: %s' % header)
        return '\n'.join(lines)

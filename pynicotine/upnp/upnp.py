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

from pynicotine.logfacility import log
from pynicotine.upnp.ssdp import SSDP
from pynicotine.utils import http_request


class PortMapping:
    def __init__(self,
                 remote_host='*',
                 public_port=0,
                 protocol='',
                 private_ip='',
                 private_port=0,
                 is_enabled=None,
                 description='',
                 lease_duration=-1
                 ):

        self.remote_host = remote_host
        self.public_port = public_port
        self.protocol = protocol
        self.private_ip = private_ip
        self.private_port = private_port
        self.is_enabled = is_enabled
        self.description = description
        self.lease_duration = lease_duration

    @classmethod
    def parse_port_map_xml(cls, xml_text, router_type):
        """ Parses a UPnP GetGenericPortMappingEntry xml response """

        from xml.etree import ElementTree

        doc = ElementTree.fromstring(xml_text)

        generic_portmap_tag_text = "{{{}}}GetGenericPortMappingEntryResponse".format(router_type)

        response_tag = doc[0][0]

        if response_tag.tag == generic_portmap_tag_text:
            remote_host = '*'
            public_port = 0
            protocol = ''
            private_ip = ''
            private_port = 0
            is_enabled = None
            description = ''
            lease_duration = 86400  # Expires in 24 hours

            for prop in response_tag:
                if prop.tag == 'NewRemoteHost':
                    remote_host = prop.text if prop.text else '*'

                elif prop.tag == 'NewExternalPort':
                    public_port = prop.text if prop.text else 0

                elif prop.tag == 'NewProtocol':
                    protocol = prop.text if prop.text else '-'

                elif prop.tag == 'NewInternalPort':
                    private_port = prop.text if prop.text else 0

                elif prop.tag == 'NewInternalClient':
                    private_ip = prop.text if prop.text else '*'

                elif prop.tag == 'NewEnabled':
                    is_enabled = prop.text if prop.text else '-'

                elif prop.tag == 'NewPortMappingDescription':
                    description = prop.text if prop.text else 'None'

                elif prop.tag == 'NewLeaseDuration':
                    lease_duration = prop.text if prop.text else '-'

            return PortMapping(
                remote_host=remote_host,
                public_port=public_port,
                protocol=protocol,
                private_ip=private_ip,
                private_port=private_port,
                is_enabled=is_enabled,
                description=description,
                lease_duration=lease_duration
            )

        return None


class UPnp:

    _add_port_mapping_template = (
        '<?xml version="1.0"?>\r\n'
        '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
        's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"><s:Body><u:AddPortMapping '
        'xmlns:u="urn:schemas-upnp-org:service:WANIPConnection:1"><NewRemoteHost></NewRemoteHost>'
        '<NewExternalPort>{}</NewExternalPort><NewProtocol>{}</NewProtocol><NewInternalPort>{}</NewInternalPort>'
        '<NewInternalClient>{}</NewInternalClient><NewEnabled>1</NewEnabled>'
        '<NewPortMappingDescription>{}</NewPortMappingDescription><NewLeaseDuration>{}</NewLeaseDuration>'
        '</u:AddPortMapping></s:Body></s:Envelope>\r\n')
    _delete_port_mapping_template = (
        '<?xml version="1.0"?>\r\n'
        '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
        's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"><s:Body>'
        '<u:DeletePortMapping xmlns:u="urn:schemas-upnp-org:service:WANIPConnection:1"><NewRemoteHost></NewRemoteHost>'
        '<NewExternalPort>{}</NewExternalPort><NewProtocol>{}</NewProtocol>'
        '</u:DeletePortMapping></s:Body></s:Envelope>\r\n')
    _list_port_mappings_template = (
        '<?xml version="1.0"?>\r\n'
        '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
        's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"><s:Body>'
        '<u:GetGenericPortMappingEntry xmlns:u="urn:schemas-upnp-org:service:WANIPConnection:1">'
        '<NewPortMappingIndex>{}</NewPortMappingIndex></u:GetGenericPortMappingEntry></s:Body></s:Envelope>\r\n')

    @classmethod
    def add_port_mapping(cls, router, protocol, public_port, private_ip, private_port,
                         mapping_description, lease_duration):
        """ Adds a port mapping to a router """

        from xml.etree import ElementTree

        log.add_debug("Adding port mapping (%s, %s, %s, %s, %s)",
                      (router.uuid, protocol, public_port, private_ip, private_port))

        url = '{}{}'.format(router.base_url, router.control_url)
        log.add_debug('Adding port mapping (%s %s/%s) at url "%s"', (private_ip, private_port, protocol, url))

        headers = {
            'Host': '{}:{}'.format(router.ip_address, router.port),
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPACTION': '"{}#AddPortMapping"'.format(router.svc_type)
        }

        data = UPnp._add_port_mapping_template.format(public_port, protocol, private_port, private_ip,
                                                      mapping_description, lease_duration).encode('utf-8')

        log.add_debug('UPnP: Add port mapping request headers: %s', headers)
        log.add_debug('UPnP: Add port mapping request contents: %s', data)

        response = http_request(
            router.url_scheme, router.base_url, router.control_url,
            request_type="POST", body=data, headers=headers
        )

        log.add_debug('UPnP: Add port mapping response: %s', response.encode('utf-8'))

        xml = ElementTree.fromstring(response)

        error_code = next(
            (x.text for x in xml.findall(".//{urn:schemas-upnp-org:control-1-0}errorCode")),
            None
        )

        error_description = next(
            (x.text for x in xml.findall(".//{urn:schemas-upnp-org:control-1-0}errorDescription")),
            None
        )

        if error_code or error_description:
            raise Exception('Error code %(code)s: %(description)s' %
                            {'code': error_code, 'description': error_description})

    @classmethod
    def delete_port_mapping(cls, router, protocol, public_port):
        """ Deletes a port mapping from a router """

        log.add_debug("Deleting port mapping (%s, %s, %s)", (router, protocol, public_port))

        url = '{}{}'.format(router.base_url, router.control_url)
        log.add_debug('Deleting port mapping (%s/%s) at url "%s"', (public_port, protocol, url))

        headers = {
            'Host': '{}:{}'.format(router.ip_address, router.port),
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPACTION': '"{}#DeletePortMapping"'.format(router.svc_type)
        }

        data = UPnp._delete_port_mapping_template.format(public_port, protocol).encode('utf-8')
        log.add_debug('UPnP: Delete port mapping request headers: %s', headers)
        log.add_debug('UPnP: Delete port mapping request contents: %s', data)

        response = http_request(
            router.url_scheme, router.base_url, router.control_url,
            request_type="POST", body=data, headers=headers
        )

        log.add_debug('UPnP: Delete port mapping response: %s', response.encode('utf-8'))

    @classmethod
    def list_port_mappings(cls, router):
        """ Lists the port mappings for a router """

        log.add_debug('Listing existing port mappings...')

        headers = {
            'Host': '{}:{}'.format(router.ip_address, router.port),
            'Content-Type': 'text/xml; charset=utf-8',
            'SOAPACTION': '"{}#GetGenericPortMappingEntry"'.format(router.svc_type)
        }

        index = -1
        portmap_found = True
        portmaps = []

        while portmap_found:
            index += 1
            data = UPnp._list_port_mappings_template.format(index).encode('utf-8')
            log.add_debug('UPnP: List port mappings request headers: %s', headers)
            log.add_debug('UPnP: List port mappings request contents: %s', data)

            response = http_request(
                router.url_scheme, router.base_url, router.control_url,
                request_type="POST", body=data, headers=headers
            )

            log.add_debug('UPnP: List port mappings response: %s', response.encode('utf-8'))

            portmap = PortMapping.parse_port_map_xml(response, router.svc_type)

            if not portmap:
                portmap_found = False
            else:
                portmaps.append(portmap)

        log.add_debug('Existing port mappings: %s', portmaps)

        return portmaps

    @classmethod
    def find_router(cls, private_ip=None):
        routers = SSDP.list(private_ip)
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

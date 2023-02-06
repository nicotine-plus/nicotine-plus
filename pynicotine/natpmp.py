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

from threading import Thread

from pynicotine.config import config
from pynicotine.events import events
from pynicotine.logfacility import log

RENEWAL_INTERVAL = 14400  # 4 hours

import os
import re
import struct
import socket
import select
import platform

# Modified version of NAT-PMP client library from https://github.com/yimingliu/py-natpmp
# 
# Provides functions to interact with NAT-PMP gateways implementing version 0
# of the NAT-PMP draft specification.
# 
# This version does not completely implement the draft standard.
# * It does not provide functionality to listen for address change packets.
# * It does not have a proper request queuing system, meaning that
# multiple requests may be issued in parallel, against spec recommendations.
# 
# For more information on NAT-PMP, see the NAT-PMP draft specification:
# http://files.dns-sd.org/draft-cheshire-nat-pmp.txt

# Copyright (c) 2008-2016, Yiming Liu, All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
# 
# * Redistributions of source code must retain the above copyright notice,
#   this list of conditions and the following disclaimer.
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# * The names of the author and contributors may not be used to endorse or promote
#   products derived from this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS 'AS IS'
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

NATPMP_PORT = 5351

NATPMP_RESERVED_VAL = 0

OP_UDP = 1
OP_TCP = 2

def op_str(op):
    if op == OP_UDP:
        return "UDP"
    elif op == OP_TCP:
        return "TCP"

    return None

class Result:
    SUCCESS = 0  # Success
    UNSUPPORTED_VERSION = 1  # Unsupported Version
    NOT_AUTHORIZED = 2  # Not Authorized/Refused/NATPMP turned off
    NETWORK_FAILURE = 3  # Network Failure
    OUT_OF_RESOURCES = 4  # can not create more mappings
    UNSUPPORTED_OP = 5  # not a supported opcode
    # all remaining results are fatal errors
    GATEWAY_NO_VALID_GATEWAY = -10
    GATEWAY_NO_SUPPORT = -11
    GATEWAY_CANNOT_FIND = -12

    MSG_DICT = {
            SUCCESS: "Success.",

            UNSUPPORTED_VERSION: "The protocol version specified is unsupported.",
            NOT_AUTHORIZED: "The operation was refused. NAT-PMP may be turned off on gateway.",
            NETWORK_FAILURE: "There was a network failure. The gateway may not have an IP address.",
            OUT_OF_RESOURCES: "The NAT-PMP gateway is out of resources "
            "and cannot create more mappings.",
            UNSUPPORTED_OP: "The NAT-PMP gateway does not support this operation.",

            GATEWAY_NO_SUPPORT: "The gateway does not support NAT-PMP",
            GATEWAY_NO_VALID_GATEWAY: "No valid gateway address was specified.",
            GATEWAY_CANNOT_FIND: "Cannot automatically determine "
            "gateway address.  Must specify manually."
            }


class NATPMPRequest(object):
    """Represents a basic NAT-PMP request.  This currently consists of the
       1-byte fields version and opcode.

       Other requests are derived from NATPMPRequest.
    """

    initial_timeout = 0.250  # seconds

    def __init__(self, version, opcode):
        self.version = version
        self.opcode = opcode

    def toBytes(self):
        """Converts the request object to a byte string."""
        return struct.pack('!BB', self.version, self.opcode)


class PublicAddressRequest(NATPMPRequest):
    """Represents a NAT-PMP request to the local gateway for a public address.
       As per the specification, this is a generic request with the opcode = 0.
    """
    def __init__(self, version=0):
        NATPMPRequest.__init__(self, version, 0)


class PortMapRequest(NATPMPRequest):
    """Represents a NAT-PMP request to the local gateway for a port mapping.
       As per the specification, this request extends NATPMPRequest with
       the fields private_port, public_port, and lifetime.  The first two
       are 2-byte unsigned shorts, and the last is a 4-byte unsigned integer.
    """
    def __init__(self, protocol, private_port, public_port, lifetime=3600,
                 version=0):
        NATPMPRequest.__init__(self, version, protocol)
        self.private_port = private_port
        self.public_port = public_port
        self.lifetime = lifetime

    def toBytes(self):
        return NATPMPRequest.toBytes(self) +\
                struct.pack('!HHHI',
                        NATPMP_RESERVED_VAL, self.private_port,
                        self.public_port, self.lifetime)


class NATPMPResponse(object):
    """Represents a generic NAT-PMP response from the local gateway.  The
       generic response has fields for version, opcode, result, and secs
       since last epoch (last boot of the NAT gateway).  As per the
       specification, the opcode is offset by 128 from the opcode of
       the original request.
    """

    def __init__(self, version, opcode, result, sec_since_epoch):
        self.version = version
        self.opcode = opcode
        self.result = result
        self.sec_since_epoch = sec_since_epoch

    def successful(self):
        return self.result == Result.SUCCESS

    def __str__(self):
        return "NATPMPResponse({}, {}, {}, {})".format(
                self.version, self.opcode, self.result, self.sec_since_epoch)

class PublicAddressResponse(NATPMPResponse):
    """Represents a NAT-PMP response from the local gateway to a
       public-address request.  It has one additional 4-byte field
       containing the IP returned.

       The member variable ip contains the Python-friendly string form, while
       ip_int contains the same in the original 4-byte unsigned int.
    """

    SIZE = 12

    def __init__(self, data):
        data = data[:self.SIZE]
        version, opcode, result, sec_since_epoch, self.ip_int =\
            struct.unpack("!BBHII", data)
        NATPMPResponse.__init__(self, version, opcode, result, sec_since_epoch)
        self.ip = socket.inet_ntoa(data[8:8+4])
        # self.ip  = socket.inet_ntoa(self.ip_bytes)

    def __str__(self):
        return "PublicAddressResponse: version {}, opcode {} ({})," \
                " result {}, ssec {}, ip {}".format(
                        self.version, self.opcode, op_str(self.opcode),
                        self.result, self.sec_since_epoch, self.ip)


class PortMapResponse(NATPMPResponse):
    """Represents a NAT-PMP response from the local gateway to a
       public-address request.  The response contains the private port,
       public port, and the lifetime of the mapping in addition to typical
       NAT-PMP headers.  Note that the port mapping assigned is
       NOT NECESSARILY the port requested (see the specification
       for details).
    """

    SIZE = 16

    def __init__(self, data):
        data = data[:self.SIZE]

        version, opcode, result, sec_since_epoch, self.private_port,\
            self.public_port, self.lifetime = struct.unpack('!BBHIHHI', data)
        NATPMPResponse.__init__(self, version, opcode, result, sec_since_epoch)

    def __str__(self):
        msg = "PortMapResponse: version %d, opcode %d (%d),"
        msg += " result %d, ssec %d, private_port %d, public port %d,"
        msg += " lifetime %d"

        return msg % (self.version, self.opcode, self.opcode, self.result,
                      self.sec_since_epoch, self.private_port, self.public_port,
                      self.lifetime)


class NATPMPError(Exception):
    """Generic exception state.  May be used to represent unknown errors."""

    def __init__(self, result_code, msg, *args):
        self.result_code = result_code
        self.msg = msg
        self.args = args


class NATPMPResultError(NATPMPError):
    """Used when a NAT gateway responds with an error-state response."""
    pass


class NATPMPNetworkError(NATPMPError):
    """Used when a network error occurred while communicating
       with the NAT gateway."""
    pass


class NATPMPUnsupportedError(NATPMPError):
    """Used when a NAT gateway does not support NAT-PMP."""
    pass


def get_gateway_addr():
    """Use netifaces to get the gateway address, if we can't import it then
       fall back to a hack to obtain the current gateway automatically, since
       Python has no interface to sysctl().

       This may or may not be the gateway we should be contacting.
       It does not guarantee correct results.

       This function requires the presence of netstat on the path on POSIX
    and NT.
    """
    try:
        import netifaces
        return netifaces.gateways()["default"][netifaces.AF_INET][0]
    except ImportError:
        shell_command = 'netstat -rn'
        if os.name == "posix":
            pattern = \
                re.compile('(?:default|0\.0\.0\.0|::/0)\s+([\w\.:]+)\s+.*UG')
        elif os.name == "nt":
            if platform.version().startswith("6.1"):
                pattern = re.compile(".*?0.0.0.0[ ]+0.0.0.0[ ]+(.*?)[ ]+?.*?\n")
            else:
                pattern = re.compile(".*?Default Gateway:[ ]+(.*?)\n")
        system_out = os.popen(shell_command, 'r').read()
        if not system_out:
            raise NATPMPNetworkError(Result.GATEWAY_CANNOT_FIND,
                                     error_str(Result.GATEWAY_CANNOT_FIND))
        match = pattern.search(system_out)
        if not match:
            raise NATPMPNetworkError(Result.GATEWAY_CANNOT_FIND,
                                     error_str(Result.GATEWAY_CANNOT_FIND))
        addr = match.groups()[0].strip()
        return addr


def error_str(result_code):
    """Takes a numerical error code and returns a human-readable
       error string.
    """
    result = Result.MSG_DICT.get(result_code)
    if not result:
        result = "Unknown fatal error."
    return result


def get_gateway_socket(gateway):
    """Takes a gateway address string and returns a non-blocking UDP
       socket to communicate with its NAT-PMP implementation on
       NATPMP_PORT.

       e.g. addr = get_gateway_socket('10.0.1.1')
    """
    if not gateway:
        raise NATPMPNetworkError(Result.GATEWAY_NO_VALID_GATEWAY,
                                 error_str(Result.GATEWAY_NO_VALID_GATEWAY))
    response_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    response_socket.setblocking(0)
    response_socket.connect((gateway, NATPMP_PORT))
    return response_socket


def get_public_address(gateway_ip=None, retry=9):
    """A high-level function that returns the public interface IP of
       the current host by querying the NAT-PMP gateway.  IP is
       returned as string.

       Takes two possible keyword arguments:
            gateway_ip - the IP to the NAT-PMP compatible gateway.
                         Defaults to using auto-detection function
                         get_gateway_addr()
            retry - the number of times to retry the request if unsuccessful.
                    Defaults to 9 as per specification.
    """
    if gateway_ip is None:
        gateway_ip = get_gateway_addr()

    addr_request = PublicAddressRequest()
    addr_response = send_request_with_retry(
            gateway_ip, addr_request,
            response_data_class=PublicAddressResponse,
            retry=retry, response_size=PublicAddressResponse.SIZE)

    if addr_response.result != 0:
        # sys.stderr.write("NAT-PMP error %d: %s\n" %
        #                  (addr_response.result,
        #                   error_str(addr_response.result)))
        # sys.stderr.flush()
        raise NATPMPResultError(addr_response.result,
                                error_str(addr_response.result), addr_response)
    addr = addr_response.ip
    return addr


def map_tcp_port(public_port, private_port, lifetime=3600, gateway_ip=None,
                 retry=9, use_exception=True):
    """A high-level wrapper to map_port() that requests a mapping
       for a public TCP port on the NAT to a private TCP port on this host.
       Returns the complete response on success.

            public_port - the public port of the mapping requested
            private_port - the private port of the mapping requested
            lifetime - the duration of the mapping in seconds.
                       Defaults to 3600, per specification.
            gateway_ip - the IP to the NAT-PMP compatible gateway.
                        Defaults to using auto-detection function
                        get_gateway_addr()
            retry - the number of times to retry the request if unsuccessful.
                    Defaults to 9 as per specification.
            use_exception - throw an exception if an error result is
                           received from the gateway.  Defaults to True.
    """
    return map_port(OP_TCP, public_port, private_port, lifetime,
                    gateway_ip=gateway_ip, retry=retry,
                    use_exception=use_exception)


def map_udp_port(public_port, private_port, lifetime=3600, gateway_ip=None,
                 retry=9, use_exception=True):
    """A high-level wrapper to map_port() that requests a mapping for
       a public UDP port on the NAT to a private UDP port on this host.
       Returns the complete response on success.

            public_port - the public port of the mapping requested
            private_port - the private port of the mapping requested
            lifetime - the duration of the mapping in seconds.
                       Defaults to 3600, per specification.
            gateway_ip - the IP to the NAT-PMP compatible gateway.
                         Defaults to using auto-detection function
                         get_gateway_addr()
            retry - the number of times to retry the request if unsuccessful.
                    Defaults to 9 as per specification.
            use_exception - throw an exception if an error result is
                            received from the gateway.  Defaults to True.
    """
    return map_port(OP_UDP, public_port, private_port, lifetime,
                    gateway_ip=gateway_ip, retry=retry,
                    use_exception=use_exception)


def map_port(protocol, public_port, private_port, lifetime=3600,
             gateway_ip=None, retry=9, use_exception=True):
    """A function to map public_port to private_port of protocol.
       Returns the complete response object, it's up to the caller
       to check the result code.

            protocol - OP_UDP or OP_TCP
            public_port - the public port of the mapping requested
            private_port - the private port of the mapping requested
            lifetime - the duration of the mapping in seconds.
                       Defaults to 3600, per specification.
            gateway_ip - the IP to the NAT-PMP compatible gateway.
                         Defaults to using auto-detection function
                         get_gateway_addr()
            retry - the number of times to retry the request if unsuccessful.
                    Defaults to 9 as per specification.
            use_exception - throw an exception if an error result
                            is received from the gateway.  Defaults to True.
    """

    if protocol not in [OP_UDP, OP_TCP]:
        raise ValueError("Invalid protocol: {}. Must be either OP_UDP or OP_TCP".format(protocol))

    if gateway_ip is None:
        gateway_ip = get_gateway_addr()

    request = PortMapRequest(protocol, private_port, public_port, lifetime)
    response = send_request_with_retry(
            gateway_ip, request, response_data_class=PortMapResponse,
            retry=retry, response_size=PortMapResponse.SIZE)

    #if response.result != 0 and use_exception:
    #    raise NATPMPResultError(response.result, error_str(response.result), response)

    return response


def send_request(gateway_socket, request):
    gateway_socket.sendall(request.toBytes())


def read_response(gateway_socket, timeout, response_size=16):
    data = ""
    source_addr = ("", "")
    rlist, wlist, xlist = select.select([gateway_socket], [], [], timeout)

    if rlist:
        resp_socket = rlist[0]
        try:
            data, source_addr = resp_socket.recvfrom(response_size)
        except Exception:
            return None, None

    return data, source_addr


def send_request_with_retry(gateway_ip, request, response_data_class=None,
                            retry=9, response_size=16):
    gateway_socket = get_gateway_socket(gateway_ip)
    n = 1
    timeout = request.initial_timeout
    data = ""

    while n <= retry and not data:
        send_request(gateway_socket, request)
        data, source_addr = read_response(gateway_socket,
                                          timeout,
                                          response_size=response_size)

        if data is None or source_addr[0] != gateway_ip or\
                source_addr[1] != NATPMP_PORT:
            data = ""  # discard data if source mismatch, as per specification

        n += 1
        timeout *= 2

    if n >= retry and not data:
        raise NATPMPUnsupportedError(Result.GATEWAY_NO_SUPPORT,
                                     error_str(Result.GATEWAY_NO_SUPPORT))

    if data and response_data_class:
        data = response_data_class(data)

    return data


class NatPMP:
    VALID_PROTOS = ["TCP", "UDP"]

    def __init__(self):
        self.proto = "TCP"
        self.public_port = None
        self.private_port = None
        self._timer = None

    @staticmethod
    def _request_port_mapping(proto, public_port, private_port, lifetime):
        proto = proto.upper()

        if proto not in NatPMP.VALID_PROTOS:
            raise Exception("Invalid protocol for forwarding: {}".format(proto))

        if not is_valid_port(public_port):
            raise Exception("Invalid port for forwarding: {}".format(public_port))

        if not is_valid_port(private_port):
            raise Exception("Invalid port for forwarding: {}".format(private_port))

        if proto == "TCP":
            proto = OP_TCP
        else:
            proto = OP_UDP

        return map_port(proto, public_port, private_port, lifetime)

    def _update_port_mapping(self, lease_duration=86400):
        """
        This function supports creating a Port Mapping via the NAT-PMP protocol.
        We set the lease period to 24 hours, and regularly renew the port mapping.
        """

        try:
            log.add_debug("NatPMP: Creating Port Mapping rule...")

            # Perform the port mapping
            log.add_debug("NatPMP: Trying to map internal {} port {} to external port {}".format(
                self.proto, self.private_port, self.public_port))

            response = self._request_port_mapping(
                proto=self.proto,
                public_port=self.public_port,
                private_port=self.private_port,
                lifetime=lease_duration
            )

            if not response.successful():
                log.add_debug("NatPMP: Port Mapping failed. {}: {}".format(
                    response.result, error_str(response.result)))
                raise RuntimeError("Error code {}: {}".format(
                    response.result, error_str(response.result)))

        except Exception as error:
            from traceback import format_exc
            log.add("NatPMP: Failed to map internal {} port {} to external port {}: {}".format(
                self.proto, self.private_port, self.public_port, error))
            log.add_debug(format_exc())
            return

        log.add("NatPMP: Internal {} port {} was successfully mapped to external port {}".format(
            self.proto, self.private_port, self.public_port))

    def add_port_mapping(self, blocking=False):

        # Test if we want to do a port mapping
        if not config.sections["server"]["natpmp"]:
            log.add_debug("NatPMP: disabled by configuration")
            return

        # Do the port mapping
        if blocking:
            self._update_port_mapping()
        else:
            Thread(target=self._update_port_mapping, name="NatPMPAddPortmapping", daemon=True).start()

        self._start_timer()

    def _start_timer(self):
        """ Port mapping entries last 24 hours, we need to regularly renew them.
        The default interval is 4 hours. """

        self.cancel_timer()
        self._timer = events.schedule(delay=RENEWAL_INTERVAL, callback=self.add_port_mapping)

    def cancel_timer(self):
        events.cancel_scheduled(self._timer)


def is_valid_port(p):
    return p in range(1, 65535)

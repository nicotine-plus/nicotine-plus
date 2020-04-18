# COPYRIGHT (C) 2016-2017 Michael Labouebe <gfarmerfr@free.fr>
# COPYRIGHT (C) 2009-2010 Quinox <quinox@users.sf.net>
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

import platform
import re
import socket
import subprocess
from gettext import gettext as _
from subprocess import PIPE
from subprocess import STDOUT
from subprocess import Popen

from pynicotine.logfacility import log
from pynicotine.pynicotine import slskmessages
from pynicotine.utils import findBestEncoding


class UPnPPortMapping:
    """Class that handle UPnP Port Mapping"""

    def __init__(self):
        """Initialize the UPnP Port Mapping object."""

        # Default discovery delay (ms)
        self.discoverdelay = 2000

        # Default requested external WAN port
        self.externalwanport = 15000

        # List of existing port mappings
        self.existingportsmappings = []

        # Initial value that determine if a port mapping already exist to the
        # client
        self.foundexistingmapping = False

        # Detect if we're on Windpws
        self.iswin32 = platform.system().startswith("Win")

        # Defining where the miniupnpc binary might be
        if self.iswin32:
            # On windows we use a static build of upnpc
            # That needs to be put in the upnpc subfolder
            self.upnpcbinary = 'files\\win32\\upnpc\\upnpc-static.exe'
        else:
            # On GNU/linux we try to find it in the $PATH
            self.upnpcbinary = 'upnpc'

    def run_binary(self, cmd):
        """Function used to call the upnpc binary.

        Redirect stderr to stdout since we don't really care having
        two distinct streams.

        Also prevent the command prompt from being shown on Windows.
        """

        if self.iswin32:
            # Ugly hack to hide the command prompt on Windows
            info = subprocess.STARTUPINFO()
            info.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            p = Popen(cmd, stdout=PIPE, stderr=STDOUT, startupinfo=info)
        else:
            p = Popen(cmd, stdout=PIPE, stderr=STDOUT)

        (out, err) = p.communicate()

        return out.rstrip()

    def IsPossible(self):
        """Function to check the requirements for doing a port mapping.

        It tries to import the MiniUPnPc python binding: miniupnpc.
        If it fails, it tries to use the MiniUPnPc binary: upnpc.
        If neither of them are available UPnP Port Mapping is unavailable.
        """

        try:
            # First we try to import the python binding
            import miniupnpc  # noqa: F401
        except ImportError as e1:
            try:
                # We fail to import the python module: fallback to the binary.
                self.run_binary([self.upnpcbinary])
            except Exception as e2:
                # Nothing works :/
                errors = [
                    _('Failed to import miniupnpc module: %(error)s') %
                    {'error': str(e1)},
                    _('Failed to run upnpc binary: %(error)s') %
                    {
                        'error': findBestEncoding(
                            str(e2),
                            ['utf-8', 'ascii', 'iso8859-1']
                        )
                    }
                ]
                return (False, errors)
            else:
                # If the binary is available we define the resulting mode
                self.mode = 'Binary'
                return (True, None)
        else:
            # If the python binding import is successful we define the
            # resulting mode
            self.mode = 'Module'
            return (True, None)

    def AddPortMapping(self, frame, np):
        """Wrapper to redirect the Port Mapping creation to either:

        - The MiniUPnPc binary: upnpc.
        - The python binding to the MiniUPnPc binary: miniupnpc.

        Both method support creating a Port Mapping
        via the UPnP IGDv1 and IGDv2 protocol.

        Need a reference to NicotineFrame to update the interface with the WAN
        external port chosen and connect to the slsk network.
        Also need a reference to the np object to extract the internal LAN
        local from the protothread socket.

        From the UPnP IGD reference:
        http://upnp.org/specs/gw/UPnP-gw-WANIPConnection-v2-Service.pdf

        IGDv1 and IGDV2: AddPortMapping:
        This action creates a new port mapping or overwrites
        an existing mapping with the same internal client.
        If the ExternalPort and PortMappingProtocol pair is already mapped
        to another internal client, an error is returned.

        IGDv1: NewLeaseDuration:
        This argument defines the duration of the port mapping.
        If the value of this argument is 0, it means it's a static port mapping
        that never expire.

        IGDv2: NewLeaseDuration:
        This argument defines the duration of the port mapping.
        The value of this argument MUST be greater than 0.
        A NewLeaseDuration with value 0 means static port mapping,
        but static port mappings can only be created through
        an out-of-band mechanism.
        If this parameter is set to 0, default value of 604800 MUST be used.

        BTW since we don't recheck periodically ports mappings
        while nicotine+ runs, any UPnP port mapping done with IGDv2
        (any modern router does that) will expire after 7 days.
        The client won't be able to send/receive files anymore...
        """

        log.add(_('Creating Port Mapping rule via UPnP...'))

        # Hack to found out the local LAN IP
        # See https://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib/28950776#28950776

        # Create a UDP socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Send a broadcast packet on a local address (doesn't need to be reachable)
        s.connect(('10.255.255.255', 0))

        # This returns the "primary" IP on the local box, even if that IP is a NAT/private/internal IP.
        self.internalipaddress = s.getsockname()[0]

        # Close the socket
        s.close()

        # Store the Local LAN port
        self.internallanport = np.protothread._p.getsockname()[1]

        # The function depends on what method of configuring port mapping is
        # available
        functiontocall = getattr(self, 'AddPortMapping' + self.mode)

        try:
            functiontocall()
        except Exception as e:
            log.addwarning(_('UPnP exception: %(error)s') % {'error': str(e)})
            log.addwarning(
                _('Failed to automate the creation of ' +
                    'UPnP Port Mapping rule.'))
            return

        log.add(
            _('Managed to map external WAN port %(externalwanport)s ' +
                'on your external IP %(externalipaddress)s ' +
                'to your local host %(internalipaddress)s ' +
                'port %(internallanport)s.') %
            {
                'externalwanport': self.externalwanport,
                'externalipaddress': self.externalipaddress,
                'internalipaddress': self.internalipaddress,
                'internallanport': self.internallanport
            }
        )

        # Set the external WAN port in the GUI
        frame.networkcallback([slskmessages.IncPort(self.externalwanport)])

        # Establish the connection to the slsk network
        frame.OnConnect(-1)

    def AddPortMappingBinary(self):
        """Function to create a Port Mapping via MiniUPnPc binary: upnpc.

        It tries to reconstruct a datastructure identical to what the python
        module does by parsing the output of the binary.
        This help to have a bunch of common code to find a suitable
        external WAN port later.

        IGDv1: If a Port Mapping already exist:
            It's updated with a new static port mapping that does not expire.
        IGDv2: If a Port Mapping already exist:
            It's updated with a new lease duration of 7 days.
        """

        # Listing existing ports mappings
        log.adddebug('Listing existing Ports Mappings...')

        command = [self.upnpcbinary, '-l']
        try:
            output = self.run_binary(command)
        except Exception as e:
            raise RuntimeError(
                _('Failed to use UPnPc binary: %(error)s') % {'error': str(e)})

        # Build a list of tuples of the mappings
        # with the same format as in the python module
        # (ePort, protocol, (intClient, iPort), desc, enabled, rHost, duration)
        # (15000, 'TCP', ('192.168.0.1', 2234), 'Nicotine+', '1', '', 0)
        #
        # Also get the external WAN IP
        #
        # Output format :
        # ...
        # ExternalIPAddress = X.X.X.X
        # ...
        #  i protocol exPort->inAddr:inPort description remoteHost leaseTime
        #  0 TCP 15000->192.168.0.1:2234  'Nicotine+' '' 0

        re_ip = re.compile(r"""
            ^
                ExternalIPAddress
                \s+ = \s+
                (?P<ip> \d+ \. \d+ \. \d+ \. \d+ )?
            $
        """, re.VERBOSE)

        re_mapping = re.compile(r"""
            ^
                \d+ \s+
                (?P<protocol> \w+ ) \s+
                (?P<ePort> \d+ ) ->
                (?P<intClient> \d+ \. \d+ \. \d+ \. \d+ ) :
                (?P<iPort> \d+ ) \s+
                ' (?P<desc> .* ) ' \s+
                ' (?P<rHost> .* ) ' \s+
                (?P<duration> \d+ )
            $
        """, re.VERBOSE)

        for line in output.split('\n'):

            line = line.strip()

            ip_match = re.match(re_ip, line)
            mapping_match = re.match(re_mapping, line)

            if ip_match:
                self.externalipaddress = ip_match.group('ip')
                next

            if mapping_match:
                enabled = '1'
                self.existingportsmappings.append(
                    (
                        int(mapping_match.group('ePort')),
                        mapping_match.group('protocol'),
                        (mapping_match.group('intClient'),
                         int(mapping_match.group('iPort'))),
                        mapping_match.group('desc'),
                        enabled,
                        mapping_match.group('rHost'),
                        int(mapping_match.group('duration'))
                    )
                )

        # Find a suitable external WAN port to map to based
        # on the existing mappings
        self.FindSuitableExternalWANPort()

        # Do the port mapping
        log.adddebug('Trying to redirect %s port %s TCP => %s port %s TCP' %
                     (
                         self.externalipaddress,
                         self.externalwanport,
                         self.internalipaddress,
                         self.internallanport
                     )
                     )

        command = [
            self.upnpcbinary,
            '-e',
            '"Nicotine+"',
            '-a',
            str(self.internalipaddress),
            str(self.internallanport),
            str(self.externalwanport),
            'TCP'
        ]

        try:
            output = self.run_binary(command)
        except Exception as e:
            raise RuntimeError(
                _('Failed to use UPnPc binary: %(error)s') % {'error': str(e)})

        for line in output.split('\n'):
            if line.startswith("external ") and \
               line.find(" is redirected to internal ") > -1:
                log.adddebug('Success')
                return
            if line.find(" failed with code ") > -1:
                log.adddebug('Failed')
                raise RuntimeError(
                    _('Failed to map the external WAN port: %(error)s') %
                    {'error': str(line)})

        raise AssertionError(
            _('UPnPc binary failed, could not parse output: %(output)s') %
            {'output': str(output)})

    def AddPortMappingModule(self):
        """Function to create a Port Mapping via the python binding: miniupnpc.

        IGDv1: If a Port Mapping already exist:
            It's updated with a new static port mapping that does not expire.
        IGDv2: If a Port Mapping already exist:
            It's updated with a new lease duration of 7 days.
        """

        import miniupnpc

        u = miniupnpc.UPnP()
        u.discoverdelay = self.discoverdelay

        # Discovering devices
        log.adddebug('Discovering... delay=%sms' % u.discoverdelay)

        try:
            log.adddebug('%s device(s) detected' % u.discover())
        except Exception as e:
            raise RuntimeError(
                _('UPnP exception (should never happen): %(error)s') %
                {'error': str(e)})

        # Select an IGD
        try:
            u.selectigd()
        except Exception as e:
            raise RuntimeError(
                _('Cannot select an IGD : %(error)s') %
                {'error': str(e)})

        self.externalipaddress = u.externalipaddress()
        log.adddebug('IGD selected : External IP address: %s' %
                     (self.externalipaddress))

        # Build existing ports mappings list
        log.adddebug('Listing existing Ports Mappings...')

        i = 0
        while True:
            p = u.getgenericportmapping(i)
            if p is None:
                break
            self.existingportsmappings.append(p)
            i += 1

        # Find a suitable external WAN port to map to based on the existing
        # mappings
        self.FindSuitableExternalWANPort()

        # Do the port mapping
        log.adddebug('Trying to redirect %s port %s TCP => %s port %s TCP' %
                     (
                         self.externalipaddress,
                         self.externalwanport,
                         self.internalipaddress,
                         self.internallanport
                     )
                     )

        try:
            u.addportmapping(self.externalwanport, 'TCP',
                             self.internalipaddress,
                             self.internallanport, 'Nicotine+', '')
        except Exception as e:
            log.adddebug('Failed')
            raise RuntimeError(
                _('Failed to map the external WAN port: %(error)s') %
                {'error': str(e)}
            )

        log.adddebug('Success')

    def FindSuitableExternalWANPort(self):
        """Function to find a suitable external WAN port to map to the client.

        It will detect if a port mapping to the client already exist.
        """

        # Output format: (ePort, protocol, (intClient, iPort), desc, enabled,
        # rHost, duration)
        log.adddebug('Existing Port Mappings: %s' % (
            sorted(self.existingportsmappings, key=lambda tup: tup[0])))

        # Analyze ports mappings
        for m in sorted(self.existingportsmappings, key=lambda tup: tup[0]):

            (ePort, protocol, (intClient, iPort),
             desc, enabled, rhost, duration) = m

            # A Port Mapping is already in place with the client: we will
            # rewrite it to avoid a timeout on the duration of the mapping
            if protocol == "TCP" and \
               str(intClient) == str(self.internalipaddress) and \
               iPort == self.internallanport:
                log.adddebug('Port Mapping already in place: %s' % str(m))
                self.externalwanport = ePort
                self.foundexistingmapping = True
                break

        # If no mapping already in place we try to found a suitable external
        # WAN port
        if not self.foundexistingmapping:

            # Find the first external WAN port > requestedwanport that's not
            # already reserved
            tcpportsreserved = [x[0] for x in sorted(
                self.existingportsmappings) if x[1] == "TCP"]

            while self.externalwanport in tcpportsreserved:
                if self.externalwanport + 1 <= 65535:
                    self.externalwanport += 1
                else:
                    raise AssertionError(
                        _('Failed to find a suitable external WAN port, ' +
                            'bailing out.'))

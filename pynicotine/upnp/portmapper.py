# COPYRIGHT (C) 2020 Nicotine+ Team
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

import socket

from gettext import gettext as _

from pynicotine.logfacility import log
from pynicotine.upnp.upnp import UPnp


class UPnPPortMapping:
    """ Class that handles UPnP Port Mapping """

    def __init__(self):
        """ Initialize the UPnP Port Mapping object """

        # List of existing port mappings
        self.existingportsmappings = []

        # Initial value that determine if a port mapping already exist to the
        # client
        self.foundexistingmapping = False

    def add_port_mapping(self, np):
        """
        This function supports creating a Port Mapping via the UPnP
        IGDv1 and IGDv2 protocol.

        Need a reference to the np object to extract the internal LAN
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

        try:
            self._add_port_mapping(np)

        except Exception as e:
            log.add_warning(_('UPnP exception: %(error)s'), {'error': str(e)})
            log.add_warning(_('Failed to automate the creation of UPnP Port Mapping rule.'))
            return

        log.add_debug(
            _('Managed to map external WAN port %(externalwanport)s ' +
                'to your local host %(internalipaddress)s ' +
                'port %(internallanport)s.'),
            {
                'externalwanport': self.externalwanport,
                'internalipaddress': self.internalipaddress,
                'internallanport': self.internallanport
            }
        )

    def _add_port_mapping(self, np):
        """
        Function that actually creates the port mapping.

        IGDv1: If a Port Mapping already exist:
            It's updated with a new static port mapping that does not expire.
        IGDv2: If a Port Mapping already exist:
            It's updated with a new lease duration of 7 days.
        """

        log.add(_('Creating Port Mapping rule via UPnP...'))

        # Placeholder LAN IP address, updated in AddPortMappingBinary or AddPortMappingModule
        self.internalipaddress = "127.0.0.1"

        # Store the Local LAN port
        self.internallanport = np.protothread._p.getsockname()[1]
        self.externalwanport = self.internallanport

        # Find devices
        router = UPnp.find_router()

        # Create a UDP socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Send a broadcast packet on a local address (doesn't need to be reachable, but MacOS requires port to be non-zero)
        s.connect(('10.255.255.255', 1))

        # This returns the "primary" IP on the local box, even if that IP is a NAT/private/internal IP.
        self.internalipaddress = s.getsockname()[0]

        # Close the socket
        s.close()

        # Get existing port mappings
        for i in UPnp.list_port_mappings(router):
            self.existingportsmappings.append(
                (
                    i.public_port,
                    i.protocol,
                    (i.private_ip, i.private_port),
                    i.description,
                    i.is_enabled,
                    i.remote_host,
                    i.lease_duration
                )
            )

        # Find a suitable external WAN port to map to based on the existing mappings
        self.find_suitable_external_wan_port()

        # Do the port mapping
        log.add_debug('Trying to redirect external WAN port %s TCP => %s port %s TCP', (
            self.externalwanport,
            self.internalipaddress,
            self.internallanport
        ))

        try:
            UPnp.add_port_mapping(
                router=router,
                protocol='TCP',
                public_port=self.externalwanport,
                private_ip=self.internalipaddress,
                private_port=self.internallanport,
                mapping_description='Nicotine+'
            )

        except Exception as e:
            raise RuntimeError(
                _('Failed to map the external WAN port: %(error)s') %
                {'error': str(e)}
            )

    def find_suitable_external_wan_port(self):
        """ Function to find a suitable external WAN port to map to the client.
        It will detect if a port mapping to the client already exists. """

        # Analyze ports mappings
        for m in sorted(self.existingportsmappings):

            e_port, protocol, (int_client, iport), desc, enabled, rhost, duration = m

            # A Port Mapping is already in place with the client: we will
            # rewrite it to avoid a timeout on the duration of the mapping
            if protocol == "TCP" and \
                    str(int_client) == str(self.internalipaddress) and \
                    str(iport) == str(self.internallanport):

                log.add_debug('Port Mapping already in place: %s', str(m))
                self.externalwanport = e_port
                self.foundexistingmapping = True
                break

        # If no mapping already in place we try to found a suitable external WAN port
        if not self.foundexistingmapping:

            # Find the first external WAN port > requestedwanport that's not already reserved
            tcpportsreserved = [x[0] for x in sorted(self.existingportsmappings) if x[1] == "TCP"]

            while str(self.externalwanport) in tcpportsreserved:
                if self.externalwanport + 1 <= 65535:
                    self.externalwanport += 1

                else:
                    raise AssertionError(
                        _('Failed to find a suitable external WAN port, bailing out.')
                    )

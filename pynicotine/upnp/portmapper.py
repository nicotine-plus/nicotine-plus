# COPYRIGHT (C) 2020-2021 Nicotine+ Team
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

        self.externalwanport = None
        self.internalipaddress = None
        self.internallanport = None

    def add_port_mapping(self, np):
        """
        This function supports creating a Port Mapping via the UPnP
        IGDv1 and IGDv2 protocol.

        Need a reference to the np object to extract the internal LAN
        local from the protothread socket.

        Any UPnP port mapping done with IGDv2 will expire after a
        maximum of 7 days (lease period), according to the protocol.
        We set the lease period to a shorter 24 hours, and regularly
        renew the port mapping (see pynicotine.py).
        """

        try:
            self._add_port_mapping(np)

        except Exception as error:
            from traceback import format_exc
            log.add(_('UPnP exception: %(error)s'), {'error': error})
            log.add_debug(format_exc())
            log.add(_('Failed to automate the creation of UPnP Port Mapping rule.'))
            return

        log.add_debug(
            _('Managed to map external WAN port %(externalwanport)s '
              + 'to your local host %(internalipaddress)s '
              + 'port %(internallanport)s.'),
            {
                'externalwanport': self.externalwanport,
                'internalipaddress': self.internalipaddress,
                'internallanport': self.internallanport
            }
        )

    def _add_port_mapping(self, np):
        """
        Function that actually creates the port mapping.
        If a port mapping already exists, it is updated with a lease
        period of 24 hours.
        """

        log.add_debug('Creating Port Mapping rule via UPnP...')

        # Create a UDP socket
        local_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Send a broadcast packet on a local address (doesn't need to be reachable,
        # but MacOS requires port to be non-zero)
        local_socket.connect(('10.255.255.255', 1))

        # This returns the "primary" IP on the local box, even if that IP is a NAT/private/internal IP.
        self.internalipaddress = local_socket.getsockname()[0]

        # Close the socket
        local_socket.close()

        # Find router
        router = UPnp.find_router(self.internalipaddress)

        if not router:
            raise RuntimeError('UPnP does not work on this network')

        # Store the Local LAN port
        self.internallanport = np.protothread.listen_socket.getsockname()[1]
        self.externalwanport = self.internallanport

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
                mapping_description='NicotinePlus',
                lease_duration=86400  # Expires in 24 hours
            )

        except Exception as error:
            raise RuntimeError(
                _('Failed to map the external WAN port: %(error)s') % {'error': error}) from error

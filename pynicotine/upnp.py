#!/usr/bin/env python
# -*- Mode: python -*-
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
#
from time import sleep

from logfacility import log
from utils import _

def fixportmapping(internallanport):
	try:
		import miniupnpc
	except ImportError, e:
		log.addwarning(_('Could not load miniupnpc module: %(error)s') % {'error':str(e)})
		return None
	u = miniupnpc.UPnP()
	u.discoverdelay = 200
	try:
		print "Discovering... delay=%ums" % u.discoverdelay
		ndevices = u.discover()
		print "%s device(s) detected" % ndevices
		u.selectigd()
		print "Selecting one of the IGD. Local address: %s External address: %s" % (u.lanaddr, u.externalipaddress())
		print "Misc: %s\n%s" % (u.statusinfo(), u.connectiontype())
		print "Selecting random external port..."
		eport = 15000
		r = u.getspecificportmapping(eport, 'TCP')
		print "Initial r: %s" % (str(r),)
		while r != None:
			eport = eport + 1
			if eport > 65535:
				print "Failed to find a suitable external port, bailing."
				return
			r = u.getspecificportmapping(eport, 'TCP')
			print "Conseq. r: %s" % (str(r),)
		print "trying to redirect %s port %u TCP => %s port %u TCP" % (externalipaddress, eport, u.lanaddr, internallanport)
		b = u.addportmapping(eport, 'TCP', u.lanaddr, internallanport, 'Nicotine+', '')
		if b:
			print "Success?"
			return (externalipaddress, eport)
		else:
			print "Failed?"
			return
	except Exception, e:
		print "Something went wrong: %s" % (str(e),)
		return

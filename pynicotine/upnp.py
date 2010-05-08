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
from utils import _, executeCommand

upnppossible = False
miniupnpc = None
miniupnpc_errors = []
try:
	import miniupnpc
	upnppossible = True
except ImportError, e:
	miniupnpc_errors.append(_("Failed to import miniupnpc module: %(error)s") % {'error':str(e)})
	try:
		executeCommand("upnpc", returnoutput=True)
		upnppossible = True
	except RuntimeError, e:
		miniupnpc_errors.append(_("Failed to run upnpc binary: %(error)s") % {'error':str(e)})

def fixportmapping(internallanport, externallanport = None):
	if not upnppossible:
		log.addwarning(_('Both MiniUPnPc python module and MiniUPnPc binary failed - automatic portmapping is not possible. Errors: %(errors)s') % {'error':"\n".join(miniupnpc_errors)})
		return
	if not externallanport:
		externallanport = internallanport
	if miniupnpc:
		return miniupnpcmodule(internallanport, externallanport)
	else:
		return miniupnpcbinary(internallanport, externallanport)
def miniupnpcbinary(internallanport, externallanport):
	if internallanport != externallanport:
		log.addWarning(_('UPnPc binary cannot be used since the internal port (%s) is not identical to the external port (%s)') % (internallanport, externallanport))
	command = 'upnpc -r $ tcp'
	try:
		output = executeCommand(command, replacement=str(externallanport), returnoutput=True)
	except RuntimeError, e:
		log.addwarning('Failed to use UPnPc binary: %s' % (str(e),))
		return
	for line in output.split('\n'):
		# "external %s:%s %s is redirected to internal %s:%s\n"
		if line.startswith("external ") and line.find(" is redirected to internal ") > -1:
			lst = line.split()
			external = lst[1].split(':')
			#internal = lst[7].split(':')
			try:
				return (external[0], int(external[1]))
			except (ValueError, IndexError):
				log.addwarning(_('UPnPc binary failed, could not decompose %s into IP and port.') % (external))
				return None
	log.addwarning('UPnPc binary failed, could not parse output: %s' % (output,))
	return None
def miniupnpcmodule(internallanport, externallanport):
	u = miniupnpc.UPnP()
	u.discoverdelay = 2000
	try:
		print "Discovering... delay=%ums" % u.discoverdelay
		ndevices = u.discover()
		print "%s device(s) detected" % ndevices
		u.selectigd()
		lanaddr = u.lanaddr
		externalipaddress = u.externalipaddress()
		print "Selecting one of the IGD. Local address: %s External address: %s" % (lanaddr, externalipaddress)
		print "Misc: %s\n%s" % (u.statusinfo(), u.connectiontype())
		print "Selecting random external port..."
		externallanport = 15000
		r = u.getspecificportmapping(externallanport, 'TCP')
		print "Initial r: %s" % (str(r),)
		while r != None:
			externallanport += 1
			if externallanport > 65535:
				print "Failed to find a suitable external port, bailing."
				return
			r = u.getspecificportmapping(externallanport, 'TCP')
			print "Conseq. r: %s" % (str(r),)
		print "trying to redirect %s port %u TCP => %s port %u TCP" % (externalipaddress, externallanport, lanaddr, internallanport)
		b = u.addportmapping(externallanport, 'TCP', lanaddr, internallanport, 'Nicotine+', '')
		if b:
			print "Success?"
			return (externalipaddress, externallanport)
		else:
			print "Failed?"
			return
	except Exception, e:
		print "Something went wrong: %s" % (str(e),)
		return

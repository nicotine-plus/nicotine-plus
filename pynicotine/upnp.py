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

miniupnpc = None
try:
	import miniupnpc
except ImportError, e:
	miniupnpc_error = str(e)

def fixportmapping(internallanport, externallanport = None):
	if not externallanport:
		externallanport = internallanport
	if miniupnpc:
		return miniupnpcmodule(internallanport, externallanport)
	log.addwarning(_('MiniUPnPc module was not imported: %(error)s. Trying binary...') % {'error':miniupnpc_error})
	return miniupnpcbinary(internallanport, externallanport)
def miniupnpcbinary(internallanport, externallanport):
	command = "upnpc -r %s %s" % (internallanport, externallanport)
	try:
		output = executeCommand(command, returnoutput=True)
	except RuntimeError, e:
		log.addwarning('Failed to use UPnPc binary: %s' % (str(e),))
		return
	for line in output.split('\n'):
		# "external %s:%s %s is redirected to internal %s:%s\n"
		if line.startswith("external ") and line.find(" is redirected to internal ") > -1:
			lst = line.split()
			external = lst[1].split(':')
			if len(external) == 2 and len(internal) == 2:
				return (external[0], external[1])
	log.addwarning('UPnPc output, could not parse output: %s' % (output,))
	return None

def miniupnpcmodule(internallanport, externallanport):
	try:
		import miniupnpc
	except ImportError, e:
		log.addwarning(_('Could not load miniupnpc module: %(error)s') % {'error':str(e)})
		return None
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

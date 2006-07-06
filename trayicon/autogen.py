#! /usr/bin/env python

import sys
py_ver = "%i.%i" % tuple(sys.version_info[0:2])

print "Generating Makefile for python %s" % py_ver
data = open("Makefile.in").read()
data = data.replace("@@PY_VER@@", py_ver)
data = data.replace("@@PREFIX@@", sys.prefix)
open("Makefile", "w").write(data)
print "Done.. Now run 'make install' as root"

#!/bin/bash

## Automagical deb/rpm creator for Nicotine+
## (C) Matthew Chesky 2010
## mchesky@gmail.com
## Use whatever you need however you see fit..  


##  Needs to be run as 'root'.  sudo will not work.  I may 
##  fix this in the future.
##
##  Dependencies:
## 
##  dh-make, debhelper, alien
##
##  Todo:  
##  1) Make this generate properly 'debianized' packages and
##  pass them through linitian for verification
##  2) Get rid of the annoying 'Press enter to continue' from dh_make
##  3) Add pbuilder and fakeroot support so root priviledges are not required
##
##-------------------------
##
##  Edit these as necessary

source `dirname $0`/"_library.sh"

verifyChangelog
exportSvn

depends="python (>= 2.4), python-support (>= 1.0.3), python-gtk2 (>= 2.16.0), x11-utils, menu"
recommends="python-pyvorbis, python-geoip, python-notify, xdg-utils"
suggests="python-psyco, python-gnome2, python-sexy, python-dbus, python-gst0.10"
pname="Matthew Chesky"
pemail="mchesky@gmail.com"

## Shouldn't need to edit anything past this point..  Might be worth a 
## look if there has been major changes to the source/hierarchy
##
## ------------------------


DEBIANDIR="$EXPORTDIR/debian"
PNS="$EXPORTDIR/debian/nicotine"
mkdir "$DEBIANDIR"

## debian/rules
echo "#!/usr/bin/make -f
# -*- makefile -*
export DH_VERBOSE=0
configure: configure-stamp
configure-stamp:
	dh_testdir
	touch configure-stamp
build: build-stamp
build-stamp: configure-stamp
	dh_testdir
	touch build-stamp
clean:
	dh_testdir
	dh_testroot
	rm -f build-stamp configure-stamp
	dh_clean
install: build
	dh_testdir
	dh_testroot
	dh_clean -k
	dh_installdirs

	mkdir -p \"$pns/usr/share/python-support\"
	mkdir -p \"$pns/usr/share/pyshared/pynicotine\"
	mkdir -p \"$pns/usr/share/pyshared/pynicotine/gtkgui\"
	mkdir -p \"$pns/usr/bin\"
	mkdir -p \"$pns/usr/share/man/man1\"
	mkdir -p \"$pns/usr/share/doc/nicotine\"
	mkdir -p \"$pns/usr/share/menu\"
	mkdir -p \"$pns/usr/share/pixmaps/\"
	mkdir -p \"$pns/usr/share/sounds/nicotine/default\"" >> "$DEBIANDIR/rules"


for i in "$EXPORTDIR"/*.py; do 
	echo "	cp '$EXPORTDIR/$i' '$pns/usr/bin/$i'" >> "$DEBIANDIR/rules"
done
echo "usr/bin" >> "$DEBIANDIR/dirs"

for i in "$EXPORTDIR/manpages/"*.1; do
	echo "	cp '$EXPORTDIR/$i' '$pns/usr/share/man/man1/$i'" >> "$DEBIANDIR/rules"
done
echo "usr/share/man/man1" >> "$DEBIANDIR/dirs"

for i in "$EXPORTDIR/languages/"*; do
	if [ -d "$i" ]; then
		echo "  mkdir -p '$pns/usr/share/locale/$i/LC_MESSAGES'" >> "$DEBIANDIR/rules"
		echo "usr/share/locale/$dir/LC_MESSAGES" >> "$DEBIANDIR/dirs"
		for mo in "$EXPORTDIR/languages/$i"/*.mo; do
			echo "  cp '$EXPORTDIR/$mo' '$pns/usr/share/locale/$dir/LC_MESSAGES/nicotine.mo'" >> "$DEBIANDIR/rules"
		done
	fi
done

for i in "$EXPORTDIR/doc/"* ; do
	echo "	cp '$EXPORTDIR/$i' '$pns/usr/share/doc/nicotine/$i'" >> "$DEBIANDIR/rules"
done
echo "usr/share/doc/nicotine" >> "$DEBIANDIR/dirs"

# THIS IS NOT RIGHT
# Copying our startup file as menu item? No wonder people see n+ popping around every time they use a package manager
echo "	cp nicotine.py '$pns/usr/share/menu/nicotine'" >> "$DEBIANDIR/rules"
die "*** You just corrupted this .deb ***"
echo "usr/share/menu/nicotine" >> "$DEBIANDIR/dirs"

for i in "$EXPORTDIR/files/"*.png; do
	echo "	cp '$EXPORTDIR/$i' '$pns/usr/share/pixmaps/$i'" >> "$DEBIANDIR/rules"
done
echo "usr/share/pixmaps" >> "$DEBIANDIR/dirs"

for i in "$EXPORTDIR/img/"*.png; do
	echo "	cp '$EXPORTDIR/$i' '$pns/usr/share/pixmaps/$i'" >> "$DEBIANDIR/rules"
done

for i in "$EXPORTDIR/files/"*.desktop; do
	echo "	cp '$EXPORTDIR/$i' '$pns/usr/share/$i'" >> "$DEBIANDIR/rules"
done

for i in "$EXPORTDIR/sounds/default/"*.ogg; do
	echo "	cp '$EXPORTDIR/$i '$pns/usr/share/sounds/nicotine/default/$i'" >> "$DEBIANDIR/rules"
done
echo "usr/share/sounds/nicotine/default" >> "$DEBIANDIR/dirs"

for i in "$EXPORTDIR/pynicotine/"*.py do
	echo "	cp '$EXPORTDIR/$i' '$pns/usr/share/pyshared/pynicotine/$i'" >> "$DEBIANDIR/rules"
	echo "/usr/share/pyshared/pynicotine/$i" >> "$pynicotine/nicotine.public"
done
echo "usr/share/pyshared/pynicotine" >> "$DEBIANDIR/dirs"
for i in "$EXPORTDIR/pynicotine/gtkgui/"*;  do
	echo "	cp '$EXPORTDIR/$i' '$pns/usr/share/pyshared/$i'" >> "$DEBIANDIR/rules"
	echo "/usr/share/pyshared/$i" >> "$EXPORTDIR/pynicotine/nicotine.public"
done
for i in "$EXPORTDIR/pynicotine/"*.public; do
	echo "	cp '$EXPORTDIR/$i' '$pns/usr/share/python-support/$i'" >> "$DEBIANDIR/rules"
done

echo "binary-indep: build install
binary-arch: build install
	dh_testdir
	dh_testroot
	dh_installchangelogs
	dh_installdocs
	dh_installexamples
	dh_installmenu
	dh_pycentral
	dh_pysupport
	dh_installman
	dh_link
	dh_strip
	dh_compress
	dh_fixperms
	dh_installdeb
	dh_shlibdeps
	dh_gencontrol
	dh_md5sums
	dh_builddeb
binary: binary-indep binary-arch
.PHONY: build clean binary-indep binary-arch binary install configure" >> "$DEBIANDIR/rules"

##  debian/control
echo "Source: nicotine
Section: net
Priority: extra
Maintainer: $pname <$pemail>
Build-Depends: $depends
Standards-Version: 3.7.3
Homepage: http://www.nicotine-plus.org/

Package: nicotine
Architecture: all
Depends: $depends
Recommends: $recommends
Suggests: $suggests
Description: graphical client for the SoulSeek peer-to-peer system
 Nicotine is a client for SoulSeek, a light and efficient file sharing
 system, written in Python and using the GTK2 toolkit, based on the
 PySoulSeek project.
 .
 It features uploading, downloading, searching and chatting, with
 strict bandwidth control, and tries to look like PySoulSeek.
 .
 URL: http://www.nicotine-plus.org/
" > "$DEBIANDIR/control"

## debian/compat
echo "7
" > "$DEBIANDIR/compat"

## debian/copyright
echo "Upstream Author(s):

    Daelstorm <daelstorm@gmail.com>

Copyright:

    <Copyright (C) $( date +%Y ) Daelstorm>

License:

    This package is free software; you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation; either version 2 of the License, or
    (at your option) any later version.

    This package is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this package; if not, write to the Free Software
    Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA


The Debian/RPM packaging is (C) $( date +%Y ), $pname <$pemail> and
is licensed under the GPL, see above.
" > "$DEBIANDIR/copyright"

## debian/changelog
echo "nicotine ($VERSION-1ubuntu1) intrepid; urgency=low

  * nicotine_$VERSION-1_all.deb

 -- $pname <$pemail>  $( date -R )

" > "$DEBIANDIR/changelog"

export DEBEMAIL=$pemail
export DEBFULLNAME=$pname
dh_clean
dh_make -r -s -i
dpkg-buildpackage
die "cd'ing into relative dirs isn't safe"
cd ..
alien -r *.deb

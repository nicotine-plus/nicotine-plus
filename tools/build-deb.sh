#!/bin/bash

## Automagical deb/rpm creator for Nicotine+
## (C) Matthew Chesky 2010
## mchesky@gmail.com
## Use whatever you need however you see fit..  


##  Needs to be run as 'root'.  sudo will not work.  I may 
##  fix this in the future.
##
##	Dependencies:
##	
##	dh-make, debhelper, alien
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

current="1.2.15"
depends="python (>= 2.4), python-support (>= 1.0.3), python-gtk2 (>= 2.16.0), x11-utils, menu"
recommends="python-pyvorbis, python-geoip, python-notify, xdg-utils"
suggests="python-psyco, python-gnome2, python-sexy, python-dbus, python-gst0.10"
pname="Matthew Chesky"
pemail="mchesky@gmail.com"

## Shouldn't need to edit anything past this point..  Might be worth a 
## look if there has been major changes to the source/hierarchy
##
## ------------------------


mkdir -p ~/autodeb
cd ~/autodeb
wget http://129.125.101.92/nicotine+/nicotine+-$current.tar.gz
tar zxvf *.gz
rm *.gz
cd nic*
mkdir debian
pns=$(pwd)/debian/nicotine

## debian/rules
echo "#!/usr/bin/make -f" > debian/rules
echo "# -*- makefile -*" >> debian/rules
echo "export DH_VERBOSE=0" >> debian/rules
echo "configure: configure-stamp" >> debian/rules
echo "configure-stamp:" >> debian/rules
echo "	dh_testdir" >> debian/rules
echo "	touch configure-stamp" >> debian/rules
echo "build: build-stamp" >> debian/rules
echo "build-stamp: configure-stamp" >> debian/rules
echo "	dh_testdir" >> debian/rules
echo "	touch build-stamp" >> debian/rules
echo "clean:" >> debian/rules
echo "	dh_testdir" >> debian/rules
echo "	dh_testroot" >> debian/rules
echo "	rm -f build-stamp configure-stamp" >> debian/rules
echo "	dh_clean" >> debian/rules
echo "install: build" >> debian/rules
echo "	dh_testdir" >> debian/rules
echo "	dh_testroot" >> debian/rules
echo "	dh_clean -k" >> debian/rules
echo "	dh_installdirs" >> debian/rules
echo "
" >> debian/rules
echo "	mkdir -p" $pns"/usr/share/python-support" >> debian/rules
echo "	mkdir -p" $pns"/usr/share/pyshared/pynicotine" >> debian/rules
echo "	mkdir -p" $pns"/usr/share/pyshared/pynicotine/gtkgui" >> debian/rules
echo "	mkdir -p" $pns"/usr/bin" >> debian/rules
echo "	mkdir -p" $pns"/usr/share/man/man1" >> debian/rules
echo "	mkdir -p" $pns"/usr/share/doc/nicotine" >> debian/rules
echo "	mkdir -p" $pns"/usr/share/menu" >> debian/rules
echo "	mkdir -p" $pns"/usr/share/pixmaps/" >> debian/rules
echo "	mkdir -p" $pns"/usr/share/sounds/nicotine/default" >> debian/rules
for file in $( ls *.py ); do 
	echo "	cp" $(pwd)"/"$file $pns"/usr/bin/"$( echo $file | sed 's!.*/!!' ) >> debian/rules
done
echo "usr/bin" > debian/dirs
for file in $( ls manpages/*.1 ); do
	echo "	cp" $(pwd)"/"$file $pns"/usr/share/man/man1/"$( echo $file | sed 's!.*/!!' ) >> debian/rules
done
echo "usr/share/man/man1" >> debian/dirs
rm languages/mergeall languages/msgfmtall.py languages/nicotine.pot ## Would love a less destructive solution but I'm lazy...
for dir in $( ls languages ); do
	echo "	mkdir -p" $pns"/usr/share/locale/"$dir"/LC_MESSAGES" >> debian/rules
	echo "usr/share/locale/"$dir"/LC_MESSAGES" >> debian/dirs
	for mo in $( ls languages/$dir/*.mo ); do
		echo "	cp" $(pwd)"/"$mo $pns"/usr/share/locale/"$dir"/LC_MESSAGES/nicotine.mo" >> debian/rules
	done
done
for file in $( ls doc/* ); do
	echo "	cp" $(pwd)"/"$file $pns"/usr/share/doc/nicotine/"$( echo $file | sed 's!.*/!!' ) >> debian/rules
done
echo "usr/share/doc/nicotine" >> debian/dirs
echo "	cp nicotine.py" $pns"/usr/share/menu/nicotine" >> debian/rules
echo "usr/share/menu/nicotine" >> debian/dirs
for file in $( ls files/*.png ); do
	echo "	cp" $(pwd)"/"$file $pns"/usr/share/pixmaps/"$( echo $file | sed 's!.*/!!' ) >> debian/rules
done
echo "usr/share/pixmaps" >> debian/dirs
for file in $( ls img/*.png ); do
	echo "	cp" $(pwd)"/"$file $pns"/usr/share/pixmaps/"$( echo $file | sed 's!.*/!!' ) >> debian/rules
done
for file in $( ls files/*.desktop ); do
	echo "	cp" $(pwd)"/"$file $pns"/usr/share/"$( echo $file | sed 's!.*/!!' ) >> debian/rules
done
for file in $( ls sounds/default/*.ogg ); do
	echo "	cp" $(pwd)"/"$file $pns"/usr/share/sounds/nicotine/default/"$( echo $file | sed 's!.*/!!' ) >> debian/rules
done
echo "usr/share/sounds/nicotine/default" >> debian/dirs
for file in $( ls pynicotine/*.py ); do
	echo "	cp" $(pwd)"/"$file $pns"/usr/share/pyshared/pynicotine/"$( echo $file | sed 's!.*/!!' ) >> debian/rules
	echo "/usr/share/pyshared/pynicotine/"$( echo $file | sed 's!.*/!!' ) >> pynicotine/nicotine.public
done
echo "usr/share/pyshared/pynicotine" >> debian/dirs
for file in $( ls pynicotine/gtkgui/* ); do
	echo "	cp" $(pwd)"/"$file $pns"/usr/share/pyshared/"$file >> debian/rules
	echo "/usr/share/pyshared/"$file >> pynicotine/nicotine.public
done
for file in $( ls pynicotine/*.public ); do
	echo "	cp" $(pwd)"/"$file $pns"/usr/share/python-support/"$( echo $file | sed 's!.*/!!' ) >> debian/rules
done
echo "binary-indep: build install" >> debian/rules
echo "binary-arch: build install" >> debian/rules
echo "	dh_testdir" >> debian/rules
echo "	dh_testroot" >> debian/rules
echo "	dh_installchangelogs" >> debian/rules
echo "	dh_installdocs" >> debian/rules
echo "	dh_installexamples" >> debian/rules
echo "	dh_installmenu" >> debian/rules
echo "	dh_pycentral" >> debian/rules
echo "	dh_pysupport" >> debian/rules
echo "	dh_installman" >> debian/rules
echo "	dh_link" >> debian/rules
echo "	dh_strip" >> debian/rules
echo "	dh_compress" >> debian/rules
echo "	dh_fixperms" >> debian/rules
echo "	dh_installdeb" >> debian/rules
echo "	dh_shlibdeps" >> debian/rules
echo "	dh_gencontrol" >> debian/rules
echo "	dh_md5sums" >> debian/rules
echo "	dh_builddeb" >> debian/rules
echo "binary: binary-indep binary-arch" >> debian/rules
echo ".PHONY: build clean binary-indep binary-arch binary install configure" >> debian/rules

##  debian/control
echo "Source: nicotine
Section: net
Priority: extra
Maintainer: "$pname" <"$pemail">
Build-Depends: "$depends"
Standards-Version: 3.7.3
Homepage: http://www.nicotine-plus.org/

Package: nicotine
Architecture: all
Depends: "$depends"
Recommends: "$recommends"
Suggests: "$suggests"
Description: graphical client for the SoulSeek peer-to-peer system
 Nicotine is a client for SoulSeek, a light and efficient file sharing
 system, written in Python and using the GTK2 toolkit, based on the
 PySoulSeek project.
 .
 It features uploading, downloading, searching and chatting, with
 strict bandwidth control, and tries to look like PySoulSeek.
 .
 URL: http://www.nicotine-plus.org/
" > debian/control

## debian/compat
echo "7
" > debian/compat

## debian/copyright
echo "Upstream Author(s):

    Daelstorm <daelstorm@gmail.com>

Copyright:

    <Copyright (C) "$( date +%Y )" Daelstorm>

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


The Debian/RPM packaging is (C) "$( date +%Y )", "$pname" <"$pemail"> and
is licensed under the GPL, see above.
" > debian/copyright

## debian/changelog
echo "nicotine ("$current"-1ubuntu1) intrepid; urgency=low

  * nicotine_"$current"-1_all.deb

 -- "$pname" <"$pemail">  "$( date -R )"

" > debian/changelog
export DEBEMAIL=$pemail
export DEBFULLNAME=$pname
dh_clean
dh_make -r -s -i
dpkg-buildpackage
cd ..
alien -r *.deb
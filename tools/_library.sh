#!/bin/bash

# Source this file to load a bunch of functions useful for generating files
# from the Nicotine+ folder such as .tar.gz, .deb and .exe

# In your own script you can use the following variables:
#
# SVNROOT
#   Absolute path to the SVN folder
#   Example: /home/quinox/nicotine_svn
# TOOLSDIR
#   Absolute path to the tools folder inside the SVN
#   Example: /home/quinox/nicotine_svn/tools
# VERSION
#   The version number of Nicotine+
#   Example: 1.2.13
# EXPORTDIR
#   Where you can find the exported SVN (only available after calling exportSvn)

# In your own script you can use the following functions:
# die
#   aborts the script with the given arguments as failure message
#   Example: die "You forgot to push the button"
# progress
# progress1
# progress2
# exportSvn
#   Exports the SVN folder to a temp. directory.
# verifyChangelog
#



# Only called from within this script
setEnvironment() {
	TOOLSDIR=$(dirname $(readlink -f $0))
	SVNROOT=${TOOLSDIR%%/tools}
	progress "SVN Root: $SVNROOT"
}
setVersion() {
	progress1 "Determining Nicotine+ version..."
	VERSION=$(sed -n "/^version \?=/{s/.* //;s/^['\"]//;s/['\"]$//;p}" "$SVNROOT/pynicotine/utils.py")
	[ -z "$VERSION" ] && die "Could not retrieve version number"
	[ "$VERSION" != "${VERSION/svn/}" ] && die "SVN is part of the version string."
	progress2 "$VERSION"
}
setTempdir() {
	if [ -z "$TMPDIR" ]; then
		progress1 "Creating temporary directory..."
		TMPDIR="/tmp/nicotine_$RANDOM"
		mkdir "$TMPDIR" || die "Failed to create temp dir $TMPDIR"
		progress2 "$TMPDIR"
	fi
}

# Use these in your own scripts
die() {
	echo "Failure: $1" >&2
	exit 1
}
progress() {
	progress1 $*
	progress2
}
progress1() {
	echo -en "\r[status] $* "
}
progress2() {
	echo "$*"
}
verifyChangelog() {
	progress1 "Verifying changelog..."
	grep --fixed-strings "$VERSION" "$SVNROOT/doc/CHANGELOG" >/dev/null || die "It seems doc/CHANGELOG does not mention version $VERSION"
	progress2 "OK."
}
exportSvn() {
	setTempdir
	progress1 "Exporting SVN..."
	EXPORTFOLDER="nicotine+-$VERSION"
	EXPORTDIR="$TMPDIR/$EXPORTFOLDER"
	svn export "$SVNROOT" "$EXPORTDIR" || die "Failed to export SVN to $EXPORTDIR"
	progress "SVN Exported to $EXPORTDIR"
}

setEnvironment
setVersion

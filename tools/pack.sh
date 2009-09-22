#!/bin/bash

die() {
	echo "Failure: $1"
	exit 1
}

cd "${PWD%%/tools}" # if we're in /tools we go 1 up, otherwise we stay were we are

VERSION=`sed -n "/^version \?=/{s/.* //;s/^['\"]//;s/['\"]$//;p}" pynicotine/utils.py`
[ -z "$VERSION" ] && die "Could not retrieve version number"
[ "$VERSION" != "${VERSION/svn/}" ] && die "It seems your repository still carries the SVN tag in the version: $VERSION"

TMPDIR="/tmp/nic_$RANDOM"
mkdir "$TMPDIR" || die "Failed to create temp dir $TMPDIR"

NICDIR="nicotine+-$VERSION"
SRCDIR="$TMPDIR/$NICDIR"

echo "Exporting SVN..."
svn export . "$SRCDIR" || die "Failed to export SVN to $SRCDIR"

cd "$TMPDIR"

echo "Tarring (BZip2)..."
tar -cjf "nicotine+-$VERSION.tar.bz2" "$NICDIR" || die "Failed to create BZip2"
echo "Tarring (GZip)..."
tar -czf "nicotine+-$VERSION.tar.gz" "$NICDIR" || die "Failed to create GZip"

echo "Nicotine+ $VERSION packed in $TMPDIR"

echo "Don't forget to tag the SVN repository:"
echo "  svn copy http://nicotine-plus.org/svn/trunk/nicotine+ http://nicotine-plus.org/svn/tags/$VERSION/"

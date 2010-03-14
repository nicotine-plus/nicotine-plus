#!/bin/bash
source `dirname $0`/"_library.sh"

verifyChangelog
exportSvn


BZ2="$TMPDIR/nicotine+-$VERSION.tar.bz2"
progress1 "Tarring (BZip2)..."
tar --create --bzip2 --directory="$TMPDIR" --file "$BZ2" "$EXPORTFOLDER" || die "Failed to create BZip2"
progress2 "Done: $BZ2"

GZ="$TMPDIR/nicotine+-$VERSION.tar.gz"
progress1 "Tarring (GZip)..."
tar --create --gzip --directory="$TMPDIR" --file "$GZ" "$EXPORTFOLDER" || die "Failed to create GZip"
progress2 "Done: $GZ"

echo ""
echo "Nicotine+ $VERSION packed in $TMPDIR"

echo "Don't forget to tag the SVN repository:"
echo "  svn copy http://nicotine-plus.org/svn/trunk/nicotine+ http://nicotine-plus.org/svn/tags/$VERSION/"

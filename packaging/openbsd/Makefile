# $OpenBSD$
COMMENT =		graphical client for the SoulSeek peer-to-peer system
CATEGORIES =		net
HOMEPAGE =		https://nicotine-plus.github.io/nicotine-plus/
MAINTAINER =		Han Boetes <han@boetes.org>

GH_ACCOUNT =		Nicotine-Plus
GH_PROJECT =		nicotine-plus
GH_TAGNAME =		3.0.0

# GPLv3
PERMIT_PACKAGE =	Yes

MODULES =		lang/python
MODPY_VERSION =		${MODPY_DEFAULT_VERSION_3}
BUILD_DEPENDS =		devel/gettext,-tools
RUN_DEPENDS =		devel/desktop-file-utils \
			devel/py-gobject3${MODPY_FLAVOR} \
			lang/python/${MODPY_VERSION},-gdbm \
			x11/gtk+3,-guic

pre-configure:
	sed -i 's|share/man|man|' ${WRKSRC}/setup.py


.include <bsd.port.mk>

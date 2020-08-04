#!/bin/sh

brew install \
  create-dmg \
  gdk-pixbuf \
  gobject-introspection \
  gspell \
  gtk+3 \
  libnotify \
  miniupnpc \
  pygobject3 \
  upx

# pip should not pick up our setup.cfg
cd pynicotine
pip3 install flake8 pyinstaller pytaglib pytest
cd ..

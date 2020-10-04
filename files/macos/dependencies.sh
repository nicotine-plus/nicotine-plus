#!/bin/sh

brew install \
  create-dmg \
  flake8 \
  gdk-pixbuf \
  gobject-introspection \
  gspell \
  gtk+3 \
  libnotify \
  miniupnpc \
  pygobject3 \
  taglib \
  upx

# pip should not pick up our setup.cfg
cd pynicotine
pip3 install pep8-naming pyinstaller==3.6 pytaglib pytest
cd ..

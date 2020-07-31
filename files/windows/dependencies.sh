#!/bin/sh

pacman --noconfirm -S --needed \
  git \
  upx \
  mingw-w64-$ARCH-gspell \
  mingw-w64-$ARCH-gtk3 \
  mingw-w64-$ARCH-miniupnpc \
  mingw-w64-$ARCH-nsis \
  mingw-w64-$ARCH-python3 \
  mingw-w64-$ARCH-python3-gobject \
  mingw-w64-$ARCH-python3-pip \
  mingw-w64-$ARCH-python3-pytest \
  mingw-w64-$ARCH-python3-flake8

# pip should not pick up our setup.cfg
cd pynicotine
pip install mutagen plyer PyInstaller
cd ..

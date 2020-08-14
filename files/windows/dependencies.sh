#!/bin/sh

pacman --noconfirm -S --needed \
  git \
  upx \
  mingw-w64-$ARCH-cython \
  mingw-w64-$ARCH-gcc \
  mingw-w64-$ARCH-gspell \
  mingw-w64-$ARCH-gtk3 \
  mingw-w64-$ARCH-miniupnpc \
  mingw-w64-$ARCH-nsis \
  mingw-w64-$ARCH-python3 \
  mingw-w64-$ARCH-python3-gobject \
  mingw-w64-$ARCH-python3-pip \
  mingw-w64-$ARCH-python3-pytest \
  mingw-w64-$ARCH-python3-flake8 \
  mingw-w64-$ARCH-taglib

# pip should not pick up our setup.cfg
cd ..
pip install plyer pyinstaller==3.6 semidbm

# pytaglib
wget https://github.com/supermihi/pytaglib/archive/v1.4.6.tar.gz
tar -zxvf v1.4.6.tar.gz
cd pytaglib-1.4.6/
sed -i "/is_windows = / s/sys.platform.startswith('win')/False/" setup.py
PYTAGLIB_CYTHONIZE=1 python setup.py install

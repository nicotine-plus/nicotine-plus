#!/bin/sh

brew install \
  miniupnpc \
  pygobject3

# pip should not pick up our setup.cfg
cd pynicotine
pip3 install flake8 mutagen pytest
cd ..

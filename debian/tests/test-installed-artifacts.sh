#!/bin/sh

# Bail on any errors...
set -e

# Enter folder with integration tests...
cd test/integration

# Install Robot Framework. This installs outside of system package manager's
#  control of the FHS...
echo "*** Installing test harness..."
pip3 --disable-pip-version-check install robotframework

# Run the GUI inside of a dummy frame buffer...
echo "*** Launching Nicotine+ inside of dummy frame buffer..."
xvfb-run robot nicotine.robot

# Done...
echo "*** OK!"


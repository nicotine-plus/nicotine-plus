#!/bin/bash

# Bail on any errors...
set -e

# Python's goofy ad hoc package manager installs outside of the safety of the
#  system's native package manager and the security it provides over the FHS.
#  We need to manually add the binaries it will install to the search path...
mkdir -p $HOME/.local/bin
PATH="$HOME/.local/bin:$PATH"

# Install Robot Framework. This installs outside of system package manager's
#  control of the FHS...
echo "*** Installing test harness..."
pip3 install robotframework

# Run the GUI inside of a dummy frame buffer...
echo "*** Launching Nicotine+ inside of dummy frame buffer..."
xvfb-run robot test/integration/nicotine.robot

# Done...
echo "*** OK!"


import os
import signal
import sys

from dogtail.config import config
config.logDebugToFile = False
from dogtail.procedural import *
from dogtail.tc import TCNode, TCBool
tcn = TCNode()

def appStartup(binary, roleName = "menu item"):
    """Launches the given binary, then checks to see that the application
    started correctly by looking for a Node with the given roleName."""

    pid = run(binary)
    tcn.compare("app exists", None, focus.application.node)
    focus.widget.node = focus.app.node.child(roleName=roleName)
    tcn.compare("app has a %s" % roleName, None, focus.widget.node)
    os.kill(pid, signal.SIGTERM)

if __name__ == "__main__":
    binary = sys.argv[1]
    appStartup(binary)

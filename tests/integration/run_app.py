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
    try:
        tcn.compare("app exists", None, focus.application.node)
        print("focus", focus)
        print("desktop", focus.desktop)
        print("app", focus.app)
        print("app.node", focus.app.node)
        print("dialog", focus.dialog)
        print("window", focus.window)
        print("widget", focus.widget)
        focus.widget.node = focus.app.node.child(roleName=roleName)
        tcn.compare("app has a %s" % roleName, None, focus.widget.node)
    finally:
        print('Killing PID', pid)
        os.kill(pid, signal.SIGTERM)


if __name__ == "__main__":
    binary = sys.argv[1]
    appStartup(binary)

import signal
import sys

from dogtail.procedural import *
from dogtail.tc import TCNode, TCBool

tcn = TCNode()


def app_startup(executable, role_name="menu item"):
    """
    Launches the given executable, then checks to see that the application
    started correctly by looking for a Node with the given roleName.
    """

    pid = run(executable)
    try:
        tcn.compare("app exists", None, focus.application.node)
        print("focus", focus)
        print("desktop", focus.desktop)
        print("app", focus.app)
        print("app.node", focus.app.node)
        print("dialog", focus.dialog)
        print("window", focus.window)
        print("widget", focus.widget)
        focus.widget.node = focus.app.node.child(roleName=role_name)
        tcn.compare("app has a %s" % role_name, None, focus.widget.node)
    finally:
        print('Killing PID', pid)
        os.kill(pid, signal.SIGTERM)


if __name__ == "__main__":
    binary = sys.argv[1]
    app_startup(binary)

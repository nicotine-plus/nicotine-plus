import signal
import sys
from time import sleep

from dogtail.procedural import *
from dogtail.tc import TCNode, TCBool

tcn = TCNode()


def app_startup(executable="nicotine", role_name="menu item"):
    """
    Launches the given executable, then checks to see that the application
    started correctly by looking for a Node with the given roleName.
    """

    pid = run(executable)
    try:
        tcn.compare("app exists", None, focus.application.node)
        focus.widget.node = focus.app.node.child(roleName=role_name)
        tcn.compare("app has a %s" % role_name, None, focus.widget.node)
    finally:
        sleep(5)
        print('Killing PID', pid)
        os.kill(pid, signal.SIGTERM)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        app_startup(sys.argv[1])
    else:
        app_startup()

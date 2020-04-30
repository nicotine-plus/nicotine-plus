import signal

from dogtail.procedural import *
from dogtail.tc import TCNode

tcn = TCNode()
TAB_TITLES = (
    "Buddy List", "User browse", "User info", "Search files",
    "Uploads", "Downloads", "Private chat", "Chat rooms"
)


def app_startup(executable):
    """
    Launches the given executable, then tries finding a few UI elements
    """

    pid = run(executable)
    try:
        tcn.compare("app exists", None, focus.application.node)
        click_tabs(TAB_TITLES)
        find_ui_element(focus.app.node, roleName="menu item")
    finally:
        print('Killing PID', pid)
        os.kill(pid, signal.SIGTERM)


def click_tabs(tab_titles):
    tab_bar = find_ui_element(focus.app.node, roleName="page tab list")
    for tab in tab_titles:
        find_ui_element(tab_bar, roleName="page tab", name=tab).click()


def find_ui_element(parent_node, **kwargs):
    ui_element_node = parent_node.child(**kwargs)
    focus.widget.node = ui_element_node
    tcn.compare(
        f"app has a {kwargs.get('roleName', '')}: {kwargs.get('name', '')}",
        None, focus.widget.node
    )
    return ui_element_node


if __name__ == "__main__":
    app_startup("nicotine")

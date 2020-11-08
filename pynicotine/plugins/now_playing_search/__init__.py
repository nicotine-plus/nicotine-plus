from pynicotine.pluginsystem import BasePlugin


def enable(plugins):
    global PLUGIN
    PLUGIN = Plugin(plugins)


def disable(plugins):
    global PLUGIN
    PLUGIN = None


class Plugin(BasePlugin):
    __name__ = "Now Playing Search"

    def OutgoingGlobalSearchEvent(self, text):  # noqa
        return (self.get_np(text),)

    def OutgoingRoomSearchEvent(self, rooms, text):  # noqa
        return (rooms, self.get_np(text))

    def OutgoingBuddySearchEvent(self, text):  # noqa
        return (self.get_np(text),)

    def OutgoingUserSearchEvent(self, users, text):  # noqa
        return (users, self.get_np(text))

    def get_np(self, text):
        self.np_format = text
        return self.frame.now_playing.get_np(get_format=self.get_format)

    def get_format(self):
        return self.np_format

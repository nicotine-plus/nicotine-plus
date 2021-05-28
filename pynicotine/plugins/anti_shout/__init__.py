from pynicotine.pluginsystem import BasePlugin


def enable(plugins):
    global PLUGIN
    PLUGIN = Plugin(plugins)


def disable(plugins):
    global PLUGIN
    PLUGIN = None


class Plugin(BasePlugin):
    __name__ = "Anti SHOUT"
    settings = {
        'player_radio': 2,                # id, starts from 0
        'player_dropdown': 'Clementine',  # can be either string or id starting from 0
    }
    metasettings = {
        'player_radio': {
            'description': 'Choose an audio player',
            'type': 'radio',
            'options': (
                'Exaile',
                'Audacious',
                'Clementine'
            )},
        'player_dropdown': {
            'description': 'Choose an audio player',
            'type': 'dropdown',
            'options': (
                'Exaile',
                'Audacious',
                'Clementine'
            )}
    }

    def capitalize(self, text):
        # Dont alter words that look like protocol links (fe http://, ftp://)
        if text.find('://') > -1:
            return text
        return text.capitalize()

    def IncomingPrivateChatEvent(self, nick, line):  # noqa
        return (nick, self.antishout(line))

    def IncomingPublicChatEvent(self, room, nick, line):  # noqa
        return (room, nick, self.antishout(line))

    def antishout(self, line):
        lowers = len([x for x in line if x.islower()])
        uppers = len([x for x in line if x.isupper()])
        score = -2  # unknown state (could be: no letters at all)
        if uppers > 0:
            score = -1  # We have at least some upper letters
        if lowers > 0:
            score = uppers / float(lowers)
        newline = line
        if len(line) > self.settings['minlength'] and (score == -1 or score > self.settings['maxscore']):
            newline = '. '.join([self.capitalize(x) for x in line.split('. ')])
        if newline == line:
            return newline
        else:
            return newline + " [as]"

# For debugging
NPLUS = True


class FakePlugin(object):
    def log(self, text):
        print(text)


from urllib.request import urlopen

try:
    from pynicotine.pluginsystem import BasePlugin
except ImportError:
    NPLUS = False
    print("It seems this plugin is not loaded from within n+. Faking events...")
    BasePlugin = FakePlugin


def enable(frame):
    global PLUGIN
    PLUGIN = Plugin(frame)


def disable(frame):
    global PLUGIN
    PLUGIN = None


# The real plugin
def deltags(string):
    open = 0
    while open > -1:
        open = string.find('<', open)
        close = string.find('>', open)
        if open > -1 and close > -1:
            string = string[:open] + ' ' + string[close + 1:]
    return string.strip()


class Plugin(BasePlugin):
    __name__ = "MusicBrainz url2search"

    def OutgoingGlobalSearchEvent(self, search):
        terms = search.split()
        for i in range(0, len(terms)):
            lowerterm = terms[i].lower()
            if lowerterm[:23] == "http://musicbrainz.org/" or lowerterm[:27] == "http://www.musicbrainz.org/":
                self.log("Fetching " + terms[i])
                terms[i] = self.mb2search(terms[i])
        return ' '.join(terms),

    def mb2search(self, url):
        print("Opening url " + url)
        f = urlopen(url)
        html = f.read()
        information = []
        start = html.find('<td class="title">')
        if start > -1:
            end = html.find('</td>', start)
            if end > -1:
                information.append(deltags(html[start:end]))
        start = html.find('<span class="linkrelease-icon">')
        if start > -1:
            end = html.find('</span>', start)
            if end > -1:
                information.append(deltags(html[start:end]))
        print("Info: " + repr(information))
        return ' '.join(information)


# Debugging again
if not NPLUS:
    print("Faking search events")
    instance = Plugin()
    urls = ['http://musicbrainz.org/artist/6af1a69f-0bd9-4b2b-8a53-94f6786443ac.html',
            'http://musicbrainz.org/release/fafde3cb-ed09-4212-9ffd-b05323152801.html',
            'http://www.musicbrainz.org/release/2971a9f7-6c30-408b-93a3-87e4d07988ea.html']
    for url in urls:
        print("Searching for '" + url + "'...")
        print("... " + repr(instance.OutgoingGlobalSearchEvent(url)))
    print("End fake")

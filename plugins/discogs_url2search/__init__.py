from urllib.request import urlopen

# For debugging
NPLUS = True


class FakePlugin(object):
    def log(self, text):
        print(text)


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
    __name__ = "Discogs url2search"
    __version__ = "2008-07-06r00"
    __author__ = "quinox"
    __desc__ = """Enables you to enter Discogs URLs in the search window which will be converted to albums, artists of both."""

    def OutgoingGlobalSearchEvent(self, search):
        terms = search.split()
        for i in range(0, len(terms)):
            lowerterm = terms[i].lower()
            if lowerterm[:30] == "http://www.discogs.com/artist/" or lowerterm[:31] == "http://www.discogs.com/release/":
                self.log("Fetching " + terms[i])
                terms[i] = self.discogs2search(terms[i])
        return ' '.join(terms),

    def discogs2search(self, url):
        print("Opening url " + url)
        f = urlopen(url)
        html = f.read()
        information = []
        start = html.find('<title>')
        if start > -1:
            end = html.find('</title>')
            if end > -1:
                clean = deltags(html[start:end])
                information.append(clean.replace(' - ', ' '))
        return ' '.join(information)


# Debugging again
if not NPLUS:
    print("Faking search events")
    instance = Plugin()
    urls = ['http://www.discogs.com/artist/Dulce+Liquido',
            'http://www.discogs.com/release/174106',
            'http://www.discogs.com/release/1225584']
    for url in urls:
        print("Searching for '" + url + "'...")
        print("... " + repr(instance.OutgoingGlobalSearchEvent(url)))
    print("End fake")

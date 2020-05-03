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
    __name__ = "AllMusic url2search"

    def OutgoingGlobalSearchEvent(self, search):
        terms = search.split()
        for i in range(0, len(terms)):
            lowerterm = terms[i].lower()
            if lowerterm[:23] == "http://allmusic.com/cg/" or lowerterm[:27] == "http://www.allmusic.com/cg/":
                self.log("Fetching " + terms[i])
                terms[i] = self.allmusic2search(terms[i])
        return ' '.join(terms),

    def allmusic2search(self, url):
        print("Opening url " + url)
        f = urlopen(url)
        html = f.read()
        information = []
        start = html.find('<TITLE>')
        if start > -1:
            end = html.find('</TITLE>')
            if end > -1:
                title = deltags(html[start:end])
                print("Title is now", title)
                if title[:9] == "allmusic ":
                    title = title[9:]
                print("Title is now", title)
                title = title.replace('(', ' ').replace(')', ' ')
                title = ' '.join([x.strip() for x in title.split(' ') if x.split()])
                print("Title is now", title)
                parts = title.split(' > ', 1)
                information.append(parts[0])
        return ' '.join(information)


# Debugging again
if not NPLUS:
    print("Faking search events")
    instance = Plugin()
    urls = ['http://www.allmusic.com/cg/amg.dll?p=amg&sql=10:gifwxqwhldhe',
            'http://allmusic.com/cg/amg.dll?p=amg&sql=10:kjfwxzljldte~T2',
            'http://allmusic.com/cg/amg.dll?p=amg&sql=11:dxfrxql5ldae']
    for url in urls:
        print("Searching for '" + url + "'...")
        print("... " + repr(instance.OutgoingGlobalSearchEvent(url)))
    print("End fake")

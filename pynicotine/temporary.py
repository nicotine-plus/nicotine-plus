# -*- coding: utf-8 -*-
from utils import strace

class HybridListDictionaryMonstrosity(object):
    """A hybrid mix between a list and a dictionary.
    
    Should be used temporarily while rewriting code. It can be used to refactor
    code to replace lists with dictionaries.  Note that this is only a partial
    class, you have overwrite __getkey__ to get a complete working class.
    
    This class will show a perfect implementation of a list, for all those list
    features that are used by Nicotine+. It will only partly implement
    dictionary-type behaviour, but those will behave precisely like regular
    dictionaries (except for the part that slices and integer cannot be used as
    keys, since that would conflict with the requirement that it behaves
    identical to lists for lists functions).
    """

    def __init__(self, *args, **kwargs):
        self._dict = dict()
        self._list = list()
        pass
    def __getkey__(self, obj):
        raise NotImplementedError("You need to implement me!")

    def append(self, obj):
        """List func."""
        key = self.__getkey__(obj)
        try:
            self._dict[key]
            #print("WARNING: Key %s is already present. I've added it, but you need to fix the calling code." % repr(key))
        except KeyError:
            pass
        self._dict[key] = obj
        self._list.append(obj)
    def index(self, obj):
        """List func."""
        return self._list.index(obj)
    def remove(self, obj):
        """List func."""
        self._list.remove(obj)
        key = self.__getkey__(obj)
        try:
            del self._dict[key]
        except KeyError:
            #print("WARNING: Cannot remove %s from dictionary, at one point it was present multiple times in the list" % repr(key))
            pass
    def __iter__(self):
        """List func.
        
        Normally this also works on dictionaries, but we can't do both at the same time without magic."""
        return self._list.__iter__()
    def keys(self):
        """Dict func."""
        return self._dict.keys()
    def __getitem__(self, index_or_key):
        """Dict/list func."""
        if isinstance(index_or_key, int):
            index = index_or_key
            return self._list.__getitem__(index)
        elif isinstance(index_or_key, slice):
            index = index_or_key
            return self._list.__getitem__(index)
        else:
            key = index_or_key
            return self._dict.__getitem__(key)
    def __setitem__(self, index_or_key, obj):
        """Dictlist func."""
        if isinstance(index_or_key, int):
            index = index_or_key
            key = self.__getkey__(self._list[index])
            self._list[index] = obj
            self._dict[key] = obj
        else:
            key = index_or_key
            try:
                self._dict[key]
                #print("WARNING: Key %s is already present. Not adding it to the list." % repr(key))
            except KeyError:
                self._list.append(obj)
            self._dict.__setitem__(key, obj)
    def __delitem__(self, key):
        """Dict func."""
        obj = self._dict[key]
        self._dict.__delitem__(key)
        self._list.remove(obj)
    def __iadd__(self, objects):
        """List func."""
        for obj in objects:
            self.append(obj)
        return self
    def __add__(self, obj):
        return self._list+obj._list
    def __len__(self):
        """List/dict func."""
        return self._list.__len__()
    def len(self):
        """Dict func."""
        return len(self._dict)
    def iteritems(self):
        """Dict func."""
        return self._dict.iteritems()

class HybridListDictionaryTransferMonstrosity(HybridListDictionaryMonstrosity):
    def __getkey__(self, obj):
        return (obj.user, obj.filename) # We use the virtual path since the real path could be shared under multiple virtual paths


class ReqidManager(dict):
    def __getitem__(self, key):
        obj = super(ReqidManager, self).__getitem__(key)
        try:
            if key != obj.req:
                print("ReqidManager: Transfer %s lost its ID!" % obj)
                print("%s (key) != %s (answer.req)" % (key, obj.req))
                raise KeyError
            return obj
        except Exception, e:
            print("ReqidManager exception in __getkey__: %s" % e)
            raise
    def __setitem__(self, key, obj):
        try:
            super(ReqidManager, self).__getitem__(key)
            print("WARNING: You are reusing reqid %s, but IDs are supposed to be unique!" % key)
        except KeyError:
            pass
        super(ReqidManager, self).__setitem__(key, obj)
    def add(self, obj):
        self.__setitem__(obj.req, obj)
    
class HybridListDictionaryTupleMonstrosity(HybridListDictionaryMonstrosity):
    def __getkey__(self, obj):
        return obj[0]
    
def test():
    print("=== Interacting with lists ===")
    #
    # First, verify the monstrosity works just like a regular list - or at
    # least close enough to be used in transfers.py, anyway
    # 
    normal = []
    monster = HybridListDictionaryTupleMonstrosity()
    tuples = [('duck', 'sauce'), ('bee', 'gees'), ('cat', 'power')]
    for t in tuples:
        normal.append(t)
        monster.append(t)
    indices = [('bee', 'gees')]
    for i in indices:
        normal.remove(i)
        monster.remove(i)
    tuples = [('wolf', 'parade')]
    for t in tuples:
        normal  += t
        monster += t
    tuples = [(('duck', 'sauce'), ('lion', 'fever'))]
    for (fromtuple, totuple) in tuples:
        normal[normal.index(fromtuple)] = totuple
        monster[monster.index(fromtuple)] = totuple

    print("=== Verifying correctness with lists ===")
    for i, obj in enumerate(normal):
        print("normal  %3s: %25s | monster:      %25s. Matches: %s" % (i, obj, monster[i], obj == monster[i]))
    for i, obj in enumerate(monster):
        print("monster %3s: %25s | normal:       %25s. Matches: %s" % (i, obj, normal[i],  obj == normal[i]))
    print("last normal: %25s | last monster: %25s. Matches: %s" % (normal[-1], monster[-1], normal[-1] == monster[-1]))
    print("len normal:  %25s | len monster:  %25s. Matches: %s" % (len(normal), len(monster), len(normal) == len(monster)))
    print("normal+normal equals monster+monster. Matches: %s" % ((normal+normal) == (monster+monster)))
    tuples = [('duck', 'sauce'), ('bee', 'gees')]
    for t in tuples:
        normal_answer = (t in normal)
        monster_answer = (t in monster)
        print("%20s in normal:  %5s | in monster: %27s. Matches: %s" % (t, normal_answer, monster_answer, normal_answer == monster_answer))
    print("[:] of normal:  %s" % repr(normal[slice(0, -1, 1)]))
    print("[:] of monster: %s" % repr(monster[slice(0, -1, 1)]))
    exit(3)

    print('\n')
    print("=== Interacting with dicts ===")
    #
    # Not let's see if we can use it as a dictionary too!
    #
    normal = {}
    monster = HybridListDictionaryTupleMonstrosity()
    tuples = [('duck', 'sauce'), ('bee', 'gees'), ('cat', 'power')]
    for (key, value) in tuples:
        normal[key] = value
        monster[key] = value
    indices = ['bee']
    for i in indices:
        del normal[i]
        del monster[i]
    for i in indices:
        try:
            del normal[i]
        except KeyError:
            print("Failed to delete key %s from normal, KeyError" % repr(i))
        try:
            del monster[i]
        except KeyError:
            print("Failed to delete key %s from monster, KeyError" % repr(i))
    tuples = [('wolf', 'parade'), ('cat', 'power')]
    for (key, value) in tuples:
       normal[key] = value
       monster[key] = value

    # Note that we can't use len() since that one is being used by the list-part of the monstrosity.
    print("=== Verifying correctness with dicts ===")
    for (key, value) in normal.iteritems():
        print("normal key  %9s -> %13s | monster: %30s. Matches: %s" % (key, value, monster[key], value == monster[key]))
    for (key, value) in monster.iteritems():
        print("monster key %9s -> %13s | normal:  %30s. Matches: %s" % (key, value, monster[key], value == monster[key]))

    print("normal keys: %25s | monster keys: %25s. Matches: %s" % (repr(normal.keys()), repr(monster.keys()), (normal.keys() == monster.keys())))
    print("length normal: %23s | length monster: %23s. Matches: %s" % (len(normal), monster.len(), (len(normal) == monster.len())))

    # Lists as dictionaries and dictionaries as lists!
    print('\n')
    print("=== And now for the fun part... ===")
    print("Adding stuff via list+dictionary...")
    monster = HybridListDictionaryTupleMonstrosity()
    monster.append(('bee', 'gees'))
    monster['duck'] = ('duck', 'sauce')
    print("   (As dictionary: %90s)" % dict(monster))
    print("   (As list:       %90s)" % list(monster))
    print("Removing stuff via list+dictionary...")
    monster.remove(('duck', 'sauce'))
    del monster['bee']
    print("   (As dictionary: %90s)" % dict(monster))
    print("   (As list:       %90s)" % list(monster))
    print("Creating inconsistencies...")
    monster.append(('duck', 'sauce'))
    monster['duck'] = ('duck', 'sauce')
    monster.append(('duck', 'sauce'))
    print("   (As dictionary: %90s)" % dict(monster))
    print("   (As list:       %90s)" % list(monster))
    print("Removing via dictionary...")
    del monster['duck']
    print("   (As dictionary: %90s)" % dict(monster))
    print("   (As list:       %90s)" % list(monster))
    print("Removing via dictionary..."),
    try:
        del monster['duck']
    except KeyError:
        print("Failed to remove!")
    print("   (As dictionary: %90s)" % dict(monster))
    print("   (As list:       %90s)" % list(monster))
    print("Removing via list...")
    monster.remove(('duck', 'sauce'))
    print("   (As dictionary: %90s)" % dict(monster))
    print("   (As list:       %90s)" % list(monster))
    print("\n...Thank you and good night.")
    import sys
    sys.exit(0)
    # You don't need to subclass it, you can do this as well:
    print("Oh, you're still here. Should I amuse you some more?")
    print("Creating partial class...")
    monster = HybridListDictionaryMonstrosity()
    def mykeyfunc(obj):
        return obj[0][::-1].upper()
    print("Adding __getkey__ method...")
    monster.__getkey__ = mykeyfunc
    print("Interacting with the monster...")
    monster.append(('bee', 'gees'))
    monster.append(('duck', 'sauce'))
    print("   (As dictionary: %90s)" % dict(monster))
    print("   (As list:       %90s)" % list(monster))
    
if __name__ == "__main__":
    test()

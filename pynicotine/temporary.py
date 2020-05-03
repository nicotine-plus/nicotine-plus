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
            # print("WARNING: Key %s is already present. I've added it, but you need to fix the calling code." % repr(key))
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
            # print("WARNING: Cannot remove %s from dictionary, at one point it was present multiple times in the list" % repr(key))
            pass

    def __iter__(self):
        """List func.

        Normally this also works on dictionaries, but we can't do both at the same time without magic."""
        return self._list.__iter__()

    def keys(self):
        """Dict func."""
        return list(self._dict.keys())

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
                # print("WARNING: Key %s is already present. Not adding it to the list." % repr(key))
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
        return self._list + obj._list

    def __len__(self):
        """List/dict func."""
        return self._list.__len__()

    def len(self):
        """Dict func."""
        return len(self._dict)

    def iteritems(self):
        """Dict func."""
        return iter(self._dict.items())


class HybridListDictionaryTransferMonstrosity(HybridListDictionaryMonstrosity):
    def __getkey__(self, obj):
        return (obj.user, obj.filename)  # We use the virtual path since the real path could be shared under multiple virtual paths


class HybridListDictionaryTupleMonstrosity(HybridListDictionaryMonstrosity):
    def __getkey__(self, obj):
        return obj[0]

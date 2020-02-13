__author__ = 'Lene Preuss <lene.preuss@gmail.com>'

"""Debugging messages to help during development"""


def debug(*args):
    """
    Prints debugging info.
    TODO: add CLI switch --debug for en-/disabling.
    """
    print('*'*8, *args)

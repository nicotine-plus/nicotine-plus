#!/usr/bin/env python

import sys
from os import listdir
from os.path import isdir, join
import mp3 as mp3original
import mp3_mutagen as mp3mutagen

TOLERANCE = 10

def formatDic(dic):
    if not dic:
        return "<no information found>"
    keys = dic.keys()
    keys.sort()
    elements = []
    for key in keys:
        elements.append("%s=%4s" % (key, dic[key]))
    return ", ".join(elements)

if __name__ == '__main__':
    import sys
    if len(sys.argv) == 1:
        print "Please provide a file or a directory."
        sys.exit(1)
    if isdir(sys.argv[1]):
        lst = [join(sys.argv[1], x) for x in listdir(sys.argv[1])]
        lst.sort()
    else:
        lst = [sys.argv[1]]
    for i in lst:
        ori = mp3original.detect_mp3(i)
        mut = mp3mutagen.detect_mp3(i)
        if str(ori) == str(mut):
            print "  " + i
        else:
            if ((ori == None or mut == None) or 
                (abs(ori['bitrate'] - mut['bitrate']) > TOLERANCE or
                abs(ori['time'] - mut['time']) > TOLERANCE)):
                print "! " + i
                print  "  Original: " + formatDic(ori)
                print  "  Mutagen:  " + formatDic(mut)
            else:
                print "~ " + i

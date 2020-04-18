# multiselect - A multi-threaded select replacement
#
# Relicensed under GPLv3 by daelstorm (2007)
#
# Copyright (C) 2007 daelstorm <daelstorm@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Original copyright notice below
# Copyright (C) 2007 Ingmar K. Steen (iksteen@gmail.com)
#
# define how large our socket sets may grow (used as a default for the
# multiselect() call).
MAX_SELECT_SOCKETS = 64

# import the necessary modules
import select
import threading

import _thread


# multiselect call mimics select.select(r,w,x,timout=None) but starts threads
# if the fd sets grow beyond the specified limit
def multiselect(r_fds, w_fds, x_fds, timeout=None, limit=MAX_SELECT_SOCKETS):
    fds = []
    for fd in r_fds + w_fds + x_fds:
        if fd not in fds:
            fds.append(fd)

    # if we're using less than the limit, fall back to regular select
    if len(fds) < limit:
        return select.select(r_fds, w_fds, x_fds, timeout)

    # divide the fd sets into groups of max MAX_SELECT_SOCKETS sets
    fdsets = []
    while fds:
        fds_ = fds[:limit]
        fds = fds[limit:]
        fdsets.append(([fd for fd in fds_ if fd in r_fds],
                       [fd for fd in fds_ if fd in w_fds],
                       [fd for fd in fds_ if fd in x_fds]))

    # the return fd sets
    r_r_fds = []
    r_w_fds = []
    r_x_fds = []

    # first, run a cycle over all threads with a 0 timeout to prevent starvation
    for fdset in fdsets:
        r, w, x = select.select(fdset[0], fdset[1], fdset[2], 0)
        r_r_fds += r
        r_w_fds += w
        r_x_fds += x
    # if we have anything to return, return it. also return if the timeout is 0
    if r_r_fds or r_w_fds or r_x_fds or (timeout == 0):
        return r_r_fds, r_w_fds, r_x_fds

    # here's where things get hairy: more than MAX_SELECT_SOCKETS sockets,
    # a non-zero timeout and no immediately available sockets

    # done_event will be set once a select thread detects workable sockets
    done_event = threading.Event()

    # a lock to prevent race conditions when appending to the return fd sets
    lock = _thread.allocate_lock()

    # the select thread
    def thread_select(r_fds, w_fds, x_fds, r_r_fds, r_w_fds, r_x_fds, lock, done_event):
        # call select with the specified timeout
        r, w, x = select.select(r_fds, w_fds, x_fds, timeout)
        # acquire the lock
        lock.acquire()
        # append our sockets to the return sets
        r_r_fds += r
        r_w_fds += w
        r_x_fds += x
        # release our lock
        lock.release()
        # set the event to indicicate that we have socket ready
        done_event.set()

    # start the select threads
    for fdset in fdsets:
        _thread.start_new_thread(thread_select, fdset + (r_r_fds, r_w_fds, r_x_fds, lock, done_event))

    # wait for one of the threads to complete
    done_event.wait(timeout)

    # acquire the lock
    lock.acquire()

    # collect the return data
    ret = (r_r_fds, r_w_fds, r_x_fds)

    # release the lock
    lock.release()

    # return our data
    return ret


if __name__ == '__main__':
    import socket
    import random
    fds = []
    files = {}
    for i in range(100):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(('www.nxs.nl', 80))
        s.send('GET /files/100mb.bin\r\n')
        fds.append(s)
        files[s] = open("data/100mb.%03i" % i, 'wb')
    while fds:
        r, w, x = multiselect(fds, [], [], None, 25)
        if r:
            print('data on fds:', ', '.join([str(fd.fileno()) for fd in r]))
            for s in r:
                data = s.recv(int(random.random() * 4096) + 1)
                if not data:
                    files[s].close()
                    del files[s]
                    fds.remove(s)
                else:
                    files[s].write(data)
    print('done')

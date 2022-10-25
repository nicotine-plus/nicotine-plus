# COPYRIGHT (C) 2022 Nicotine+ Contributors
#
# GNU GENERAL PUBLIC LICENSE
#    Version 3, 29 June 2007
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

import sched
import time

from threading import Thread


class Scheduler(Thread):
    """ Class that allows for scheduling one-time and repeating events """

    def __init__(self):

        super().__init__(name="SchedulerThread", daemon=True)
        self._scheduler = sched.scheduler()
        self._event_id = 0
        self._events = {}

        self.start()

    def _callback_one_time(self, callback, event_id):
        self._events.pop(event_id, None)
        callback()

    def _callback_repeat(self, delay, callback, event_id):
        callback()
        self._add_repeat(delay, callback, event_id)

    def _add_repeat(self, delay, callback, event_id):
        self._events[event_id] = self._scheduler.enter(
            delay=delay, priority=1, action=self._callback_repeat, argument=(delay, callback, event_id))

    def add(self, delay, callback, repeat=False):

        self._event_id += 1

        if repeat:
            self._add_repeat(delay, callback, self._event_id)

        else:
            self._events[self._event_id] = self._scheduler.enter(
                delay=delay, priority=1, action=self._callback_one_time, argument=(callback, self._event_id))

        return self._event_id

    def cancel(self, event_id):

        event = self._events.pop(event_id, None)

        if event is not None:
            self._scheduler.cancel(event)

    def run(self):

        while True:
            next_event_time = self._scheduler.run(blocking=False)

            if next_event_time is None or next_event_time > 1:
                next_event_time = 1

            time.sleep(next_event_time)


scheduler = Scheduler()

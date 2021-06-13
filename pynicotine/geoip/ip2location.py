# MIT License
#
# Copyright (c) 2021 Nicotine+ Team
# Copyright (c) 2017 IP2Location.com
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import mmap
import struct
import socket


MAX_IPV4_RANGE = 4294967295


class IP2Location:
    """ IP2Location country database """

    def __init__(self, filename):

        with open(filename, 'rb') as db1:
            try:
                self._f = mmap.mmap(db1.fileno(), 0, prot=mmap.PROT_READ)
            except AttributeError:
                self._f = mmap.mmap(db1.fileno(), 0, access=mmap.ACCESS_READ)

        self._dbtype = struct.unpack('B', self._f.read(1))[0]
        self._dbcolumn = struct.unpack('B', self._f.read(1))[0]
        self._dbyear = struct.unpack('B', self._f.read(1))[0]
        self._dbmonth = struct.unpack('B', self._f.read(1))[0]
        self._dbday = struct.unpack('B', self._f.read(1))[0]
        self._ipv4dbcount = struct.unpack('<I', self._f.read(4))[0]
        self._ipv4dbaddr = struct.unpack('<I', self._f.read(4))[0]
        self._ipv6dbcount = struct.unpack('<I', self._f.read(4))[0]
        self._ipv6dbaddr = struct.unpack('<I', self._f.read(4))[0]
        self._ipv4indexbaseaddr = struct.unpack('<I', self._f.read(4))[0]
        self._ipv6indexbaseaddr = struct.unpack('<I', self._f.read(4))[0]

    def get_country_code(self, addr):
        return self._get_record(addr)

    def _readi(self, offset):
        self._f.seek(offset - 1)
        return struct.unpack('<I', self._f.read(4))[0]

    def _read_record(self, mid):

        baseaddr = self._ipv4dbaddr
        col_offset = baseaddr + mid * (self._dbcolumn * 4) + 4 - 1
        country_offset = struct.unpack('<I', self._f[col_offset:col_offset + 4])[0]

        self._f.seek(country_offset)
        length = struct.unpack('B', self._f.read(1))[0]
        country_code = self._f.read(length).decode('utf-8')

        return country_code

    def _get_record(self, ip_address):

        low = 0
        ipnum = struct.unpack('!L', socket.inet_aton(ip_address))[0]

        if ipnum == MAX_IPV4_RANGE:
            ipno = ipnum - 1
        else:
            ipno = ipnum

        off = 0
        baseaddr = self._ipv4dbaddr
        high = self._ipv4dbcount
        if self._ipv4indexbaseaddr > 0:
            indexpos = ((ipno >> 16) << 3) + self._ipv4indexbaseaddr
            low = self._readi(indexpos)
            high = self._readi(indexpos + 4)

        while low <= high:
            mid = int((low + high) / 2)
            ipfrom = self._readi(baseaddr + (mid) * (self._dbcolumn * 4 + off))
            ipto = self._readi(baseaddr + (mid + 1) * (self._dbcolumn * 4 + off))

            if ipfrom <= ipno < ipto:
                return self._read_record(mid)

            if ipno < ipfrom:
                high = mid - 1
            else:
                low = mid + 1

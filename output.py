#!/usr/bin/python3
# vim: set ai et ts=4 sw=4 tw=80 fileencoding=utf-8:

import sys
import re
from specparse import SpecTags
import colorama as col

class FormOut:
    def __init__(self):
        col.init(autoreset=True)
        self.upav_norq = col.Fore.RED + col.Style.BRIGHT
        self.upav_wirq = col.Fore.GREEN
        self.formstr   = '{:55s} {:15s} {:15s} {:15s}'
    
    def print(self, key, propmap):
        self.style = ''
        outmsg     = b''
        if propmap['update']:
            rq         = propmap['reqs']
            rqmsg      = ' {:s} [{:s}]'.format(rq[0],rq[1][:35]) if rq[1] else ''
            self.style = self.upav_wirq if rqmsg else self.upav_norq
            outmsg     = u'↑{:s}'.format(rqmsg).encode('utf-8')
        print(self.style + self.formstr.format(key,
                                               propmap['specVer'].public,
                                               propmap['upsVer'].public,
                                               outmsg.decode('utf-8')))

    def printAll(self, stmap):
        for k in stmap.keys():
            self.print(k, stmap[k])
       

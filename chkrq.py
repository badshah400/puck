#!/usr/bin/python3
# vim: set ai et ts=4 sw=4 tw=80 fileencoding=utf-8:

import sys
import osc.conf
import osc.core
from pkglistparse import PrjPkgList
from lxml import etree

def chkrq(prj,pkg):
    apiurl = osc.conf.config['apiurl']

    u   = osc.core.makeurl(apiurl, ['request'],
                           query = { 'view'    : 'collection', 
                                     'project' : prj,
                                     'package' : pkg,
                                     'limit'   : 1,
                                     'states'  : 'new,review' })
    fi = osc.core.http_GET(u)

    # Join all lines and read them into an etree object
    collxml = etree.fromstring(b''.join(fi.readlines()))

    nreq = int(collxml.get('matches'))                # Get no. of new/review requests

    if not nreq:                                      # nreq = 0 => no requests
        return (u'', None)
    else:
        descr = collxml[0].find('description').text   # Get text in <description> node...
        descr = descr.splitlines()[0]                 # ... keeping only first line

        return (u'r', descr)

if __name__ == '__main__':
    osc.conf.get_config()
    pkgs = []
    if len(sys.argv) == 1:
        pkgs = ['science/plplot']
    else:
        for a in sys.argv[1:]:
            pkgs.append(a)

    f = PrjPkgList(pkgs)

    for prj, pkg in f.List():
        u, msg = chkrq(prj, pkg)
        if msg:
            print('{:s} [{:s}]'.format(u, msg))

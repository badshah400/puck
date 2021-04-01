#!/usr/bin/python3
# vim: set ai et ts=4 sw=4 tw=80 fileencoding=utf-8:

import sys
import osc.conf
import osc.core
from pkglistparse import PrjPkgList
from lxml import etree

def chkrq(prj,pkg):
    apiurl  = osc.conf.config['apiurl']
    u       = osc.core.makeurl(apiurl, ['request'],
                               query = { 'view'    : 'collection',
                                         'project' : prj,
                                         'package' : pkg,
                                         'limit'   : 1,
                                         'states'  : 'new,review' })
    fi      = osc.core.http_GET(u)

    collxml = etree.fromstring(b''.join(fi.readlines()))
                                                      # Join all lines into a byte-string
                                                      # and read into etree object
    nreq    = int(collxml.get('matches'))             # Get no. of new/review requests

    if nreq:                                          # nreq = 0 => no requests
        target = collxml[0].find('.//target')         # To check if target matches
        tgtprj = target.get('project')
        tgtpkg = target.get('package')
        if (tgtprj == prj) and (tgtpkg == pkg):
            descr = collxml[0].find('description')
                                                      # Get text in <description> node...
            descr = descr.text.splitlines()[0] if descr else ''
                                                      # ... keeping only first line
            rqid  = collxml[0].get('id')              # Get the request id
            return (u'sr#{:s}'.format(rqid), descr)
        else:
            return None
    else:
        return None

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

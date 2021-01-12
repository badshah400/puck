#!/usr/bin/python3
# vim: set ai et ts=4 sw=4 tw=80 fileencoding=utf-8:

import osc.conf
import osc.core
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
    numcollect = etree.fromstring(b''.join(fi.readlines()).decode('utf-8'))
    nreq = int(numcollect.get('matches'))
    if not nreq:
        return (u'', None)
    else:
        descr  = numcollect[0].find('description').text
        eolidx = descr.find('\n')
        return (u'r', descr[:eolidx])

if __name__ == '__main__':
    osc.conf.get_config()
    u, msg = chkrq('science', 'plplot')
    print('{:s} [{:s}]'.format(u, msg))

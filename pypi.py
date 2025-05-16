#!/usr/bin/python3
# vim: set ai et ts=4 sw=4 tw=80 fileencoding=utf-8:

import sys
import os
from string import Template
import re
from os import path
import feedparser as fp
from packaging.version import Version, parse
import osc.conf
from specparse import SpecTags
from pkglistparse import PrjPkgList
from errors import Errors
from stdver import stdver
from chkrq import chkrq
from output import FormOut

# initialize osc configuration
osc.conf.get_config()
apiurl = osc.conf.config['apiurl']

errs = Errors()

def pypiLastVer(prj):
    urlTemp = Template('https://pypi.org/rss/project/${proj}/releases.xml')
    url     = urlTemp.substitute(proj=prj)
    d       = fp.parse(url)
    if not len(d.entries):
        # TRY python-$prj as prjname
        url = urlTemp.substitute(proj='python-{:s}'.format(prj))
        d   = fp.parse(url)
        if not len(d.entries):
            global errs
            errs.Append('{:s}: Invalid pypi project'.format(prj))
            return Version('0.0.0')

    ver = Version('0.0.0')
    for e in d.entries:
        last_tag = e
        ver      = stdver(last_tag.title)
        if not Version(ver).is_prerelease:
            break
    return ver

if __name__ == '__main__':
    out = FormOut()
    pypre   = re.compile(r'^python[2-3]?\-')
    if len(sys.argv) == 1:
        f = PrjPkgList.fromfile('pypipkg.txt')
    else:
        pkgs = []
        for a in sys.argv[1:]:
            pkgs.append(a)
        f = PrjPkgList(pkgs)

    for prj, pkg in f.List():
        idstr   = prj + '/' + pkg
        pypiprj  = pypre.sub('', pkg)
        stags   = SpecTags(prj, pkg)
        url     = stags.Url()
        src_url = stags.SourceUrl()

        statusmap = {'specVer' : parse(stags.Version()),
                      'upsVer' : parse(pypiLastVer(pypiprj)),
                      'reqs'   : None,
                      'update' : False
                    }

        if statusmap['upsVer'] > statusmap['specVer']:
            rq                  = chkrq(prj, pkg)
            statusmap['reqs']   = rq
            statusmap['update'] = True
        
        out.print(idstr, statusmap)

errs.Print()

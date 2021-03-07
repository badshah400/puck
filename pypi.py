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
import colorama as col

col.init(autoreset=True)

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

    last_tag = d.entries[0]
    ver      = stdver(last_tag.title)
    return ver

if __name__ == '__main__':
    pypre   = re.compile('^python[2-3]?\-')
    if len(sys.argv) == 1:
        f = PrjPkgList.fromfile('pypipkg.txt')
    else:
        pkgs = []
        for a in sys.argv[1:]:
            pkgs.append(a)
        f = PrjPkgList(pkgs)

    for prj, pkg in f.List():
        pypiprj  = pypre.sub('', pkg)
        stags   = SpecTags(prj, pkg)
        url     = stags.Url()
        src_url = stags.SourceUrl()
        # print(srcURL)
        # pypiprj = src_url.split('/')[4]
        # if not re.search(r'pythonhosted\.com', src_url):
        #     if not re.search(r'pypi\.org', url):
        #         errs.Append(r'{:s}/{:s}: Source does not point to PyPI URL'
        #                    .format(prj,pkg))
        #         continue
        
        specVer = parse(stags.Version())
        pVer    = parse(pypiLastVer(pypiprj))

        newer = b''
        colour = ''
        if pVer > specVer:
            rq    = chkrq(prj, pkg)
            rqmsg = ' {:s} [{:s}]'.format(rq[0],rq[1][:35]) if rq[1] else ''
            newer = u'↑{:s}'.format(rqmsg).encode('utf-8')
            colour = col.Fore.GREEN if len(rqmsg) else col.Fore.RED + col.Style.BRIGHT

        print(colour + '{:55s} {:15s} {:15s} {:15s}'
              .format(prj+'/'+pkg, specVer.public, pVer.public, newer.decode('utf-8')))

errs.Print()

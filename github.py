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

def ghLastVer(ghuser, ghrepo):
    urlTemp = Template('https://github.com/${user}/${repo}/tags.atom')
    url     = urlTemp.substitute(user=ghuser, repo=ghrepo)
    d       = fp.parse(url)
    if not len(d.entries):
        global errs
        errs.Append('{:s}/{:s}: Invalid github project'.format(ghuser, ghrepo))
        return Version('0.0.0')

    last_tag = d.entries[0]
    ver      = last_tag.id.split('/')[-1]
    return stdver(ver)

if __name__ == '__main__':
    if len(sys.argv) == 1:
        f = PrjPkgList.fromfile('ghpkg.txt')
    else:
        pkgs = []
        for a in sys.argv[1:]:
            pkgs.append(a)
        f = PrjPkgList(pkgs)

    for prj, pkg in f.List():
        stags   = SpecTags(prj, pkg)
        url     = stags.Url()
        src_url = stags.SourceUrl()

        ghuser, ghrepo = src_url.split('/')[3:5]
        if not re.search(r'github\.com', src_url):
            if not re.search(r'github\.com', url):
                errs.Append(r'{:s}/{:s}: Source does not point to github URL'
                           .format(prj,pkg))
                continue
            else:
                ghuser, ghrepo = url.split('/')[3:5]
        
        specVer = parse(stags.Version())
        ghVer   = parse(ghLastVer(ghuser, ghrepo))

        newer = b''
        colour = ''
        if ghVer > specVer:
            rq    = chkrq(prj, pkg)
            rqmsg = ' {:s} [{:s}]'.format(rq[0],rq[1][:35]) if rq[1] else ''
            newer = u'↑{:s}'.format(rqmsg).encode('utf-8')
            colour = col.Fore.GREEN if len(rqmsg) else col.Fore.RED + col.Style.BRIGHT

        print(colour + '{:55s} {:15s} {:15s} {:15s}'
              .format(prj+'/'+pkg, specVer.public, ghVer.public, newer.decode('utf-8')))

errs.Print()

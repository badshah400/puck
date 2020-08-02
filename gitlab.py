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
from vercomp import NewUpstreamVer
from pkglistparse import PrjPkgList
from errors import Errors

# initialize osc configuration
osc.conf.get_config()
apiurl = osc.conf.config['apiurl']

errs = Errors()

def glLastVer(gurl):
    urlTemp = Template('${url}/-/tags?format=atom')
    url     = urlTemp.substitute(url=gurl)
    d       = fp.parse(url)
    if not len(d.entries):
        d   = fp.parse(url)
        if not len(d.entries):
            global errs
            errs.Append('{:s}: Invalid Gitlab URL'.format(gurl))
            return ('0.0.0')

    alphastr = re.compile('alpha', re.I)
    betastr  = re.compile('beta', re.I)

    last_tag = d.entries[0]
    ver      = last_tag.title
    nametag  = re.compile('^[a-zA-Z_.-]+')
    ver      = nametag.sub('', ver)
    return ver

if __name__ == '__main__':
    f = []
    if len(sys.argv) == 1:
        with open('glpkg.txt') as F:
            lines = F.readlines()
        for line in lines:
            prjpkg, glurl = line.split()
            prj, pkg      = prjpkg.split('/')
            f.append([prj, pkg, glurl])
    else:
        pkgs = []
        for a in sys.argv[1:]:
            pkgs.append(a)
        f = PrjPkgList(pkgs)

    for prj, pkg, gl in f:
        stags   = SpecTags(prj, pkg)
        url     = stags.Url()
        src_url = stags.SourceUrl()
        specgl  = gl if gl != '-' else '/'.join(src_url.split('/')[0:5])
        
        rehttps = re.compile('^https?://')
        if not rehttps.match(specgl):
            errs.Append('{:s}: Invalid Gitlab URL'.format(specgl))
            continue

        specVer = Version(stags.Version())
        
        pVer     = Version(glLastVer(specgl))

        newer = u'↑'.encode('utf-8') if (pVer > specVer) else b''
        print('{:55s} {:15s} {:15s} {:15s}'
              .format(prj+'/'+pkg, specVer.public, pVer.public, newer.decode('utf-8')))

errs.Print()

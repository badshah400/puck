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

# Local modules
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

def glLastVer(gurl):
    urlTemp = Template('${url}/-/tags?sort=updated_desc&format=atom')
    url     = urlTemp.substitute(url=gurl)
    d       = fp.parse(url)
    if not len(d.entries):
        d   = fp.parse(url)
        if not len(d.entries):
            global errs
            errs.Append('{:s}: Invalid Gitlab URL'.format(gurl))
            return '0.0.0'

    last_tag = d.entries[0]
    ver      = last_tag.title.replace('_', '.')
    return stdver(ver)

if __name__ == '__main__':
    f = []
    out = FormOut()
    if len(sys.argv) == 1:
        with open('glpkg.txt') as F:
            lines = F.readlines()
        for line in lines:
            prjpkg, glurl = line.split()
            prj, pkg      = prjpkg.split('/')
            f.append([prj, pkg, glurl])
    else:
        prjpkg   = sys.argv[1]
        prj, pkg = prjpkg.split('/')
        glurl    = '-'
        f.append([prj, pkg, glurl])

    statusmap = {}
    for prj, pkg, gl in f:
        idstr   = prj + '/' + pkg
        stags   = SpecTags(prj, pkg)
        url     = stags.Url()
        src_url = stags.SourceUrl()
        src_url = re.sub('%{?url}?', url, src_url)   # Replace %{url} in source URL with url
        src_url = re.sub(r'%{?name}?', pkg, src_url) # Handle %name in source URL

        if src_url.split('/')[0] != 'https:':
            # This means the src_url is just the file name, e.g. when using a
            # _service file
            src_url = url + '/-/archive/{:s}/{:s}'.format(stags.Version(),
                                                          src_url)

        specgl  = gl if gl != '-' else '/'.join(src_url.split('/')[0:5])

        rehttps = re.compile('^https?://')
        if not rehttps.match(specgl):
            errs.Append('{:s}: Invalid Gitlab URL'.format(specgl))
            continue

        uver    = glLastVer(specgl)
        try:
            parse(uver)
        except:
            errs.Append(r'{:s}/{:s}: Invalid package versiion {:s}'
                       .format(prj, pkg, uver))
            continue

        statusmap[idstr] = { 'specVer' : parse(stags.Version()),
                             'upsVer'  : parse(uver),
                             'reqs'    : None,
                             'update'  : False
                           }

        if statusmap[idstr]['upsVer'] > statusmap[idstr]['specVer']:
            rq                         = chkrq(prj, pkg)
            statusmap[idstr]['reqs']   = rq
            statusmap[idstr]['update'] = True

        out.print(idstr, statusmap[idstr])

    # out.printAll(statusmap)

errs.Print()

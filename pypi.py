#!/usr/bin/python3
# vim: set ai et ts=4 sw=4 tw=80 fileencoding=utf-8:

import sys
import os
from string import Template
import re
from os import path
import feedparser as fp

import osc.conf
from specparse import SpecTags
from vercomp import NewUpstreamVer
from pkglistparse import PrjPkgList
from errors import Errors

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
            return ('0.0.0')

    alphastr = re.compile('alpha', re.I)
    betastr  = re.compile('beta', re.I)

    last_tag = d.entries[0]
    ver      = last_tag.title
    nametag  = re.compile('^[a-zA-Z_.-]+')
    ver      = nametag.sub('', ver)
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
        
        specVer = stags.Version()
        
        pVer     = pypiLastVer(pypiprj)

        newer = u'↑'.encode('utf-8') if NewUpstreamVer(pVer, specVer) else b''
        print('{:55s} {:15s} {:15s} {:15s}'
              .format(prj+'/'+pkg, specVer, pVer, newer.decode('utf-8')))

errs.Print()

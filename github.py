#!/usr/bin/python
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

def ghLastVer(ghuser, ghrepo):
    urlTemp = Template('https://github.com/${user}/${repo}/releases.atom')
    url     = urlTemp.substitute(user=ghuser, repo=ghrepo)
    d       = fp.parse(url)
    if not len(d.entries):
        global errs
        errs.Append('{:s}/{:s}: Invalid github project'.format(ghuser, ghrepo))
        return ('0.0.0')

    alphastr = re.compile('alpha', re.I)
    betastr  = re.compile('beta', re.I)
    for item in d.entries:
        id    = item.id
        title = item.title
        ver = id.split('/')[-1]
        # Strip any leading name tags, etc. we just want the version
        nametag = re.compile('^[a-zA-Z_.-]+')
        if re.match(nametag, ver):
            ver = nametag.sub('', ver)
        if re.search(alphastr, ver) or re.search(betastr, ver):
            continue
        if re.search(alphastr, title) or re.search(betastr, title):
            continue
        return(ver)

if __name__ == '__main__':
    f = PrjPkgList('ghpkg.txt')

    for prj, pkg in f.List():

        stags   = SpecTags(prj, pkg)
        src_url = stags.SourceUrl()
#        print(srcURL)
        ghuser, ghrepo = src_url.split('/')[3:5]
        if not re.search(r'github\.com', src_url):
            errs.Append(r'{:s}/{:s}: Source does not point to github URL'
                         .format(prj,pkg))
            continue
        
        specVer = stags.Version()
#        print(specver)
        
        ghVer     = ghLastVer(ghuser, ghrepo)

        newer = u'↑'.encode('utf-8') if NewUpstreamVer(ghVer, specVer) else ''
        print('{:45s} {:15s} {:15s} {:15s}'
              .format(prj+'/'+pkg, specVer, ghVer, newer))

errs.Print()

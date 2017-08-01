#!/usr/bin/python2
# vim: set ai et ts=4 sw=4 tw=80 fileencoding=utf-8:

import sys
import os
from os import path
import urllib2
import re
from lxml import etree #import ElementTree as ET
import osc.conf
from specparse import SpecTags
from vercomp import NewUpstreamVer
from errors import Errors
from pkglistparse import PrjPkgList

# initialize osc configuration
osc.conf.get_config()
apiurl = osc.conf.config['apiurl']

errs = Errors()

def hepVer(prj):
    response = urllib2.urlopen('https://www.hepforge.org/downloads/' + prj)
    html = response.read()
    strongs = etree.HTML(html).findall('.//strong')
    try:
        strongver=strongs[1]
    except:
        return('-')
    return(strongver.text)


if __name__ == '__main__':
    f = PrjPkgList('hfpkg.txt')

    for prj, pkg in f.List():
        sp  = SpecTags(prj, pkg)
        url = sp.Url()
        srcURL = sp.SourceUrl()
#        print(url)
#        print(srcURL)
        if re.search(r'hepforge\.org', url):
            re_http = re.compile('https?://')
            hepprj = re_http.sub('', url).split('.')[0]
        elif re.search(r'hepforge\.org', srcURL):
            hepprj = srcURL.split('/')[4]
        else:
            errs.Append(r'{:s}/{:s}: Source does not point to hepforge URL'
                         .format(prj,pkg))
            continue
        
        specVer = sp.Version()
#        print(specver)
        
        hepver     = hepVer(hepprj)
#        print(hepver)

        try:
            newer = u'↑'.encode('utf-8') if NewUpstreamVer(hepver, specVer) else ''
        except:
            newer = ''
            errs.Append(r'{:s}/{:s}: Invalid version from hepforge'
                         .format(prj,pkg))
        print('{:45s} {:15s} {:15s} {:15s}'
              .format(prj+'/'+pkg, specVer, hepver.encode('utf-8'), newer))

errs.Print()

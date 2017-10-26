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

def hepVer(prj, pkgext=None):
    exts = ['.bz2', '.gz', '.tar', '.tgz', '.xz', '.7z', '.zip', '.rar']
    response = urllib2.urlopen('https://www.hepforge.org/downloads/' + prj)
    html = response.read()
    strongs = etree.HTML(html).findall('.//strong')
    try:
        if not strongs:
            raise Exception("Not listed on hepforge downloads page")
        for i in range(1,len(strongs)-1,3):
            strongver = strongs[i]
            strext    = '.' + strongs[i+1][0].get('href').split('.')[-1]
            if not pkgext:
                if strext in exts:
                    break
            else:
                if strext == pkgext:
                    break
    except:
        return('-')
    return(strongver.text.strip())


if __name__ == '__main__':
    f = PrjPkgList.fromfile('hfpkg.txt')

    for prj, pkg in f.List():
        sp  = SpecTags(prj, pkg)
        url = sp.Url()
        srcURL = sp.SourceUrl()
#        print(url)
#        print(srcURL)
        if re.search(r'hepforge\.org', url):
            re_http = re.compile('^https?://')
            hepprj = re_http.sub('', url).split('.')[0]

            # Handle URL's in the form: http://projects.hepforge.org/pyfeyn/
            if hepprj == 'projects':
                hepprj = re_http.sub('', url).rstrip('/').split('/')[-1]

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

### PYTHIA CHECK ###
pythia_url = 'http://home.thep.lu.se/~torbjorn/pythia82html/UpdateHistory.html'
response   = urllib2.urlopen(pythia_url)
html       = response.read()
li_all     = etree.HTML(html).findall('.//li')
li0_text   = li_all[0].text

pythia_ver, rel_date = li0_text.split(':')
rel_date   = rel_date.strip()

prj = 'science'
pkg = 'pythia'
sp  = SpecTags(prj, pkg)
specVer = sp.Version()
try:
    newer = (u'↑'.encode('utf-8') if NewUpstreamVer(pythia_ver, specVer)
             else '')
except:
    newer = ''
    errs.Append(r'{:s}/{:s}: Invalid version from Pythia webpage'
                 .format(prj,pkg))

print('{:45s} {:15s} {:15s} {:15s}'
      .format(prj+'/'+pkg, specVer, pythia_ver.encode('utf-8'), newer))

errs.Print()

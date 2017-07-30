#!/usr/bin/python
# vim: set ai et ts=4 sw=4 tw=80 fileencoding=utf-8:

import sys
import os
from string import Template
import re
from os import path
from lxml import etree
import requests as rq
from io import BytesIO
import feedparser as fp
from subprocess import call, check_output, PIPE
from tempfile import NamedTemporaryFile

import osc.conf
import osc.core

# initialize osc configuration
osc.conf.get_config()
apiurl = osc.conf.config['apiurl']

errs = []

def newver(ver1, ver2):
    arr1 = ver1.split('.')
    arr2 = ver2.split('.')
    len1 = len(arr1)
    len2 = len(arr2)
    if len1 <= len2:
        for i in range(0, len1):
            if int(arr1[i]) > int(arr2[i]):
                return True
            elif int(arr1[i]) < int(arr2[i]):
                return False
            else:
                continue
        return False
    elif len1 > len2:
        for i in range(0, len2):
            if int(arr1[i]) > int(arr2[i]):
                return True
            elif int(arr1[i]) < int(arr2[i]):
                return False
            else:
                continue
        return True
        

def ghLastVer(ghuser, ghrepo):
    urlTemp = Template('https://github.com/${user}/${repo}/releases.atom')
    url     = urlTemp.substitute(user=ghuser, repo=ghrepo)
    d       = fp.parse(url)
    if not len(d.entries):
        global errs
        errs.append('{:s}/{:s}: Invalid github project'.format(ghuser, ghrepo))
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
    re_s0  = re.compile('Source0?:.*')
    re_ver = re.compile('Version:.*')

    f = open('pkglist.txt', 'r')

    for line in f:
        # IGNORE COMMENTED LINES
        if line[0] == '#':
            continue

        # REPLACE SPACE BY '/' THEN SPLIT BY '/'
        line = line.replace(' ', '/')
#        print(line)
        l = line.split('/')
        if len(l) != 2:
            continue
#        print(l)
        prj = l[0]
        pkg = l[1].rstrip('\n')
        u   = osc.core.makeurl(apiurl, ['source', prj, pkg, pkg + '.spec'],
                               query = { 'expand': 1 })

        fi = osc.core.http_GET(u)
        try:
            spec = ''.join(fi.readlines())
        except:
            print("Error fetching spec file.")
        
        cachedir = path.join('.', '.osc')
        if not path.exists(cachedir):
            os.mkdir(cachedir)
        
        with NamedTemporaryFile(mode='w', suffix='.spec', dir=cachedir) as f:
            f.write(spec)
            f.flush()
            
#            print(f.name)
            src0 = check_output(['rpmdev-spectool', '-S', f.name])
#            print(src0)
        
        if src0:
            srcURL = (re_s0.search(src0).group()).split(' ')[-1]
        else:
            srcURL = re.search(r'Source0?:.*', spec).group().split(' ')[-1]
#        print(srcURL)
        ghuser, ghrepo = srcURL.split('/')[3:5]
        if not re.search(r'github\.com', srcURL):
            errs.append(r'{:s}/{:s}: Source does not point to github URL'
                         .format(prj,pkg))
            continue
        
        specVer = (re_ver.search(spec).group()).split(' ')[-1]
#        print(specver)
        
        ghVer     = ghLastVer(ghuser, ghrepo)

        newer = u'↑'.encode('utf-8') if newver(ghVer, specVer) else ''
        print('{:45s} {:15s} {:15s} {:15s}'
              .format(prj+'/'+pkg, specVer, ghVer, newer))

if errs:
    print("\nCollected error messages")    
    for err in errs:
        print(err)


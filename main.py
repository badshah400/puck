#!/usr/bin/python3
# vim: set ai et ts=4 sw=4 tw=80:

import sys
import os
from string import Template
import re
from os import path
from lxml import etree
import requests as rq
from io import BytesIO
import feedparser as fp
from subprocess import run, PIPE

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

        pr = run(['./oscGetPkgVer.sh', prj, pkg], stdout=PIPE, stderr=PIPE)
        reserr = pr.stderr.decode('utf-8')
        if len(reserr) > 0:
            errs.append('{:s}/{:s}: {:s}'.
                        format(prj, pkg, reserr.rstrip('\n')))
            continue

        resstr = pr.stdout.decode('utf-8').split()
        oscPkgVer = resstr[-1]
        ghVer     = ghLastVer(resstr[0], resstr[1])

        newer = '↑' if newver(ghVer, oscPkgVer) else ''
        print('{:45s} {:15s} {:15s} {:15s}'
              .format(prj+'/'+pkg, oscPkgVer, ghVer, newer))

if errs:
    print("\nCollected error messages")    
    for err in errs:
        print(err)


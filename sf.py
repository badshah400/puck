#!/usr/bin/python2
# vim: set ai et ts=4 sw=4 tw=80 fileencoding=utf-8:

import sys
import os
from os import path
from string import Template
import re
import feedparser as fp
from tempfile import NamedTemporaryFile
import osc.conf
from specparse import SpecTags
from vercomp import NewUpstreamVer
from pkglistparse import PrjPkgList
from errors import Errors
import osc.conf

# initialize osc configuration
osc.conf.get_config()
apiurl = osc.conf.config['apiurl']

errs = Errors()

def sfLastVer(sfprj, srcf, oldver):
    urlTemp = Template('https://sourceforge.net/projects/${prj}/rss')
    url     = urlTemp.substitute(prj=sfprj)
    d       = fp.parse(url)
    ver     = oldver
    verfind = False
    srcname, srcext = path.splitext(srcf)

    vertemp = '[0-9]+' + '(\.?[0-9]){0,6}' + '([aA]lpha.*)?([Bb]eta.*)?'
    anyver  = re.compile(r'[^a-zA-Z]{:s}'.format(vertemp))
    srcf    = srcf.replace(oldver, vertemp)
    srcname_anyver = re.compile(r'{:s}'.format(srcf))

    for item in d.entries:
        title     = item.title
        itemname  = title.split('/')[-1]
        matsrc_it = srcname_anyver.finditer(itemname)

        if not matsrc_it:
            continue

        for matsrc in matsrc_it:
            matver = anyver.search(matsrc.group())
            itemname, itemext = path.splitext(matsrc.group())

            if itemext == srcext:
                ver = matver.group().rstrip('.')
                if not re.match(r'^[0-9]', ver):
                    ver = ver[1:]
                verfind = True
                break

        if verfind:
            break;

    return (ver)

if __name__ == '__main__':
    sf_dlurl_re1  = re.compile('^downloads?\.sf\.net$|^downloads?\.sourceforge\.net$')
    sf_dlurl_re2  = re.compile('^sf\.net$|^sourceforge\.net$')
    sf_prjurl_re1 = re.compile('sourceforge\.net/projects/?|sf\.net/projects/?')
    sf_prjurl_re2 = re.compile('\.sourceforge\.net/?|\.sf\.net/?')
    
    if len(sys.argv) == 1:
        f = PrjPkgList('sfpkg.txt')
    else:
        pkgs = []
        for a in sys.argv[1:]:
            pkgs.append(a)
        f = PrjPkgList.frominputlist(pkgs)

    for prj, pkg in f.List():
        stags     = SpecTags(prj, pkg)
        src_url   = stags.SourceUrl()
        src_parts = src_url.split('/')[2:] # Drop the leading 'http://'
        src_file  = src_parts[-1]
        specVer   = stags.Version()

        sfprj     = ''

        # Figure out SF project name
        if (sf_dlurl_re1.match(src_parts[0])):
            # This works when the srcURL is of the form:
            # http://downloads.sourceforge.net/<sfprj>/<src_file>
            sfprj = src_parts[1]

        if (sf_dlurl_re2.match(src_parts[0])):
            # This works when the srcURL is of the form:
            # http://sourceforge.net/projects/mikmod/files/...
            sfprj = src_parts[1]

        elif (sf_prjurl_re1.search(stags.Url())):
            # http://sourceforge.net/projects/mathmod/
            sfprj = stags.Url().split('/')[4]

        elif (sf_prjurl_re2.search(stags.Url())):
            # If the srcURL does not point to a dowload(s).s*f*.net
            # then we look at the spec file's URL, and split the sfprj from
            # http://<sfprj>.sourceforge.net/
            sfprj = stags.Url().split('/')[2]
            sfprj = sfprj.split('.')[0]

        if not sfprj:
            errs.Append(r'{:s}/{:s}: Source does not point to sourceforge URL'
                         .format(prj,pkg))
            continue

        sfVer = sfLastVer(sfprj, src_file, specVer)

        newer = u'↑'.encode('utf-8') if NewUpstreamVer(sfVer, specVer) else ''
        print('{:45s} {:15s} {:15s} {:15s}'
              .format(prj+'/'+pkg, specVer, sfVer, newer))

errs.Print()

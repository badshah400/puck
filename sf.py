#!/usr/bin/python3
# vim: set ai et ts=4 sw=4 tw=80 fileencoding=utf-8:

import sys
import os
from os import path
from string import Template
import re
import feedparser as fp
from tempfile import NamedTemporaryFile
from specparse import SpecTags
from packaging.version import Version, parse
from pkglistparse import PrjPkgList
from errors import Errors
from stdver import stdver
from chkrq import chkrq
import osc.conf
from output import FormOut

# initialize osc configuration
osc.conf.get_config()
apiurl = osc.conf.config['apiurl']

errs = Errors()

def sfLastVer(sfprj, srcf, oldver):
    srcf            = srcf.replace('+', r'\+')
    urlTemp         = Template('https://sourceforge.net/projects/${prj}/rss?path=/')
    url             = urlTemp.substitute(prj=sfprj)
    d               = fp.parse(url)
    ver             = oldver
    verfind         = False
    srcname, srcext = path.splitext(srcf)

    vertemp         = '[0-9]+' + '(\.?[0-9]){0,6}' + '([aA]lpha.*)?([Bb]eta.*)?'
    anyver          = re.compile(r'[^a-zA-Z]{:s}'.format(vertemp))
    srcf            = srcf.replace(oldver, vertemp)
    srcname_anyver  = re.compile(r'{:s}'.format(srcf))

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
                # HACK: Drop 7z extension manually
                if itemext == '.7z':
                    ver = ver.rsplit('.', 1)[0]
                verfind = True
                break

        if verfind:
            break;

    return stdver(ver.replace('_', '.'))

if __name__ == '__main__':
    sf_dlurl_re1  = re.compile('^downloads?\.(sourceforge|sf)\.net$')
    sf_dlurl_re2  = re.compile('^(sourceforge|sf)\.net$')
    sf_prjurl_re1 = re.compile('(sourceforge|sf)\.net/projects/?')
    sf_prjurl_re2 = re.compile('\.(sourceforge|sf)\.(net|io)/?')
    url_http      = re.compile('^https?:')
    
    if len(sys.argv) == 1:
        f = PrjPkgList.fromfile('sfpkg.txt')
    else:
        pkgs = []
        for a in sys.argv[1:]:
            pkgs.append(a)
        f = PrjPkgList(pkgs)

    out = FormOut()
    for prj, pkg in f.List():
        idstr   = prj + '/' + pkg
        stags   = SpecTags(prj, pkg)
        url     = stags.Url()
        src_url = stags.SourceUrl()

        # If src_url is not a URL (e.g. using a service file, etc.)
        if not url_http.match(src_url):
            src_parts = [src_url]
        else:
            src_parts = src_url.split('/')[2:] # Drop the leading 'http://'

        src_file  = src_parts[-1]
        specVer   = parse(stags.Version())

        sfprj     = ''

        # Figure out SF project name
        if (sf_dlurl_re1.match(src_parts[0])):
            # This works when the srcURL is of the form:
            # http://downloads.sourceforge.net/<sfprj>/<src_file>
            # or http://downloads.sourceforge.net/project/<sfprj>/<src_file>
            sfprj = src_parts[2] if src_parts[1] == 'project' else src_parts[1]

        elif (sf_dlurl_re2.match(src_parts[0])):
            # This works when the srcURL is of the form:
            # http://sourceforge.net/projects/mikmod/files/...
            sfprj = src_parts[2]

        elif (sf_prjurl_re1.search(stags.Url())):
            # http://sourceforge.net/projects/mathmod/
            sfprj = stags.Url().split('/')[4]

        elif (sf_prjurl_re2.search(stags.Url())):
            # If the srcURL does not point to a dowload(s).s*f*.net
            # then we look at the spec file's URL, and split the sfprj from
            # http://<sfprj>.sourceforge.net/
            sfprj = url.split('/')[2]
            sfprj = sfprj.split('.')[0]

        if not sfprj:
            errs.Append(r'{:s}/{:s}: Source does not point to sourceforge URL'
                         .format(prj,pkg))
            continue

        specVer          = parse(stags.Version())
        # Hack for scintilla which drops the dots from tarball versions:
        # version 5.1.0 -> scintilla510.tgz; use no-dots-version
        if sfprj == 'scintilla':
            specVerstr = specVer.public.replace('.', '')
            specVer    = Version(specVerstr)

        uver   = sfLastVer(sfprj, src_file, specVer.public)
        try:
            parse(uver)
        except:
            errs.Append(r'{:s}/{:s}: Invalid package versiion {:s}'
                       .format(prj, pkg, uver))
            continue

        statusmap = { 'specVer' : specVer,
                      'upsVer'  : parse(uver),
                      'reqs'    : None,
                      'update'  : False
                    }

        if statusmap['upsVer'] > statusmap['specVer']:
            rq                  = chkrq(prj, pkg)
            statusmap['reqs']   = rq
            statusmap['update'] = True

        out.print(idstr, statusmap)

errs.Print()

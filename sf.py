#!/usr/bin/python3
# vim: set ai et ts=4 sw=4 tw=80 fileencoding=utf-8:

import sys
from os import path
import re
import requests
from packaging.version import Version, parse
import osc.conf
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

def sfLastVer(sfproj, srcf, oldver):
    '''Get last published version on SourceForge
    '''

    srcf    = srcf.replace('+', r'\+')
    headers = {
               'Accept'        : '*/*',
               'User-Agent'    : 'curl/8.14.1',
               'cache-control' : 'no-cache',
               'Connection'    : 'keep-alive',
              }
    sf_data = requests.get(f'https://sourceforge.net/projects/{sfproj}/best_release.json',
                           headers=headers, timeout=30,
                           allow_redirects=False)
    if sf_data.status_code == requests.codes['ok']:
        sf_json = sf_data.json()
    else:
        errs.Append(f'{pkg!s}/{prj!s}: Unable to obtain sourceforge data.')
        sf_data.raise_for_status()
        return stdver('0.0.0')

    vertemp     = r'[0-9]+' + r'(\.?[0-9]){0,6}' + r'([aA]lpha.*)?([Bb]eta.*)?'
    anyver      = re.compile(f'[^a-zA-Z]{vertemp}')
    srcf        = srcf.replace(oldver, vertemp)
    sf_fname, _ = path.splitext(sf_json['release']['filename'])
    ver         = anyver.search(sf_fname).group()[1:]

    # Hack for scintilla
    if (sfproj == 'scintilla'):
        ver = ver.replace('.', '')
    return stdver(ver.replace('_', '.'))

if __name__ == '__main__':
    sf_dlurl_re1  = re.compile(r'^downloads?\.(sourceforge|sf)\.net$')
    sf_dlurl_re2  = re.compile(r'^(sourceforge|sf)\.net$')
    sf_prjurl_re1 = re.compile(r'(sourceforge|sf)\.net/projects/?')
    sf_prjurl_re2 = re.compile(r'\.(sourceforge|sf)\.(net|io)/?')
    url_http      = re.compile(r'^https?:')

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

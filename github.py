#!/usr/bin/python3
# vim: set ai et ts=4 sw=4 tw=80 fileencoding=utf-8:

import sys
import os
from string import Template
import re
from os import path
import feedparser as fp
from packaging.version import Version, parse, InvalidVersion
import osc.conf
from specparse import SpecTags
from pkglistparse import PrjPkgList
from errors import Errors
from stdver import stdver
from chkrq import chkrq
from output import FormOut
from subprocess import CalledProcessError

# initialize osc configuration
osc.conf.get_config()
apiurl = osc.conf.config['apiurl']

errs = Errors()

def ghLastVer(ghuser, ghrepo):
    urlTemp = Template('https://github.com/${user}/${repo}/tags.atom')
    url     = urlTemp.substitute(user=ghuser, repo=ghrepo)
    d       = fp.parse(url)
    if not len(d.entries):
        global errs
        errs.Append('{:s}/{:s}: Invalid github project'.format(ghuser, ghrepo))
        return Version('0.0.0')

    # Loop entries to get tag with valid version, max 5 times, otherwise give up
    MAX_ENTRIES = 5
    for cnt in range(0, MAX_ENTRIES):
        last_tag = d.entries[cnt]
        ver      = last_tag.id.split('/')[-1]

        # ghrepo ending in digits messes up version search, drop them from tag name
        if end_num_patt := re.search(r'\d+$', ghrepo):
            ver = ver.replace(end_num_patt.string, '', 1)

        try:
            ver = parse(stdver(ver.replace('_', '.')))
            return ver
        except:
            pass

    errs.Append('{:s}/{:s}: Unable to obtain version from last {:d} tags'
                .format(ghuser, ghrepo, MAX_ENTRIES))
    return Version('0.0.0')


if __name__ == '__main__':
    out = FormOut()
    if len(sys.argv) == 1:
        f = PrjPkgList.fromfile('ghpkg.txt')
    else:
        pkgs = []
        for a in sys.argv[1:]:
            pkgs.append(a)
        f = PrjPkgList(pkgs)

    for prj, pkg in f.List():
        idstr   = prj + '/' + pkg
        try:
            stags   = SpecTags(prj, pkg)
        except RuntimeError as e:
            errs.Append(f'{prj}/{pkg}: {e}')
            continue
        except CalledProcessError as e:
            errs.Append(f'{prj}/{pkg}: rpmspec error while parsing specfile.')
            continue
        except:
            errs.Append('{:s}/{:s}: Failed to sparse spec file, invalid OBS '
                        'package?'.format(prj, pkg))
            continue
        url     = stags.Url()
        src_url = stags.SourceUrl()

        ghuser, ghrepo = src_url.split('/')[3:5]
        if not re.search(r'github\.com', src_url):
            if not re.search(r'github\.com', url):
                errs.Append(F'{prj}/{pkg}: Source does not point to github URL')
                continue

            ghuser, ghrepo = url.split('/')[3:5]

        # Handle %name in ghrepo
        ghrepo    = re.sub(r'%{?name}?', pkg, ghrepo)
        # Handle ghrepo ending in .git
        ghrepo    = re.sub(r'.git$', '', ghrepo)

        uver      = ghLastVer(ghuser, ghrepo)
        statusmap = {'specVer' : parse(stags.Version()),
                     'upsVer' : uver,
                     'reqs'   : None,
                     'update' : False
                    }

        if statusmap['upsVer'] > statusmap['specVer']:
            rq                  = chkrq(prj, pkg)
            statusmap['reqs']   = rq
            statusmap['update'] = True

        out.print(idstr, statusmap)

errs.Print()

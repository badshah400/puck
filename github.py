#!/usr/bin/python3
# vim: set ai et ts=4 sw=4 tw=100 fileencoding=utf-8:
# mypy: disable-error-code=import-untyped

import sys
from string import Template
import re
import feedparser as fp
from packaging.version import parse
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
        raise RuntimeError(f'Invalid github project "{ghrepo}"')

    # ghrepo ending in digits messes up version search, drop them from tag name
    end_num_patt = re.search(r'\d+$', ghrepo)
    # Loop entries to get tag with valid version, max 5 times, otherwise give up
    MAX_ENTRIES = 5
    for cnt in range(0, MAX_ENTRIES):
        last_tag = d.entries[cnt]
        ver      = last_tag.id.split('/')[-1]
        # Drop leading 'v' from tag
        ver      = ver[1:] if ver[0] == 'v' else ver
        ver      = ver.replace(end_num_patt.string, '', 1) if end_num_patt else ver

        try:
            return parse(stdver(ver.replace('_', '.')))
        except Exception:
            pass

    raise RuntimeError(f'Unable to obtain version from last {MAX_ENTRIES:d} tags')


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
        except CalledProcessError:
            errs.Append(f'{prj}/{pkg}: rpmspec error while parsing specfile.')
            continue
        except Exception:
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
        ghrepo = re.sub(r'%{?name}?', pkg, ghrepo)

        if ghrepo[0] == '%': # Leading % implies an rpm macro which is not %name
            bare_macro = ghrepo.lstrip('%').strip('{}')
            macro_line = re.search(rf'^%(define|global)\s+{bare_macro}\s+.*', stags.Spec(),
                                   flags=re.MULTILINE)
            try:
                macro_def = macro_line.group(0).split(' ')[2:]
            except AttributeError:
                errs.Append(f'{prj}/{pkg}: Error when resolving macro {ghrepo}')
                continue
            ghrepo = ''.join(macro_def)


        # Handle ghrepo ending in .git
        ghrepo = re.sub(r'.git$', '', ghrepo)

        try:
            uver   = ghLastVer(ghuser, ghrepo)
        except RuntimeError as e:
            errs.Append(f'{prj}/{pkg}: {e}')
            continue

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

# vim: set ai et ts=4 sw=4:
# SPDX-FileCopyrightText: 2025-present Atri Bhattacharya <atrib@duck.com>
#
# SPDX-License-Identifier: MIT
#
"""puck main module"""

import sys
import argparse
import logging as log
import re
from pathlib import Path
from textwrap import wrap
from urllib.error import HTTPError
from packaging.version import parse

from puck.__about__ import __version__

from puck.pkglistparse import PrjPkgList
from puck.output import FormOut
from puck.errors import Errors
from puck.specparse import CalledProcessError, SpecTags
from puck.chkrq import chkrq
from puck.github import GithubVersion

class GnuStyleHelpFormatter(argparse.HelpFormatter):
    """
    Format help string in GNU style, i.e.

    * `-s, --long           Help string for long`
      for an action that takes no argument
    * `-s, --long=LONG      Help string for long`
      for an action that requires an argument
    """

    def __init__(self, prog):
        """
        Initialise
        """
        argparse.HelpFormatter.__init__(self, prog, max_help_position=30, width=80)

    def _format_action_invocation(self, action):
        if not action.option_strings:
            default = self._get_default_metavar_for_positional(action)
            (metavar,) = self._metavar_formatter(action, default)(1)
            return metavar

        parts = []

        # if the Optional doesn't take a value, format is:
        #    -s, --long
        if action.nargs == 0:
            parts.extend(action.option_strings)

        # if the Optional takes a value, format is:
        #    -s, --long=ARGS
        else:
            default = self._get_default_metavar_for_optional(action)
            args_string = self._format_args(action, default)
            for option_string in action.option_strings:
                if len(option_string.lstrip("-")) == 1:  # short form
                    parts.append(f"{option_string}")
                else:  # long form
                    parts.append(f"{option_string}={args_string}")

        return ", ".join(parts)

    def _split_lines(self, text, width):
        return wrap(text, width=52, break_on_hyphens=False)


def parse_args():
    """Set up argparse options and parse input args accordingly"""
    parser = argparse.ArgumentParser(
        description=(
            "Compare package version on OBS against latest upstream tag/release"
            f" (version {__version__})."
        ),
        formatter_class=GnuStyleHelpFormatter,
        usage="%(prog)s [OPTIONS] FILENAME",
    )


class Puck:
    """
    The main class that simply handles user inputs and arguments and directs control to the
    appropriate action class
    """

    def __init__(self, args):
        self.args = parse_args(args)
        log.basicConfig(
            format="[%(levelname)s] %(message)s",
            level=((log.INFO // self.args.verbose) if self.args.verbose > 0 else log.WARN),
        )
        self.cwd = Path.cwd()


def cmp_version():
    out = FormOut()
    errs = Errors()
    if len(sys.argv) == 1:
        f = PrjPkgList.fromfile('./data/ghpkg.txt')
    else:
        pkgs = []
        for a in sys.argv[1:]:
            pkgs.append(a)
        f = PrjPkgList(pkgs)

    for prj, pkg in f.List():
        idstr   = prj + '/' + pkg
        try:
            stags = SpecTags(prj, pkg)
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
            G = GithubVersion(ghuser, ghrepo)
        except Exception as e:
            errs.Append(f'{prj}/{pkg}: {e}')
        try:
            uver   = G.get_version()
        except RuntimeError as e:
            errs.Append(f'{prj}/{pkg}: {e}')
            continue
        except HTTPError as h:
            errs.Append(f'{prj}/{pkg}: {h}')
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

if __name__ == '__main__':
    pass

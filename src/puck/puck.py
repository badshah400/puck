# vim: set ai et ts=4 sw=4:
# SPDX-FileCopyrightText: 2025-present Atri Bhattacharya <atrib@duck.com>
#
# SPDX-License-Identifier: MIT
#
# mypy: disable-error-code=import-untyped
# mypy: disable-error-code=union-attr
"""puck main module"""

import sys

# from logging import log
import argparse
import time
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


def parse_args(args):
    """Set up argparse options and parse input args accordingly"""
    parser = argparse.ArgumentParser(
        description=(
            "Compare package version on OBS against latest upstream tag/release"
            f" (version {__version__})."
        ),
        formatter_class=GnuStyleHelpFormatter,
        usage="%(prog)s [OPTIONS] NAME",
    )

    parser.add_argument(
        "name",
        metavar="FILENAME or PACKAGE",
        type=str,
        help="input file name or obs package id",
    )

    return parser.parse_args(args)


def resolve_unexp_macros(url: str, src_url: str, stags: SpecTags) -> dict[str, str]:
    """
    Returns a dictionary of in-file macros with their values as keys

    :url: The URL tag parsed from specfile (str)
    :src_url: The Source URl parsed from specfile; may not be a full URL (str)
    :returns: Dictionary with macro regex as key and macro value as its value (dict[str,str])
    """

    macro_resolv_dic: dict[str, str] = {}
    UNEXP_MACRO_RE = re.compile(r"%{?\w+}?")

    for s in url, src_url:
        for matched_patt in UNEXP_MACRO_RE.findall(s, re.MULTILINE):
            bare_macro = matched_patt.lstrip("%").strip("{}")
            macro_line = re.search(
                rf"^%(define|global)\s+{bare_macro}\s+.*", stags.Spec(), flags=re.MULTILINE
            )
            try:
                macro_def = macro_line.group(0).split(" ")[1:]
                macro_resolv_dic[rf"%{{?{macro_def[0]}}}?"] = "".join(macro_def[1:])
            except AttributeError:
                # An unresolved macro is not an error, we trust rpm build to
                # resolve macros not explicitly defined in the specfile
                continue
    return macro_resolv_dic


class Puck:
    """
    The main class that simply handles user inputs and arguments and directs control to the
    appropriate action class
    """

    rpm_macros: dict[str, str] = {}

    def __init__(self, args):
        self.args = parse_args(args)
        if not self.args.name:
            print(f"{self.args.help}")
            sys.exit(1)
        # log.basicConfig(
        #     format="[%(levelname)s] %(message)s",
        #     level=((log.INFO // self.args.verbose) if self.args.verbose > 0 else log.WARN),
        # )
        self.cwd = Path.cwd()

    def cmp_version(self):
        out = FormOut()
        errs = Errors()
        try:
            f = PrjPkgList.fromfile(self.args.name)
        except Exception as _:
            f = PrjPkgList([self.args.name])

        for prj, pkg in f.List():
            idstr = prj + "/" + pkg
            try:
                stags = SpecTags(prj, pkg)
            except RuntimeError as e:
                errs.Append(f"{prj}/{pkg}: {e}")
                continue
            except CalledProcessError:
                errs.Append(f"{prj}/{pkg}: rpmspec error while parsing specfile.")
                continue
            except Exception:
                errs.Append(
                    "{:s}/{:s}: Failed to sparse spec file, invalid OBS package?".format(prj, pkg)
                )
                continue

            url = stags.Url()
            src_url = stags.SourceUrl()
            self.rpm_macros = resolve_unexp_macros(url, src_url, stags)

            try:
                G = GithubVersion(url, src_url, self.rpm_macros)
            except Exception as e:
                errs.Append(f"{prj}/{pkg}: {e}")
                continue
            try:
                uver = G.get_version()
            except RuntimeError as e:
                errs.Append(f"{prj}/{pkg}: {e}")
                continue
            except HTTPError as h:
                errs.Append(f"{prj}/{pkg}: {h}")
                continue

            statusmap = {
                "specVer": parse(stags.Version()),
                "upsVer": uver,
                "reqs": None,
                "update": False,
            }

            if statusmap["upsVer"] > statusmap["specVer"]:
                rq = chkrq(prj, pkg)
                statusmap["reqs"] = rq
                statusmap["update"] = True

            out.print(idstr, statusmap)
            time.sleep(0.2)  # Avoid getting IP blocked by ddos guards

        errs.Print()


def run_puck():
    p = Puck(sys.argv[1:])
    p.cmp_version()


if __name__ == "__main__":
    pass

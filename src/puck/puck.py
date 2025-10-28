# vim: set ai et ts=4 sw=4 tw=100:
# SPDX-FileCopyrightText: 2025-present Atri Bhattacharya <atrib@duck.com>
#
# SPDX-License-Identifier: MIT
#
"""puck main module"""

import sys

import argparse
import os
import osc.conf
import time
from pathlib import Path
from textwrap import wrap
from urllib.error import HTTPError
from packaging.version import parse, InvalidVersion
from xdg.BaseDirectory import xdg_cache_home
from puck.__about__ import __version__
from puck.pkglistparse import PrjPkgList
from puck.output import FormOut
from puck.errors import Errors
from puck.specparse import CalledProcessError, SpecTags
from puck.chkrq import chkrq
from puck.scrapers.github import GithubVersion
from puck.scrapers.gitlab import GitlabVersion
from puck.scrapers.hepforge import HepForgeVersion
from puck.scrapers.pypi import PyPIVersion
from puck.scrapers.sf import SFVersion


# from logging import log



CACHE_DIR = Path(xdg_cache_home).joinpath("puck")


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
        metavar="FILENAME or OBS-PACKAGE",
        type=str,
        help="input file name or obs package id",
    )

    parser.add_argument(
        "-V",
        "--version",
        help="print %(prog)s version and exit",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    ALLOWED_UPSTREAMS = ["github", "pypi", "gitlab", "hepforge", "sourceforge", "sf"]
    parser.add_argument(
        "-u",
        "--upstream",
        choices=ALLOWED_UPSTREAMS,
        metavar="UPSTREAM",
        type=str,
        help=f"URL for version look-up ({', '.join(ALLOWED_UPSTREAMS)})",
        default=ALLOWED_UPSTREAMS[0],
    )

    parser.add_argument(
        "--url",
        metavar="UPSTREAM_URL",
        help="URL to upstream project",
        type=str,
        default=""
    )

    parser.add_argument(
        "--srcurl",
        metavar="SOURCE_URL",
        help="URL to upstream source tarball",
        type=str,
        default=""
    )

    return parser.parse_args(args)


class Puck:
    """
    The main class that simply handles user inputs and arguments and directs control to the
    appropriate action class
    """

    ups_locator: str = ""

    def __init__(self, args):
        # initialize osc configuration
        osc.conf.get_config()

        self.args = parse_args(args)
        if not self.args.name:
            print(f"{self.args.help}")
            sys.exit(1)
        # log.basicConfig(
        #     format="[%(levelname)s] %(message)s",
        #     level=((log.INFO // self.args.verbose) if self.args.verbose > 0 else log.WARN),
        # )
        self.cwd = Path.cwd()
        self.ups_locator = self.args.upstream
        self.setup_cache_dir()

    def setup_cache_dir(self, dir=CACHE_DIR):
        """Set up cache dir

        :dir: Optional patch to cache dir
        :returns: None

        """
        try:
            os.makedirs(CACHE_DIR)
        except FileExistsError as _:
            pass
        except Exception as e:
            raise e
            sys.exit(1)

    def cmp_version(self) -> None:
        out = FormOut()
        errs = Errors()
        try:
            f = PrjPkgList.fromfile(self.args.name)
        except FileNotFoundError:
            f = PrjPkgList([self.args.name])

        for prj, pkg, m_url in f.List():
            if m_url != "-":
                self.args.url = m_url
            idstr = prj + "/" + pkg
            pkg_cache_dir: Path = CACHE_DIR / f"{prj!s}" / f"{pkg!s}"
            try:
                os.makedirs(pkg_cache_dir)
            except FileExistsError:
                pass
            except Exception:
                sys.exit(1)

            try:
                stags = SpecTags(prj, pkg, pkg_cache_dir)
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

            url = self.args.url or stags.Url()
            src_url = self.args.srcurl or stags.SourceUrl()

            try:
                G : GithubVersion | GitlabVersion | HepForgeVersion | PyPIVersion | SFVersion
                if self.args.upstream == "github":
                    G = GithubVersion(pkg_cache_dir, url, src_url)
                elif self.args.upstream == "gitlab":
                    G = GitlabVersion(pkg_cache_dir, url, src_url)
                elif self.args.upstream == "hepforge":
                    G = HepForgeVersion(pkg_cache_dir, url, src_url)
                elif self.args.upstream == "pypi":
                    G = PyPIVersion(pkg_cache_dir, src_url, pkg, self.args.url)
                elif self.args.upstream in ["sourceforge", "sf"]:
                    G = SFVersion(pkg_cache_dir, url, src_url)
            except Exception as e:
                errs.Append(f"{prj}/{pkg}: {e}")
                continue
            try:
                uver = G.get_version()
            except (HTTPError, InvalidVersion, RuntimeError) as e:
                errs.Append(f"{prj}/{pkg}: {e}")
                continue

            statusmap = {
                "specVer": parse(stags.Version()),
                "upsVer": uver,
                "reqs": None,
                "update": False,
            }

            if statusmap["upsVer"] > statusmap["specVer"]:
                req = chkrq(prj, pkg)
                statusmap["reqs"] = req
                statusmap["update"] = True

            out.print(idstr, statusmap)

            time.sleep(0.2)  # Avoid getting IP blocked by ddos guards

        errs.Print()


def run_puck():
    p = Puck(sys.argv[1:])
    p.cmp_version()


if __name__ == "__main__":
    pass

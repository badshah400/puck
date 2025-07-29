# vim: set ai et ts=4 sw=4:
# SPDX-FileCopyrightText: 2025-present Atri Bhattacharya <atrib@duck.com>
#
# SPDX-License-Identifier: MIT
#
"""puck main module"""

import sys
import argparse
import logging as log
from pathlib import Path
from textwrap import wrap
from puck.__about__ import __version__


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

    def cmp_version(self):
        pass

if __name__ == '__main__':
    p = Puck(sys.argv)
    p.cmp_version()

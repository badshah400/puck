#!/usr/bin/python3
# vim: set ai et ts=4 sw=4 tw=100 fileencoding=utf-8:

import colorama as col


class FormOut:
    def __init__(self):
        col.init(autoreset=True)
        self.upav_norq = col.Fore.RED + col.Style.BRIGHT
        self.upav_wirq = col.Fore.GREEN
        self.formstr = "{:55s} {:15s} {:15s} {:15s}"
        self.style = ""

    def print(self, key, propmap):
        self.style = ""  # reset for each print
        outmsg = b""
        if propmap["update"] and not propmap["upsVer"].is_prerelease:
            rq = propmap["reqs"]
            rqmsg = f" {rq[0]} [{rq[1][:35]}]".format(rq[0], rq[1][:35]) if rq else ""
            self.style = self.upav_wirq if rqmsg else self.upav_norq
            outmsg = f"↑{rqmsg}".encode("utf-8")
        print(
            self.style
            + self.formstr.format(
                key, propmap["specVer"].public, propmap["upsVer"].public, outmsg.decode("utf-8")
            )
        )

    def printAll(self, stmap):
        for k in stmap.keys():
            self.print(k, stmap[k])

#!/usr/bin/python
# vim: set ai et ts=4 sw=4 tw=100:

import sys


class Errors:
    errs: list[str] = []
    errhead = "Collected error messages"

    def Append(self, msg):
        self.errs.append(msg)

    def Print(self):
        if self.errs:
            nerrs = len(self.errs)
            if nerrs == 1:
                print("\nThere was an error\n  * {:s}".format(self.errs[0]), file=sys.stderr)
            else:
                print("\nThere were %d errors" % len(self.errs), file=sys.stderr)
                print(self.errhead, file=sys.stderr)
                for err in self.errs:
                    print("  * {:s}".format(err), file=sys.stderr)

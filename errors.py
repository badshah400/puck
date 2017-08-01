#!/usr/bin/python
# vim: set ai et ts=4 sw=4 tw=80:

class Errors:
    errs   = []
    errhead = 'Collected error messages'
    
    def Append(self, msg):
        self.errs.append(msg)

    def Print(self):
        if self.errs:
            nerrs = len(self.errs)
            if nerrs == 1:
                print("\nThere was an error.")
                for err in self.errs:
                    print(err)
            else:
                print("\nThere were %d errors." % len(self.errs))
                print(self.errhead)
                for err in self.errs:
                    print(err)

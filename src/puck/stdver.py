# vim: set ai et ts=4 sw=4 tw=80 fileencoding=utf-8:
import re

nametag  = re.compile(r'^[a-zA-Z_.-]+')       # match leading app name out of
                                              # full tarball name
vsep     = re.compile(r'([0-9])[\_-]([0-9])') # match weird version connectors
                                              # (e.g. to convert "0_147" ->
                                              # "0.147")

def stdver(v):
    ver = nametag.sub('', v)
    return vsep.sub(r'\1.\2', ver)

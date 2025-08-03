# vim: set ai et ts=4 sw=4 tw=100 fileencoding=utf-8:
import re

connectors = r'[._-]'
vsep       = re.compile(r'([0-9])[\_-]([0-9])') # match weird version connectors
                                                # (e.g. to convert "0_147" -> "0.147")

def stdver(v, appname):
    strip_appname_regex = rf'{appname}{connectors}'
    ver = re.sub(strip_appname_regex, '', v)
    return vsep.sub(r'\1.\2', ver)

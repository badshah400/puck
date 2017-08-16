#!/usr/bin/python2
# vim: set ai et ts=4 sw=4 tw=80 fileencoding=utf-8:

import osc.conf
import sys
import re
from specparse import SpecTags

# initialize osc configuration
osc.conf.get_config()
apiurl = osc.conf.config['apiurl']

if len(sys.argv) < 3:
    print('Usage: pkgscan.py <prj> <pkg1> <pkg2>...')
    print('One project and at least one pkg expected at input.')
    sys.exit(-1)
    
prj  = sys.argv[1]
pkgs = sys.argv[2:]

sf_re = re.compile('sourceforge\.net|sf\.net')

for pkg in pkgs:
    try:
        stags   = SpecTags(prj, pkg)
        src_url = stags.SourceUrl()
    except:
        continue

    if sf_re.search(src_url):
        print('{:s}/{:s}'.format(prj, pkg))
#    else:
#        print('{:s}/{:s}'.format(prj, pkg))        


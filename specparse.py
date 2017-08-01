#!/usr/bin/python3
# vim: set ai et ts=4 sw=4 tw=80:

from os import path
from subprocess import call, check_output, PIPE
from tempfile import NamedTemporaryFile
import re
import osc.conf
import osc.core

class SpecTags:
    
    re_src0 = re.compile('Source0?:.*')
    re_ver  = re.compile('Version:.*')
    re_url  = re.compile('U[rR][lL]:.*')
    apiurl  = osc.conf.config['apiurl']

    def __init__(self, prj, pkg):
        self.Name    = ''
        self.Ver     = ''
        self.URL     = ''
        self.srcURL  = ''

        u   = osc.core.makeurl(self.apiurl, ['source', prj, pkg, pkg + '.spec'],
                               query = { 'expand': 1 })

        fi = osc.core.http_GET(u)
        try:
            spec = ''.join(fi.readlines())
        except:
            print("Error fetching spec file.")
        
        cachedir = path.join('.', '.osc')
        if not path.exists(cachedir):
            os.mkdir(cachedir)
        
        with NamedTemporaryFile(mode='w', suffix='.spec', dir=cachedir) as f:
            f.write(spec)
            f.flush()
            
#            print(f.name)
            src0 = check_output(['rpmdev-spectool', '-S', f.name])
#            print(src0)
        
        if src0:
            self.srcURL = self.re_src0.search(src0).group().split(' ')[-1]
        else:
            self.srcURL = self.re_src0.search(spec).group().split(' ')[-1]
#        print(srcURL)
        
        self.Ver = self.re_ver.search(spec).group().split(' ')[-1]
        self.URL = self.re_url.search(spec).group().split()[-1]
#        print(specver)

    def Name(self):
        return self.Name

    def Version(self):
        return self.Ver

    def Url(self):
        return self.URL

    def SourceUrl(self):
        return self.srcURL


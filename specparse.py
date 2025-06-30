#!/usr/bin/python3
# vim: set ai et ts=4 sw=4 tw=100:

import sys
from lxml import etree
from os import path, mkdir
from subprocess import run, CalledProcessError
from tempfile import NamedTemporaryFile
import re
import osc.conf
import osc.core

# List of uncommon macros that need additional macro defintion files for rpmspec to expand. Instead,
# as they are anyway unnecessary for our purposes, we just set them to %nil by passing
# `--define='useless_macro %nil'` for each macro.
UNDEFINED_MACROS = ['openmpi_requires', 'sysusers_requires']

class SpecTags:
    re_src0 = re.compile('Source0?:.*')
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
            spec = b''.join(fi.readlines()).decode('utf-8')
        except:
            print(f"{prj}/{pkg}: Error fetching spec file.")
            sys.exit(-1)

        cachedir = path.join('.', '.osc')
        if not path.exists(cachedir):
            mkdir(cachedir)

        with NamedTemporaryFile(mode='w', suffix='.spec', dir=cachedir) as f:
            f.write(spec)
            f.flush()

            rpmspec_cmdline = '/usr/bin/rpmspec --srpm -q --qf "%{url} %{version}" '
            rpmspec_cmdline += ' '.join([f'--define="{macro} %nil"' for macro in UNDEFINED_MACROS])
            rpmspec_cmdline += f' {f.name}'
            try:
                proc = run(rpmspec_cmdline, shell=True, capture_output=True, text=True, check=True)
                self.URL, self.Ver = proc.stdout.split()
            except CalledProcessError as e:
                print(f'{prj}/{pkg}: {e.stderr}')
                sys.exit(-1)

            try:
                spec_parse  = run(['/usr/bin/rpmspec', '-P', f.name],
                                  capture_output=True, text=True, check=True)
                spec_exp    = spec_parse.stdout
                self.srcURL = self.re_src0.search(spec_exp).group().split(' ')[-1]
            except CalledProcessError as e:
                self.srcURL = self.re_src0.search(spec).group().split(' ')[-1]

        try:
            # If srcURL is really a URL, then it will have at least 3 parts (http://...)
            _ = self.srcURL.split('/')[2]
        except IndexError:
            # Get srcURL from _service file
            service_file = osc.core.http_GET(u.replace(f"{pkg}.spec", "_service"))
            service_xml  = b''.join(service_file.readlines())
            service_root = etree.fromstring(service_xml.decode('utf-8'))
            for f in service_root.findall(".//param[@name]"):
                if f.attrib["name"] == "url":
                    self.srcURL = f.text

    def Name(self):
        return self.Name

    def Version(self):
        return self.Ver

    def Url(self):
        return self.URL

    def SourceUrl(self):
        return self.srcURL


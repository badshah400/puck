#!/usr/bin/env python3
# vim: set ai et ts=4 sw=4 tw=100:

from os import path, mkdir
from subprocess import run, CalledProcessError
from tempfile import NamedTemporaryFile
import re
from urllib.error import HTTPError
from lxml import etree
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
        self.name    = ''
        self.ver     = ''
        self.url     = ''
        self.src_url = ''

        # Check if package is multi-build and error out early if so
        multi = osc.core.makeurl(self.apiurl, ['source', prj, pkg, '_multibuild'],
                                 query={'expand': 1})
        try:
            osc.core.http_GET(multi)
            raise RuntimeError('Cannot handle multibuild package; bailing out.')
        except HTTPError as e:
            if (404 == e.getcode()):
                # This means no _multibuild file found, so we are good to proceed
                pass
            else:
                # Re-raise if something else has gone wrong
                raise e

        u = osc.core.makeurl(self.apiurl, ['source', prj, pkg, pkg + '.spec'],
                             query={'expand': 1})

        try:
            fi = osc.core.http_GET(u)
            spec = b''.join(fi.readlines()).decode('utf-8')
        except HTTPError:
            raise RuntimeError("Error fetching spec file.")
            pass

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
                self.url, self.ver = proc.stdout.split()
            except CalledProcessError as e:
                raise e

            try:
                spec_parse  = run(['/usr/bin/rpmspec', '-P', f.name],
                                  capture_output=True, text=True, check=True)
                spec_exp    = spec_parse.stdout
                self.src_url = self.re_src0.search(spec_exp).group().split(' ')[-1]
            except CalledProcessError:
                self.src_url = self.re_src0.search(spec).group().split(' ')[-1]

        try:
            # If srcURL is really a URL, then it will have at least 3 parts (http://...)
            _ = self.src_url.split('/')[2]
        except IndexError:
            # Get srcURL from _service file
            service_file = osc.core.http_GET(u.replace(f"{pkg}.spec", "_service"))
            service_xml  = b''.join(service_file.readlines())
            service_root = etree.fromstring(service_xml.decode('utf-8'))
            for f in service_root.findall(".//param[@name]"):
                if f.attrib["name"] == "url":
                    self.src_url = f.text

    def Name(self):
        return self.name

    def Version(self):
        return self.ver

    def Url(self):
        return self.url

    def SourceUrl(self):
        return self.src_url


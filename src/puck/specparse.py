#!/usr/bin/env python3
# vim: set ai et ts=4 sw=4 tw=100:
# mypy: disable-error-code=import-untyped

import json
from contextlib import suppress
from pathlib import Path
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
UNDEFINED_MACROS = ['glib2_gsettings_schema_requires',
                    'openmpi_requires',
                    'sysusers_requires']


class SpecTags:
    # Useful pre-compiled regexes
    RE_SRC0 = re.compile('^Source0?:.*', flags=re.MULTILINE)
    RE_URL  = re.compile('^(URL|Url):.*', flags=re.MULTILINE)
    RE_VER  = re.compile('^Version:.*', flags=re.MULTILINE)

    API_URL = osc.conf.config['apiurl']
    obs_metadata: dict = {}

    def __init__(self, prj: str, pkg: str, cache_dir: Path):
        self.name    = ''
        self.ver     = ''
        self.url     = ''
        self.src_url = ''
        self.spec    = ''

        is_multi_flavoured = False

        try:
            obs_rev = osc.core.get_source_rev(self.API_URL, prj, pkg)
        except HTTPError:
            raise RuntimeError("Error fetching spec file.")

        obs_mdata_cache: dict = {}
        obs_mdata_file: Path = Path(cache_dir) / 'obs.json'

        try:
            with open(obs_mdata_file, mode="r") as f:
                with suppress(json.JSONDecodeError):
                    obs_mdata_cache = json.load(f)
        except FileNotFoundError:
            pass
        except Exception as e:
            raise e

        if obs_mdata_cache.get("revision", "-1") == obs_rev["rev"]:
            self.url = obs_mdata_cache["url"]
            self.src_url = obs_mdata_cache["source_url"]
            self.ver = obs_mdata_cache["version"]
        else:
            multi = osc.core.makeurl(self.API_URL, ['source', prj, pkg, '_multibuild'],
                                     query={'expand': 1})
            # If package is multi-build, we need to avoid rpmspec
            try:
                osc.core.http_GET(multi)
                is_multi_flavoured = True  # rpmspec won't work, so we have to grep manually
            except HTTPError as e:
                if (404 == e.getcode()):
                    # This means no _multibuild file found, so we are good to proceed with rpmspec
                    pass
                else:
                    # Re-raise if something else has gone wrong
                    raise e

            obs_spec_url = osc.core.makeurl(self.API_URL, ['source', prj, pkg, pkg + '.spec'],
                                            query={'expand': 1})
            try:
                fi = osc.core.http_GET(obs_spec_url, headers={'Keep-Alive': 'timeout=5'})
                self.spec = b''.join(fi.readlines()).decode('utf-8')
            except HTTPError:
                raise RuntimeError("Error fetching spec file.")

            if is_multi_flavoured:
                self._grep_spec_for_tags()
            else:
                with NamedTemporaryFile(mode='w', suffix='.spec', dir=cache_dir) as pkg_spec:
                    pkg_spec.write(self.spec)
                    pkg_spec.flush()

                    RPMSPEC_BIN     = run(['which', 'rpmspec'], capture_output=True, text=True)
                    rpmspec_cmdline = f'{RPMSPEC_BIN.stdout.strip()} --srpm -q --qf "%{{url}} %{{version}}" '
                    rpmspec_cmdline += ' '.join([f'--define="{macro} %nil"' for macro in UNDEFINED_MACROS])
                    rpmspec_cmdline += f' {pkg_spec.name}'
                    try:
                        proc = run(rpmspec_cmdline, shell=True, capture_output=True, text=True, check=True)
                        self.url, self.ver = proc.stdout.split()
                        spec_parse  = run(['/usr/bin/rpmspec', '-P', pkg_spec.name],
                                          capture_output=True, text=True, check=True)
                        spec_exp    = spec_parse.stdout
                        self.src_url = (self.RE_SRC0.search(spec_exp) or re.Match()).group().split()[-1]
                    except CalledProcessError:
                        # At this stage, it is clear that rpmspec is not working for this specfile
                        self._grep_spec_for_tags()

                try:
                    # If srcURL is really a URL, then it will have at least 3 parts (http://...)
                    self.src_url.split('/')[2]
                except IndexError:
                    try:
                        # Get srcURL from _service file
                        service_file = osc.core.http_GET(obs_spec_url.replace(f"{pkg}.spec", "_service"))
                        service_xml  = b''.join(service_file.readlines())
                        service_root = etree.fromstring(service_xml.decode('utf-8'))
                        for pkg_spec in service_root.findall(".//param[@name]"):
                            if pkg_spec.attrib["name"] == "url":
                                self.src_url = pkg_spec.text
                    except Exception as e:
                        raise e

            self._resolve_unexp_macros()
            self.obs_metadata = {"project": prj,
                                 "package": pkg,
                                 "is_multibuild": "True" if is_multi_flavoured else "False",
                                 "url" : self.url,
                                 "source_url" : self.src_url,
                                 "version" : self.ver,
                                 "revision": obs_rev.get('rev', ''),
                                }

            with open(obs_mdata_file, mode="w") as mfile:
                json.dump(self.obs_metadata, mfile)


    def _grep_spec_for_tags(self):
        """Function to set class data by grep-ing for rpm tags when rpmspec fails"""

        self.url = (self.RE_URL.search(self.spec) or re.Match()).group().split()[-1]
        self.ver = (self.RE_VER.search(self.spec) or re.Match()).group().split()[-1]
        self.src_url = (self.RE_SRC0.search(self.spec) or re.Match()).group().split()[-1]

    def Name(self):
        return self.name

    def Version(self):
        return self.ver

    def Url(self):
        return self.url

    def SourceUrl(self):
        return self.src_url

    def Spec(self):
        return self.spec

    def _resolve_unexp_macros(self) -> dict[str, str]:
        """
        Returns a dictionary of in-file macros with their values as keys

        :returns: Dictionary with macro regex as key and macro value as its value (dict[str,str])
        """

        macro_resolv_dic: dict[str, str] = {r"%{?name}?": self.name}
        UNEXP_MACRO_RE = re.compile(r"%{?\w+}?")

        for s in self.url, self.src_url:
            for matched_patt in UNEXP_MACRO_RE.findall(s, re.MULTILINE):
                bare_macro = matched_patt.lstrip("%").strip("{}")
                # Note: This line-by-line search for macro definition works because
                # typically macro defintions relevant to URL or Source URL tags are
                # short and defined in a single line. If the macro definition
                # stretches across multiple lines, this will fail.
                macro_line = re.search(
                    rf"^%(define|global)\s+{bare_macro}\s+.*", self.spec, flags=re.MULTILINE
                )
                if macro_line:
                    macro_def = macro_line.group(0).split(" ")[1:]
                    macro_resolv_dic[rf"%{{?{macro_def[0]}}}?"] = "".join(macro_def[1:])

        for mcro, val in macro_resolv_dic.items():
            self.url = re.sub(mcro, val, self.url)
            self.src_url = re.sub(mcro, val, self.src_url)

        return macro_resolv_dic

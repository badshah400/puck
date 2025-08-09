#!/usr/bin/python3
# vim: set ai et ts=4 sw=4 tw=100 fileencoding=utf-8:

import sys
import os
from pathlib import Path
import urllib.request
import re
from lxml import etree  # import ElementTree as ET
import osc.conf
from specparse import SpecTags
from packaging.version import Version, parse, InvalidVersion
from errors import Errors
from chkrq import chkrq
from pkglistparse import PrjPkgList
from output import FormOut

# initialize osc configuration
osc.conf.get_config()
apiurl = osc.conf.config["apiurl"]

errs = Errors()


def hepVer(prj, pkgext=None):
    exts = [".bz2", ".gz", ".tar", ".tgz", ".xz", ".7z", ".zip", ".rar"]
    response = urllib.request.urlopen("https://www.hepforge.org/downloads/" + prj).read()
    html = response.decode("utf-8")
    strongs = etree.HTML(html).findall('.//*[@class="name"]/a')[0].text
    # print(strongs)
    try:
        if not strongs:
            raise Exception("Not listed on hepforge downloads page")
    except:
        return "-"

    nametag = re.compile("^[a-zA-Z_.-]+")
    ver = nametag.sub("", strongs)
    while Path(ver).suffix in exts:
        ver = ver.rsplit(".", 1)[0]
        # print(ver)

    return Version(ver.strip())


if __name__ == "__main__":
    if len(sys.argv) == 1:
        f = PrjPkgList.fromfile("hfpkg.txt")
    else:
        pkgs = []
        for a in sys.argv[1:]:
            pkgs.append(a)
        f = PrjPkgList(pkgs)

    out = FormOut()
    for prj, pkg in f.List():
        # Whole other URL for Pythia
        if pkg == "pythia":
            continue
        sp = SpecTags(prj, pkg)
        url = sp.Url()
        srcURL = sp.SourceUrl()
        #        print(url)
        #        print(srcURL)
        if re.search(r"hepforge\.org", url):
            re_http = re.compile("^https?://")
            hepprj = re_http.sub("", url).split(".")[0]

            # Handle URL's in the form: http://projects.hepforge.org/pyfeyn/
            if hepprj == "projects":
                hepprj = re_http.sub("", url).rstrip("/").split("/")[-1]

        elif re.search(r"hepforge\.org", srcURL):
            hepprj = srcURL.split("/")[4]
        else:
            errs.Append(r"{:s}/{:s}: Source does not point to hepforge URL".format(prj, pkg))
            continue

        specVer = Version(sp.Version())
        #        print(specver)

        try:
            hepver = hepVer(hepprj)
        except InvalidVersion:
            errs.Append("Could not parse version for {:s}/{:s}".format(prj, pkg))
            continue

        statusmap = {"specVer": specVer, "upsVer": hepver, "reqs": None, "update": False}

        try:
            if hepver > specVer:
                rq = chkrq(prj, pkg)
                statusmap["reqs"] = rq
                statusmap["update"] = True
        except:
            newer = b""
            errs.Append(r"{:s}/{:s}: Invalid version from hepforge".format(prj, pkg))

        out.print("{}/{}".format(prj, pkg), statusmap)

### PYTHIA CHECK ###
pythia_url = "https://pythia.org/history/"
response = urllib.request.urlopen(pythia_url)
html = response.read().decode("utf-8")
htmldivs = etree.HTML(html).findall('.//div[@class="main"]')
li_all = htmldivs[0].findall('.//p[@id="collapsible"]')
li0_text = li_all[0].text

pythia_ver, rel_date = li0_text.split(":")
rel_date = rel_date.strip()
prj = "science"
pkg = "pythia"
sp = SpecTags(prj, pkg)
specVer = Version(sp.Version())
pythiaVer = parse(pythia_ver)
statusmap = {"specVer": specVer, "upsVer": pythiaVer, "reqs": None, "update": False}

try:
    if hepver > specVer:
        rq = chkrq(prj, pkg)
        statusmap["reqs"] = rq
        statusmap["update"] = True
except:
    errs.Append(r"{:s}/{:s}: Invalid version from Pythia webpage".format(prj, pkg))

out = FormOut()
out.print("{}/{}".format(prj, pkg), statusmap)

errs.Print()

#!/usr/bin/python3
# vim: set ai et ts=4 sw=4 tw=100 fileencoding=utf-8:
# mypy: disable-error-code=import-untyped

import sys
import re
from packaging.version import parse, InvalidVersion
import osc.conf
import requests
from subprocess import CalledProcessError
import time

# Local modules
from specparse import SpecTags
from errors import Errors
from stdver import stdver
from chkrq import chkrq
from output import FormOut

# initialize osc configuration
osc.conf.get_config()
apiurl = osc.conf.config["apiurl"]

# Match any non-digits that come before a version string
NON_VERSION_PREFIX = re.compile(r"^[^0-9]*")

errs = Errors()


def glLastVer(gl_inst, gl_prj, gl_repo):
    """Get latest tag from Gitlab instance"""
    rest_url = f"https://{gl_inst}/api/v4/projects/{gl_prj}%2F{gl_repo}/repository/tags"
    headers = {"User-Agent": "Linux"}
    gl_data = requests.get(rest_url, headers=headers, timeout=30)

    if gl_data.status_code == requests.codes["ok"]:
        gl_json = gl_data.json()
    else:
        gl_data.raise_for_status()

    tag_name = gl_json[0]["name"]
    tag_ver = NON_VERSION_PREFIX.sub("", tag_name)
    ver = tag_ver.replace("_", ".").replace("-", ".")
    return stdver(ver)


if __name__ == "__main__":
    f = []
    out = FormOut()
    if len(sys.argv) == 1:
        with open("glpkg.txt", encoding="utf-8") as F:
            lines = F.readlines()
        for line in lines:
            prjpkg, glurl = line.split()
            prj, pkg = prjpkg.split("/")
            f.append([prj, pkg, glurl])
    else:
        prjpkg = sys.argv[1]
        prj, pkg = prjpkg.split("/")
        glurl = "-"
        f.append([prj, pkg, glurl])

    for obs_prj, obs_pkg, glurl in f:
        idstr = obs_prj + "/" + obs_pkg
        try:
            stags = SpecTags(obs_prj, obs_pkg)
        except RuntimeError as e:
            errs.Append(f"{obs_prj}/{obs_pkg}: {e}")
            continue
        except CalledProcessError as e:
            errs.Append(f"{obs_prj}/{obs_pkg}: rpmspec error while parsing specfile.")
            continue
        except:
            errs.Append(
                "{:s}/{:s}: Failed to sparse spec file, invalid OBS package?".format(
                    obs_prj, obs_pkg
                )
            )
            continue
        url = stags.Url()
        src_url = stags.SourceUrl()
        src_url = re.sub("%{?url}?", url, src_url)  # Replace %{url} in source URL with url
        src_url = re.sub(r"%{?name}?", obs_pkg, src_url)  # Handle %name in source URL

        if src_url.split("/")[0] != "https:":
            # This means the src_url is just the file name, e.g. when using a
            # _service file
            src_url = url + f"/-/archive/{stags.Version()}/{src_url}"

        specgl = glurl if glurl != "-" else src_url
        specgl = specgl.rstrip("/")  # Drop trailing '/'
        # Drop everything in src_url after '/-'
        specgl = re.sub(r"/-.*$", "", specgl)
        specgl_parts = specgl.split("/")[2:]
        if len(specgl_parts) == 3:
            git_host, git_prj, git_repo = specgl_parts
        else:
            git_host = specgl_parts[0]
            git_prj = specgl_parts[1]
            git_repo = f"{specgl_parts[2]}%2F{specgl_parts[3]}"

        rehttps = re.compile("^https?://")
        if not rehttps.match(specgl):
            errs.Append(f"{specgl}: Invalid Gitlab URL")
            continue

        try:
            uver = glLastVer(git_host, git_prj, git_repo)
            parse(uver)
        except InvalidVersion as _:
            errs.Append(f"{obs_prj}/{obs_pkg}: Invalid package version {uver}")
            continue
        except requests.HTTPError as ex_http:
            errs.Append(f"{obs_prj}/{obs_pkg}: " + str(ex_http))
            continue

        statusmap = {
            "specVer": parse(stags.Version()),
            "upsVer": parse(uver),
            "reqs": None,
            "update": False,
        }

        if statusmap["upsVer"] > statusmap["specVer"]:
            rq = chkrq(obs_prj, obs_pkg)
            statusmap["reqs"] = rq
            statusmap["update"] = True

        out.print(idstr, statusmap)
        time.sleep(1.0)

    # out.printAll(statusmap)

errs.Print()

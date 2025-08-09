#!/usr/bin/python3
# vim: set ai et ts=4 sw=4 tw=100 fileencoding=utf-8:

import osc.conf
import osc.core
from lxml import etree


def chkrq(prj, pkg):
    apiurl = osc.conf.config["apiurl"]
    u = osc.core.makeurl(
        apiurl,
        ["request"],
        query={
            "view": "collection",
            "project": prj,
            "package": pkg,
            "limit": 1,
            "states": "new,review",
        },
    )
    fi = osc.core.http_GET(u)

    collxml = etree.fromstring(b"".join(fi.readlines()))
    # Join all lines into a byte-string
    # and read into etree object
    nreq = int(collxml.get("matches"))  # Get no. of new/review requests

    if nreq:  # nreq = 0 => no requests
        target = collxml[0].find(".//target")  # To check if target matches
        tgtprj = target.get("project")
        tgtpkg = target.get("package")
        if (tgtprj == prj) and (tgtpkg == pkg):
            descr = collxml[0].find("description")
            # Get text in <description> node...
            descr = descr.text.splitlines()[0] if descr.text is not None else ""
            # ... keeping only first line
            rqid = collxml[0].get("id")  # Get the request id
            return ("sr#{:s}".format(rqid), descr)
        else:
            return None
    else:
        return None


if __name__ == "__main__":
    pass

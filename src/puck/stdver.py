# vim: set ai et ts=4 sw=4 tw=100 fileencoding=utf-8:
import re

connectors = r"[._-]"
non_ver_re = re.compile(r"^[^\d]+")  # match leading non-version identifiers,
# e.g. 'Version_' in 'Version_2.14.0'
vsep = re.compile(r"([0-9])[\_-]([0-9])")  # match weird version connectors
# (e.g. to convert "0_147" -> "0.147")


def stdver(tag_id: str, appname: str) -> str:
    strip_appname_regex = rf"{appname}{connectors}"
    ver = re.sub(strip_appname_regex, "", tag_id)
    # strip other leading non-version words
    ver = non_ver_re.sub("", ver)

    return vsep.sub(r"\1.\2", ver)

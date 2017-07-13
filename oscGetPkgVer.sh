#!/bin/bash
# vim: set ai et ts=2 sw=2:

tempdir=`mktemp -d .oscpkg.XXXXX`

cleanuptmp()
{
  rm -fr ${tempdir}
}

prj=$1
pkg=$2
osc cat ${prj} ${pkg} ${pkg}.spec 2>&1 > ${tempdir}/${pkg}.spec
[ $? -eq 0 ] || \
  { echo "Error in fetching spec file (invalid project/package?)" >> /dev/stderr; cleanuptmp;  exit 1 ; }
srcURL=`cat ${tempdir}/${pkg}.spec | grep -E "Source0?:" \
        | awk '{print $2}'`
specVer=`grep -E "^Version:" ${tempdir}/${pkg}.spec | awk '{print $2}'`

ghInit=`echo $srcURL | awk 'BEGIN {FS="/";} {print $3;}'`
[ $ghInit = "github.com" ] || \
  { echo "Error: Source does not point to github URL" >> /dev/stderr; cleanuptmp; exit 2; }
ghuser=`echo $srcURL | awk 'BEGIN {FS="/";} {print $4;}'`
ghrepo=`echo $srcURL | awk 'BEGIN {FS="/";} {print $5;}'`
[ $ghrepo = "%{name}" ] && ghrepo=`echo $ghrepo | sed "s/%{name}/$pkg/"`

cleanuptmp
echo $ghuser $ghrepo $specVer

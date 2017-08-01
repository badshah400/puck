#!/usr/bin/python2
# vim: set ai et ts=4 sw=4 tw=80:

def NewUpstreamVer(ver1, ver2):
    arr1 = ver1.split('.')
    arr2 = ver2.split('.')
    len1 = len(arr1)
    len2 = len(arr2)
    res  = False
    try:
        if len1 <= len2:
            for i in range(0, len1):
                if int(arr1[i]) > int(arr2[i]):
                    return True
                elif int(arr1[i]) < int(arr2[i]):
                    return False
                else:
                    continue
        elif len1 > len2:
            for i in range(0, len2):
                if int(arr1[i]) > int(arr2[i]):
                    return True
                elif int(arr1[i]) < int(arr2[i]):
                    return False
                else:
                    continue
            res = True
    except:
        raise
    return(res)


#!/usr/bin/python2
# vim: set ai et ts=4 sw=4 tw=80:

def NewUpstreamVer(ver1, ver2):
    arr1 = ver1.split('.')
    arr2 = ver2.split('.')
    res  = False

    for i in range(min(len(arr1), len(arr2))):
        # PAD WITH HIGHEST ASCII CHARACTER IF SUBSTR LENGTH ARE NOT IDENTICAL
        # E.G. 2.0.1beta1 > 2.0.1 but 2.0.1beta1 < 2.0.1~~~~~
        # FIXME: DO WE WANT TO HANDLE CORNER CASES LIKE 2.1 > 2.1.BETA1?
        lendiff = len(arr1[i]) - len(arr2[i])
        if lendiff > 0:
            arr2[i] += ('~' * abs(lendiff))
        elif lendiff < 0:
            arr1[i] += ('~' * abs(lendiff))
    try:
        return True if arr1 > arr2 else False
    except:
        raise
    return(res)

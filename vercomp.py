#!/usr/bin/python2
# vim: set ai et ts=4 sw=4 tw=80:

def NewUpstreamVer(ver1, ver2):
    ver1 = ver1.replace('-', '.')
    ver2 = ver2.replace('-', '.')
    arr1 = ver1.split('.') #if type(ver1) == "string" else [ver1]
    arr2 = ver2.split('.')
    res  = False

    nums = len(arr1) - len(arr2)
    if nums > 0:
        for i in range(nums):
            arr2.append('0')
    else:
        for i in range(-nums):
            arr1.append('0')

    for i in range(len(arr1)):
        # PAD WITH HIGHEST ASCII CHARACTER IF SUBSTR LENGTH ARE NOT IDENTICAL
        # E.G. 2.0.1beta1 > 2.0.1 but 2.0.1beta1 < 2.0.1~~~~~
        # FIXME: DO WE WANT TO HANDLE CORNER CASES LIKE 2.1 > 2.1.BETA1?
        lendiff = len(arr1[i]) - len(arr2[i])
        if lendiff > 0:
            arr2[i] += ('~' * abs(lendiff))
        elif lendiff < 0:
            arr1[i] += ('~' * abs(lendiff))

        if arr1[i] > arr2[i]:
            return True
        elif arr1[i] < arr2[i]:
            return False

    return(res)

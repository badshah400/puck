#!/usr/bin/python3
# vim: set ai et ts=4 sw=4 tw=100:


class PrjPkgList:
    def __init__(self, pkglist):
        self.prjpkgs = []

        for line in pkglist:
        # IGNORE COMMENTED LINES
            if line[0] == '#':
                continue

            # REPLACE SPACE BY '/' THEN SPLIT BY '/'
            line = line.replace(' ', '/')
            # print(line)
            line_parts = line.split('/')
            if len(line_parts) != 2:
                continue
            # print(l)
            self.prjpkgs.append((line_parts[0], line_parts[1].rstrip('\n')))

    @classmethod
    def fromfile(cls, filename):
        arr = []

        try:
            f = open(filename, 'r', encoding='utf-8')
        except FileNotFoundError as e:
            raise e
        for line in f:
            # IGNORE COMMENTED LINES
            if line[0] == '#':
                continue

            arr.append(line)

        return cls(arr)

    def List(self):
        return self.prjpkgs


#!/usr/bin/python2.4

import apt
import sys
from optparse import OptionParser

class MyCache(apt.Cache):
    def __init__(self):
        apt.Cache.__init__(self)
        self.brokenCount = self._depcache.BrokenCount
    def clear(self):
        for pkg in cache:
            pkg.markKeep()
        assert self._depcache.InstCount == 0 and \
               self._depcache.BrokenCount == 0 \
               and self._depcache.DelCount == 0
        

def is_allowed_origin(pkg, allowed_origins):
    origin = pkg.candidateOrigin
    #print origin
    for allowed in allowed_origins:
        if origin.origin == allowed[0] and origin.archive == allowed[1]:
            return True
    return False

def check_changes_for_sanity(cache, allowed_origins):
    if cache.brokenCount != 0:
        return False
    for pkg in cache:
        if pkg.markedDelete:
            return False
        if pkg.markedInstall or pkg.markedUpgrade:
            if not is_allowed_origin(pkg, allowed_origins):
                return False
    return True

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-d", "--debug",
                      action="store_true", dest="debug", default=False,
                      help="print debug messages")

    (options, args) = parser.parse_args()
    debug = options.debug

    # get a cache
    cache = MyCache()
    pkgs_to_upgrade = []
    allowed_origins = [("Ubuntu","breezy-security")]
    
    for pkg in cache:
        if pkg.isUpgradable and \
               is_allowed_origin(pkg,allowed_origins):
            pkg.markUpgrade()
            if check_changes_for_sanity(cache, allowed_origins):
                 pkgs_to_upgrade.append(pkg)
            else:
                cache.clear()
                for pkg2 in pkgs_to_upgrade:
                    pkg2.markUpgrade()

    
    print "pkgs to upgrade: "
    print "\n".join([pkg.name for pkg in pkgs_to_upgrade])
                    
# TODO: download and check for possible conffile prompts

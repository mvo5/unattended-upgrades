#!/usr/bin/python2.4

import apt
from optparse import OptionParser

class MyCache(apt.Cache):
    def clear(self):
        for pkg in cache:
            pkg.markKeep()
        assert self._cache.InstCout == 0 and self._cache.BrokenCount == 0 \
               and self._cache.RemoveCount == 0
        

def is_allowed_origin(pkg, allowed_origins):
    origin = pkg.candidateOrigin
    print origin
    for allowed in allowed_origins:
        if origin.component == allowed:
            return True
    return False

def check_changes_for_sanity(cache, allowed_origins):
    if cache.BrokenCount != 0:
        return False
    for pkg in cache:
        if pkg.markedRemove:
            return False
        if pkg.markedInstall or pkg.markedUpgrade:
            if not is_allowed_origion(pkg, allowed_origins):
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
    allowed_origins = ["breezy-security"]
    
    for pkg in cache:
        if pkg.isUpgradable and \
               is_allowed_origin(pkg,allowed_origins):
            pkg.markUpgrade()
            if check_changes_for_sanity(cache):
                cache.clean()
                for pkg2 in pkgs_to_upgrade:
                    pkg2.markUpgradable()
                else:
                    pkgs.append(pkg)
    print "pkgs to upgrade: %s" % pkgs_to_upgrade
                    
# TODO: download and check for possible conffile prompts

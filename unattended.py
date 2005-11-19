#!/usr/bin/python2.4

import apt, apt_pkg
import sys, os
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
    # FIXME: check if the archive is trusted!
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

    # options
    parser = OptionParser()
    parser.add_option("-d", "--debug",
                      action="store_true", dest="debug", default=False,
                      help="print debug messages")
    (options, args) = parser.parse_args()
    debug = options.debug

    if debug:
        dir = "/tmp/pyapt-test"
        try:
            os.mkdir(dir)
            os.mkdir(dir+"/partial")
        except OSError:
            pass
        apt_pkg.Config.Set("Dir::Cache::archives",dir)

    # get a cache
    cache = MyCache()

    # FIXME: figure with with lsb_release
    allowed_origins = [("Ubuntu","breezy-security")]

    # find out about the packages that are upgradable (in a allowed_origin)
    pkgs_to_upgrade = []
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


                    
    # download
    list = apt_pkg.GetPkgSourceList()
    list.ReadMainList()
    recs = apt_pkg.GetPkgRecords(cache._cache)
    fetcher = apt_pkg.GetAcquire()
    pm = apt_pkg.GetPackageManager(cache._depcache)
    pm.GetArchives(fetcher,list,recs)
    for item in fetcher.Items:
        #print "%s -> %s:\n Status: %s Complete: %s IsTrusted: %s" % \
        #      (item.DescURI, item.DestFile,  item.Status,
        #       item.Complete,  item.IsTrusted)
        if item.Status == item.StatError:
            print "Some error ocured: '%s'" % item.ErrorText
        print
    res = fetcher.Run()

    # now check the downloaded debs for conffile conflicts
    for item in fetcher.Items:
        print "%s -> %s:\n Status: %s Complete: %s IsTrusted: %s" % \
              (item.DescURI, item.DestFile,  item.Status,
               item.Complete,  item.IsTrusted)
        if item.Status == item.StatError:
            print "Some error ocured: '%s'" % item.ErrorText
        if item.Complete == False:
            print "No error, still nothing downloaded"
        print
        # check_conffile_prompt(item.DestFile) 

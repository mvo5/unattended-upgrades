#!/usr/bin/python2.4

import apt, apt_pkg, apt_inst
import sys, os, string
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

def pkgname_from_deb(debfile):
    # FIXME: add error checking here
    control = apt_inst.debExtractControl(open(debfile))
    sections = apt_pkg.ParseSection(control)
    return sections["Package"]

def conffile_prompt(destFile):
    print "check_conffile_prompt('%s')" % destFile
    pkgname = pkgname_from_deb(destFile)
    status_file = apt_pkg.Config.Find("Dir::State::status")
    parse = apt_pkg.ParseTagFile(open(status_file,"r"))
    while parse.Step() == 1:
        if parse.Section.get("Package") == pkgname:
            print "found pkg: %s" % pkgname
            if parse.Section.has_key("Conffiles"):
                conffiles = parse.Section.get("Conffiles")
                # Conffiles:
                # /etc/bash_completion.d/m-a c7780fab6b14d75ca54e11e992a6c11c
                for line in string.split(conffiles,"\n"):
                    (file, md5) = string.split(string.strip(line))
                    if os.path.exists(file):
                        current_md5 = apt_pkg.md5sum(open(file).read())
                        if current_md5 != md5:
                            return True
    return False


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

        # FIXME: add tests for the conffile_prompt code
        #if conffile_prompt(sys.argv[1]):
        #    print "will prompt"
        #else:
        #    print "wont prompt"
        #sys.exit(1)


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
    if debug:
        fetcher = apt_pkg.GetAcquire(apt.progress.TextFetchProgress())
    else:
        fetcher = apt_pkg.GetAcquire()
    pm = apt_pkg.GetPackageManager(cache._depcache)
    pm.GetArchives(fetcher,list,recs)
    #for item in fetcher.Items:
    #    #print "%s -> %s:\n Status: %s Complete: %s IsTrusted: %s" % \
    #    #      (item.DescURI, item.DestFile,  item.Status,
    #    #       item.Complete,  item.IsTrusted)
    #    if item.Status == item.StatError:
    #        print "Some error ocured: '%s'" % item.ErrorText
    #    #print
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
            continue
        if conffile_prompt(item.DestFile):
            # FIXME: skip package (means to re-run the whole marking again
            # and making sure that the package will not be pulled in by
            # some other package again!
            print "pkg '%s' has conffile prompt" % pkgname_from_deb(item.DestFile)
            

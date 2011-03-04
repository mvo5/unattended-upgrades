#!/usr/bin/python

import apt
import logging
import glob
import os
import shutil
import subprocess
import sys
import unittest

apt.apt_pkg.config.set("APT::Architecture", "i386")
sys.path.insert(0, "..")
import unattended_upgrade

SOURCES_LIST="""
deb http://archive.ubuntu.com/ubuntu/ lucid main restricted
deb-src http://archive.ubuntu.com/ubuntu/ lucid main restricted

deb http://archive.ubuntu.com/ubuntu/ lucid-updates main restricted
deb-src http://archive.ubuntu.com/ubuntu/ lucid-updates main restricted

deb http://security.ubuntu.com/ubuntu/ lucid-security main restricted
deb-src http://security.ubuntu.com/ubuntu/ lucid-security main restricted
"""
TARBALL="lucid-i386.tgz"

class MockOptions(object):
    debug = False
    dry_run = False
    minimal_upgrade_steps = False

class TestUnattendedUpgrade(unittest.TestCase):

    def _create_new_debootstrap_tarball(self, tarball, target):
        print "creating initial test tarball, this is needed only once"
        # force i386
        subprocess.call(["debootstrap",
                         "--arch=i386",
                         "lucid", target])
        subprocess.call(["chroot", target, "apt-get", "clear"])
        subprocess.call(["tar", "czf", tarball, target])

    def _unpack_debootstrap_tarball(self, tarball, target):
        subprocess.call(["tar", "xzf", tarball])

    def test_normal_upgrade(self):
        print "Running normal unattended upgrade in chroot"
        options = MockOptions()
        options.minimal_upgrade_steps = False
        self._run_upgrade_test_in_real_chroot(options)

    def test_minimal_steps_upgrade(self):
        print "Running minimal steps unattended upgrade in chroot"
        options = MockOptions()
        options.minimal_upgrade_steps = True
        self._run_upgrade_test_in_real_chroot(options)

    def _run_upgrade_test_in_real_chroot(self, options):
        """ helper that runs the unattended-upgrade in a chroot
            and does some basic verifications
        """
        if os.getuid() != 0:
            print "Skipping because uid != 0"
            return

        # create chroot
        target = "./test-chroot"
        # cleanup 
        if os.path.exists(target):
            shutil.rmtree(target)
        if not os.path.exists(TARBALL):
            self._create_new_debootstrap_tarball(TARBALL, target)
        # create new
        self._unpack_debootstrap_tarball(TARBALL, target)
        open(os.path.join(target, "etc/apt/apt.conf"), "w").write(
            'APT::Architecture "i386";')
        open(os.path.join(target, "etc/apt/sources.list"), "w").write(
            SOURCES_LIST)
        # and run the upgrade test
        pid = os.fork()
        if pid == 0:
            # chroot
            os.chroot(target)
            os.chdir("/")
            if not os.path.exists("/var/log/unattended-upgrades/"):
                os.makedirs("/var/log/unattended-upgrades/")
            # make sure we are up-to-date
            subprocess.call(["apt-get","update", "-q", "-q"])
            # run it
            unattended_upgrade.DISTRO_CODENAME = "lucid"
            unattended_upgrade.main(options)
            os._exit(0)
        else:
            (pid, status) = os.waitpid(pid, 0)
            ret = os.WEXITSTATUS(status)
        self.assertEqual(ret, 0)
        # examine log
        log = os.path.join(
            target, "var/log/unattended-upgrades/unattended-upgrades.log")
        logfile = open(log).read()
        self.assertTrue("Packages that are upgraded: bzip2" in logfile)
        self.assertFalse("ERROR Installing the upgrades failed" in logfile)
        #print logfile
        dpkg_log = os.path.join(target, "var/log/unattended-upgrades/*-dpkg*.log")
        dpkg_logfile = open(glob.glob(dpkg_log)[0]).read()
        self.assertTrue("Preparing to replace bzip2 1.0.5-4" in dpkg_logfile)
        #print dpkg_logfile


if __name__ == "__main__":
    #logging.basicConfig(level=logging.DEBUG)
    unittest.main()

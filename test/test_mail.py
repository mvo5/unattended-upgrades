#!/usr/bin/python

import apt
import apt_pkg
import os
import logging
import unittest
import sys

from StringIO import StringIO

import unattended_upgrade
from unattended_upgrade import send_summary_mail

class TestSendSummaryMail(unittest.TestCase):

    def setUp(self):
        # monkey patch to make it testable
        unattended_upgrade.REBOOT_REQUIRED_FILE = "./reboot-required"
        # mock-mail binary that creates a mail.txt file
        unattended_upgrade.MAIL_BINARY = "./mock-mail"
        # setup mail
        apt_pkg.config.set("Unattended-Upgrade::Mail", "root")

    def tearDown(self):
        for f in ["mail.txt", "reboot-required", "apt-term.log"]:
            if os.path.exists(f):
                os.unlink(f)

    def _return_mock_data(self):
        """ return input tuple for send_summary_mail """
        pkgs = "\n".join(["2vcard"])
        res = True
        pkgs_kept_back = []
        mem_log = StringIO("mem_log text")
        logfile_dpkg = "./apt-term.log"
        open("./apt-term.log", "w").write("logfile_dpkg text")
        return (pkgs, res, pkgs_kept_back, mem_log, logfile_dpkg)

    def _verify_common_mail_content(self, mail_txt):
        self.assertTrue("logfile_dpkg text" in mail_txt)
        self.assertTrue("mem_log text" in mail_txt)
        self.assertTrue("Packages that are upgraded:\n 2vcard" in mail_txt)

    def testSummaryMailReboot(self):
        open("./reboot-required","w").write("")
        send_summary_mail(*self._return_mock_data())
        os.unlink("./reboot-required")
        mail_txt = open("mail.txt").read()
        self.assertTrue("[reboot required]" in mail_txt)
        self._verify_common_mail_content(mail_txt)
        
    def testSummaryMailNoReboot(self):
        send_summary_mail(*self._return_mock_data())
        mail_txt = open("mail.txt").read()
        self.assertFalse("[reboot required]" in mail_txt)
        self._verify_common_mail_content(mail_txt)

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()


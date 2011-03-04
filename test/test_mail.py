#!/usr/bin/python

import apt
import apt_pkg
import os
import logging
import unittest
import sys

from StringIO import StringIO

import unattended_upgrade
import unattended_upgrade
from unattended_upgrade import send_summary_mail, setup_apt_listchanges

class TestSendSummaryMail(unittest.TestCase):

    def setUp(self):
        # monkey patch to make it testable
        unattended_upgrade.REBOOT_REQUIRED_FILE = "./reboot-required"
        # mock-mail binary that creates a mail.txt file
        unattended_upgrade.MAIL_BINARY = "./mock-mail"
        # setup mail
        apt_pkg.config.set("Unattended-Upgrade::Mail", "root")
        apt_pkg.config.set("Unattended-Upgrade::MailOnlyOnError", "false")

    def tearDown(self):
        for f in ["mail.txt", "reboot-required", "apt-term.log"]:
            if os.path.exists(f):
                os.unlink(f)

    def _return_mock_data(self, successful=True):
        """ return input tuple for send_summary_mail """
        pkgs = "\n".join(["2vcard"])
        res = successful
        pkgs_kept_back = []
        mem_log = StringIO("mem_log text")
        logfile_dpkg = "./apt-term.log"
        open("./apt-term.log", "w").write("logfile_dpkg text")
        return (pkgs, res, pkgs_kept_back, mem_log, logfile_dpkg)

    def _verify_common_mail_content(self, mail_txt):
        self.assertTrue("logfile_dpkg text" in mail_txt)
        self.assertTrue("mem_log text" in mail_txt)
        self.assertTrue("Packages that are upgraded:\n 2vcard" in mail_txt)

    def test_summary_mail_reboot(self):
        open("./reboot-required","w").write("")
        send_summary_mail(*self._return_mock_data())
        os.unlink("./reboot-required")
        mail_txt = open("mail.txt").read()
        self.assertTrue("[reboot required]" in mail_txt)
        self._verify_common_mail_content(mail_txt)
        
    def test_summary_mail_no_reboot(self):
        send_summary_mail(*self._return_mock_data())
        mail_txt = open("mail.txt").read()
        self.assertFalse("[reboot required]" in mail_txt)
        self._verify_common_mail_content(mail_txt)
    
    def test_summary_mail_only_on_error(self):
        # default is to always send mail, ensure this is correct
        # for both success and failure
        apt_pkg.config.set("Unattended-Upgrade::MailOnlyOnError", "false")
        send_summary_mail(*self._return_mock_data(successful=True))
        self._verify_common_mail_content(open("mail.txt").read())
        os.remove("mail.txt")
        # now with a simulated failure
        send_summary_mail(*self._return_mock_data(successful=False))
        self._verify_common_mail_content(open("mail.txt").read())
        os.remove("mail.txt")
        # now test with "MailOnlyOnError"
        apt_pkg.config.set("Unattended-Upgrade::MailOnlyOnError", "true")
        send_summary_mail(*self._return_mock_data(successful=True))
        self.assertFalse(os.path.exists("mail.txt"))
        send_summary_mail(*self._return_mock_data(successful=False))
        mail_txt = open("mail.txt").read()
        self._verify_common_mail_content(mail_txt)
        self.assertTrue("Unattended upgrade returned: False" in mail_txt)
        self.assertTrue(os.path.exists("mail.txt"))

    def test_apt_listchanges(self):
        # test with mail as frontend
        os.environ["APT_LISTCHANGES_FRONTEND"] = "canary"
        unattended_upgrade.SENDMAIL_BINARY="/bin/true"
        setup_apt_listchanges("./data/listchanges.conf.mail")
        self.assertEqual(os.environ["APT_LISTCHANGES_FRONTEND"], "canary")
        # test with pager as frontend
        os.environ["APT_LISTCHANGES_FRONTEND"] = "canary"
        unattended_upgrade.SENDMAIL_BINARY="/bin/true"
        setup_apt_listchanges("./data/listchanges.conf.pager")
        self.assertEqual(os.environ["APT_LISTCHANGES_FRONTEND"], "none")

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()


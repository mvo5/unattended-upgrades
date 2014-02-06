#!/usr/bin/python3
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import apt_pkg
import os
import sys
import unittest

from io import StringIO
from email.parser import Parser

import unattended_upgrade
from unattended_upgrade import send_summary_mail, setup_apt_listchanges


# note this is not a unittest.TestCase as it needs to be parameterized
class CommonTestsForMailxAndSendmail(object):

    EXPECTED_MAIL_CONTENT_STRINGS = [
        "logfile_dpkg text",
        "mem_log text",
    ]

    def common_setup(self):
        # monkey patch to make it testable
        unattended_upgrade.REBOOT_REQUIRED_FILE = "./reboot-required"
        unattended_upgrade.MAIL_BINARY = "./no-mailx-binary-here"
        unattended_upgrade.SENDMAIL_BINARY = "./no-sendmail-binary-here"
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
        # include some unicode chars here for good measure
        mem_log = StringIO("""mem_log text üöä
Allowed origins are: ['o=Debian,n=wheezy', 'o=Debian,n=wheezy-updates',\
 'o=Debian,n=wheezy,l=Debian-Security', 'origin=Debian,archive=stable,label=\
Debian-Security']
""")
        logfile_dpkg = "./apt-term.log"
        with open("./apt-term.log", "w") as fp:
            fp.write("logfile_dpkg text")
        return (pkgs, res, pkgs_kept_back, mem_log, logfile_dpkg)

    def _verify_common_mail_content(self, mail_txt):
        for expected_string in self.EXPECTED_MAIL_CONTENT_STRINGS:
            self.assertTrue(expected_string in mail_txt)

    def test_summary_mail_reboot(self):
        with open("./reboot-required", "w") as fp:
            fp.write("")
        send_summary_mail(*self._return_mock_data())
        os.unlink("./reboot-required")
        # this is used for py2 compat for py3 only we can do
        # remove the "rb" and the subsequent '.decode("utf-8")'
        with open("mail.txt", "rb") as fp:
            mail_txt = fp.read().decode("utf-8")
        self.assertTrue("[reboot required]" in mail_txt)
        self._verify_common_mail_content(mail_txt)
        self.assertTrue("Packages that were upgraded:\n 2vcard" in mail_txt)

    def test_summary_mail_no_reboot(self):
        send_summary_mail(*self._return_mock_data())
        with open("mail.txt", "rb") as fp:
            mail_txt = fp.read().decode("utf-8")
        self.assertFalse("[reboot required]" in mail_txt)
        self._verify_common_mail_content(mail_txt)
        self.assertTrue("Packages that were upgraded:\n 2vcard" in mail_txt)

    def test_summary_mail_only_on_error(self):
        # default is to always send mail, ensure this is correct
        # for both success and failure
        apt_pkg.config.set("Unattended-Upgrade::MailOnlyOnError", "false")
        send_summary_mail(*self._return_mock_data(successful=True))
        with open("mail.txt", "rb") as fp:
            self._verify_common_mail_content(fp.read().decode("utf-8"))
        os.remove("mail.txt")
        # now with a simulated failure
        send_summary_mail(*self._return_mock_data(successful=False))
        with open("mail.txt", "rb") as fp:
            self._verify_common_mail_content(fp.read().decode("utf-8"))
        os.remove("mail.txt")
        # now test with "MailOnlyOnError"
        apt_pkg.config.set("Unattended-Upgrade::MailOnlyOnError", "true")
        send_summary_mail(*self._return_mock_data(successful=True))
        self.assertFalse(os.path.exists("mail.txt"))
        send_summary_mail(*self._return_mock_data(successful=False))
        with open("mail.txt", "rb") as fp:
            mail_txt = fp.read().decode("utf-8")
        self._verify_common_mail_content(mail_txt)
        self.assertTrue("Unattended upgrade returned: False" in mail_txt)
        self.assertTrue(os.path.exists("mail.txt"))
        self.assertTrue(
            "Packages that attempted to upgrade:\n 2vcard" in mail_txt)

    def test_apt_listchanges(self):
        # test with sendmail available
        unattended_upgrade.SENDMAIL_BINARY = "/bin/true"
        setup_apt_listchanges("./data/listchanges.conf.mail")
        self.assertEqual(os.environ["APT_LISTCHANGES_FRONTEND"], "mail")
        # test without sendmail
        unattended_upgrade.SENDMAIL_BINARY = "/bin/not-here-xxxxxxxxx"
        setup_apt_listchanges("./data/listchanges.conf.pager")
        self.assertEqual(os.environ["APT_LISTCHANGES_FRONTEND"], "none")


class MailxTestCase(CommonTestsForMailxAndSendmail, unittest.TestCase):

    def setUp(self):
        self.common_setup()
        unattended_upgrade.MAIL_BINARY = "./mock-mail"

    def _verify_common_mail_content(self, mail_txt):
        CommonTestsForMailxAndSendmail._verify_common_mail_content(
            self, mail_txt)
        # setting this header with mailx is not possible so ensure
        # we don't accidently try
        self.assertFalse('text/plain; charset="utf-8"' in mail_txt)


class SendmailTestCase(CommonTestsForMailxAndSendmail, unittest.TestCase):

    def setUp(self):
        self.common_setup()
        unattended_upgrade.SENDMAIL_BINARY = "./mock-sendmail"

    def _verify_common_mail_content(self, mail_txt):
        CommonTestsForMailxAndSendmail._verify_common_mail_content(
            self, mail_txt)

        # python2 needs this as utf8 encoded string (not unicode)
        if sys.version < '3':
            mail_txt = mail_txt.encode("utf-8")

        msg = Parser().parsestr(mail_txt)
        content_type = msg["Content-Type"]
        self.assertEqual(content_type, 'text/plain; charset="utf-8"')

    def test_mail_quoted_printable(self):
        """Regression test for debian bug #700178"""
        send_summary_mail(*self._return_mock_data())
        with open("mail.txt", "rb") as fp:
            log_data = fp.read().decode("utf-8")
        needle = "Allowed origins are: ['o=3DDebian,n=3Dwheezy', "\
            "'o=3DDebian,n=3Dwheezy-updat=\n"\
            "es', 'o=3DDebian,n=3Dwheezy,l=3DDebian-Security', "\
            "'origin=3DDebian,archive=\n"\
            "=3Dstable,label=3DDebian-Security']"
        self.assertTrue(needle in log_data)


class SendmailAndMailxTestCase(SendmailTestCase):

    def setUp(self):
        self.common_setup()
        unattended_upgrade.MAIL_BINARY = "./mock-mail"
        unattended_upgrade.SENDMAIL_BINARY = "./mock-sendmail"

if __name__ == "__main__":
    #logging.basicConfig(level=logging.DEBUG)
    unittest.main()

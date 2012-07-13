#!/usr/bin/python
# -*- coding: utf-8 -*-
import apt_pkg
import os
import unittest

from email.parser import Parser
from StringIO import StringIO

import unattended_upgrade
from unattended_upgrade import send_summary_mail, setup_apt_listchanges


# note this is not a unittest.TestCase as it needs to be parameterized
class CommonTestsForMailxAndSendmail(object):

    EXPECTED_MAIL_CONTENT_STRINGS = [
        "logfile_dpkg text",
        "mem_log text",
        "Packages that are upgraded:\n 2vcard",
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
        mem_log = StringIO(u"mem_log text üöä")
        logfile_dpkg = "./apt-term.log"
        open("./apt-term.log", "w").write("logfile_dpkg text")
        return (pkgs, res, pkgs_kept_back, mem_log, logfile_dpkg)

    def _verify_common_mail_content(self, mail_txt):
        for expected_string in self.EXPECTED_MAIL_CONTENT_STRINGS:
            self.assertTrue(expected_string in mail_txt)

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
        # test with sendmail available
        unattended_upgrade.SENDMAIL_BINARY="/bin/true"
        setup_apt_listchanges("./data/listchanges.conf.mail")
        self.assertEqual(os.environ["APT_LISTCHANGES_FRONTEND"], "mail")
        # test without sendmail
        unattended_upgrade.SENDMAIL_BINARY="/bin/not-here-xxxxxxxxx"
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
        msg = Parser().parsestr(mail_txt)
        content_type = msg["Content-Type"]
        self.assertEqual(content_type, 'text/plain; charset="utf-8"')
    

class SendmailAndMailxTestCase(SendmailTestCase):

    def setUp(self):
        self.common_setup()
        unattended_upgrade.MAIL_BINARY = "./mock-mail"
        unattended_upgrade.SENDMAIL_BINARY = "./mock-sendmail"

if __name__ == "__main__":
    #logging.basicConfig(level=logging.DEBUG)
    unittest.main()


#!/usr/bin/python3
# -*- coding: utf-8 -*-
from email.parser import Parser
from io import StringIO
from unittest.mock import patch
import os
from textwrap import dedent
import unittest


import apt_pkg

import unattended_upgrade
from unattended_upgrade import (
    get_dpkg_log_content,
    LoggingDateTime,
    send_summary_mail,
    setup_apt_listchanges,
)
from test.test_base import TestBase, MockOptions


class ExtractDpkgLogTestCase(TestBase):

    def test_get_dpkg_log_content(self):
        logfile_dpkg = os.path.join(self.tempdir, "apt-term.log")
        # note that we intentionally not have a "Log ended:" here
        # because this may happen if something crashes power goes
        # down etc
        OLD_LOG = dedent("""\
            Log started: 2013-01-01  12:00:00
            old logfile text
        """)
        NEW_LOG = dedent("""\
            Log started: 2014-10-28  10:00:00
            random logfile_dpkg text
            Log ended: 2013-01-01  12:20:00

            Log started: 2014-10-28  12:21:00
            more random logfile_dpkg text
            Log ended: 2013-01-01  12:30:00
            """)
        with open(logfile_dpkg, "w") as fp:
            fp.write(OLD_LOG)
            fp.write("\n")
            fp.write(NEW_LOG)
        start_time = LoggingDateTime.from_string("2014-10-28  10:00:00")
        dpkg_log_content = get_dpkg_log_content(logfile_dpkg, start_time)
        self.assertEqual(dpkg_log_content, NEW_LOG)


# note this is not a unittest.TestCase as it needs to be parameterized
class CommonTestsForMailxAndSendmail(object):

    EXPECTED_MAIL_CONTENT_STRINGS = [
        "random logfile_dpkg text",
        "mem_log text",
    ]
    NOT_EXPECTED_MAIL_CONTENT_STRINGS = [
        "old logfile text",
    ]

    def common_setup(self):
        # monkey patch to make it testable
        unattended_upgrade.REBOOT_REQUIRED_FILE = os.path.join(
            self.tempdir, "reboot-required")
        unattended_upgrade.MAIL_BINARY = "./no-mailx-binary-here"
        unattended_upgrade.SENDMAIL_BINARY = "./no-sendmail-binary-here"
        # setup mail
        apt_pkg.config.set("Unattended-Upgrade::Mail", "root")
        apt_pkg.config.set("Unattended-Upgrade::MailReport", "on-change")
        apt_pkg.config.set("Unattended-Upgrade::LogDir", self.tempdir)

    def _return_mock_data(self, successful=True):
        """ return input tuple for send_summary_mail """
        pkgs = ["2vcard"]
        res = successful
        result_str = "Result String"
        pkgs_kept_back = {"Debian wheezy-security": ["linux-image"]}
        pkgs_removed = ["telnet"]
        pkgs_kept_installed = ["hello"]
        # include some unicode chars here for good measure
        mem_log = StringIO("""mem_log text üöä
Allowed origins are: ['o=Debian,n=wheezy', 'o=Debian,n=wheezy-updates',\
 'o=Debian,n=wheezy,l=Debian-Security', 'origin=Debian,archive=stable,label=\
Debian-Security']
""")
        dpkg_log_content = dedent("""\
        Log started: 2014-10-28  12:21:00
        random logfile_dpkg text
        Log ended: 2013-01-01  12:30:00
        """)
        return (pkgs, res, result_str, pkgs_kept_back, pkgs_removed,
                pkgs_kept_installed, mem_log, dpkg_log_content)

    def _verify_common_mail_content(self, mail_txt):
        for expected_string in self.EXPECTED_MAIL_CONTENT_STRINGS:
            self.assertTrue(expected_string in mail_txt)
        for not_expected_string in self.NOT_EXPECTED_MAIL_CONTENT_STRINGS:
            self.assertFalse(not_expected_string in mail_txt)
        self.assertEqual(mail_txt.count("Log started: "), 1)

    def test_summary_mail_reboot(self):
        with open(unattended_upgrade.REBOOT_REQUIRED_FILE, "w") as fp:
            fp.write("")
        send_summary_mail(*self._return_mock_data())
        # this is used for py2 compat for py3 only we can do
        # remove the "rb" and the subsequent '.decode("utf-8")'
        with open(os.path.join(self.tempdir, "mail.txt"), "rb") as fp:
            mail_txt = fp.read().decode("utf-8")
        self.assertTrue("[reboot required]" in mail_txt)
        self._verify_common_mail_content(mail_txt)
        self.assertTrue("Packages that were upgraded:\n 2vcard" in mail_txt)

    def test_summary_mail_no_reboot(self):
        send_summary_mail(*self._return_mock_data())
        with open(os.path.join(self.tempdir, "mail.txt"), "rb") as fp:
            mail_txt = fp.read().decode("utf-8")
        self.assertFalse("[reboot required]" in mail_txt)
        self._verify_common_mail_content(mail_txt)
        self.assertTrue("Packages that were upgraded:\n 2vcard" in mail_txt)

    def test_summary_mail_only_on_error(self):
        # default is to always send mail, ensure this is correct
        # for both success and failure
        apt_pkg.config.set("Unattended-Upgrade::MailReport", "on-change")
        send_summary_mail(*self._return_mock_data(successful=True))
        with open(os.path.join(self.tempdir, "mail.txt"), "rb") as fp:
            self._verify_common_mail_content(fp.read().decode("utf-8"))
        os.remove(os.path.join(self.tempdir, "mail.txt"))
        # now with a simulated failure
        send_summary_mail(*self._return_mock_data(successful=False))
        with open(os.path.join(self.tempdir, "mail.txt"), "rb") as fp:
            self._verify_common_mail_content(fp.read().decode("utf-8"))
        os.remove(os.path.join(self.tempdir, "mail.txt"))
        # now test with "only-on-error"
        apt_pkg.config.set("Unattended-Upgrade::MailReport", "only-on-error")
        send_summary_mail(*self._return_mock_data(successful=True))
        self.assertFalse(
            os.path.exists(os.path.join(self.tempdir, "mail.txt")))
        send_summary_mail(*self._return_mock_data(successful=False))
        with open(os.path.join(self.tempdir, "mail.txt"), "rb") as fp:
            mail_txt = fp.read().decode("utf-8")
        self._verify_common_mail_content(mail_txt)
        self.assertTrue("Unattended upgrade result: Result String" in mail_txt)
        self.assertTrue(
            os.path.exists(os.path.join(self.tempdir, "mail.txt")))
        self.assertTrue(
            "Packages that attempted to upgrade:\n 2vcard" in mail_txt)

    def test_summary_mail_blacklisted(self):
        # Test that blacklisted packages are mentioned in the mail message.
        send_summary_mail(*self._return_mock_data())
        self.assertTrue(
            os.path.exists(os.path.join(self.tempdir, "mail.txt")))
        with open(os.path.join(self.tempdir, "mail.txt"), "rb") as fp:
            mail_txt = fp.read().decode("utf-8")
        self.assertTrue("[package on hold]" in mail_txt)
        self._verify_common_mail_content(mail_txt)
        self.assertTrue(
            "Packages with upgradable origin but kept back:\n"
            " Debian wheezy-security:\n  linux-image"
            in mail_txt)

    def test_summary_mail_blacklisted_only(self):
        # Test that when only blacklisted packages are available, they
        # are still mentioned in the mail message.
        pkgs, res, result_str, pkgs_kept_back, pkgs_removed, \
            pkgs_kept_installed, mem_log, logf_dpkg = self._return_mock_data(
                successful=True)
        pkgs = []
        send_summary_mail(pkgs, res, result_str, pkgs_kept_back, pkgs_removed,
                          pkgs_kept_installed, mem_log, logf_dpkg)
        self.assertTrue(
            os.path.exists(os.path.join(self.tempdir, "mail.txt")))
        with open(os.path.join(self.tempdir, "mail.txt"), "rb") as fp:
            mail_txt = fp.read().decode("utf-8")
        self.assertTrue("[package on hold]" in mail_txt)
        self._verify_common_mail_content(mail_txt)
        self.assertTrue(
            "Packages with upgradable origin but kept back:\n"
            " Debian wheezy-security:\n  linux-image"
            in mail_txt)
        self.assertFalse(
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

    def test_summary_mail_from_address(self):
        apt_pkg.config.set("Unattended-Upgrade::Sender", "rootolv")
        self.addCleanup(apt_pkg.config.set, "Unattended-Upgrade::Sender", "")
        send_summary_mail(*self._return_mock_data())
        with open(os.path.join(self.tempdir, "mail.txt"), "rb") as fp:
            mail_txt = fp.read().decode("utf-8")
        self.assertTrue(
            "From: rootolv" in mail_txt, "missing From: in %s" % mail_txt)

    @patch("unattended_upgrade.run")
    def test_exception(self, mock_run):
        exception_string = "Test exception for email"
        mock_run.side_effect = Exception(exception_string)
        # run it
        options = MockOptions()
        exception_raised = False
        try:
            unattended_upgrade.main(options)
        except Exception as e:
            self.assertEqual(str(e), exception_string)
            exception_raised = True
        self.assertTrue(exception_raised)
        with open(os.path.join(self.tempdir, "mail.txt"), "rb") as fp:
            mail_txt = fp.read().decode("utf-8")
        self.assertTrue(exception_string in mail_txt)


class MailxTestCase(CommonTestsForMailxAndSendmail, TestBase):

    def setUp(self):
        TestBase.setUp(self)
        self.common_setup()
        unattended_upgrade.MAIL_BINARY = make_mock_mailx(self.tempdir)

    def _verify_common_mail_content(self, mail_txt):
        CommonTestsForMailxAndSendmail._verify_common_mail_content(
            self, mail_txt)
        # setting this header with mailx is not possible so ensure
        # we don't accidently try
        self.assertFalse('text/plain; charset="utf-8"' in mail_txt)


def make_mock_sendmail(tmpdir):
    p = os.path.join(tmpdir, "mock-sendmail")
    with open(p, "w") as fp:
        fp.write("""#!/bin/sh
cat - -- > %s/mail.txt
    """ % tmpdir)
    os.chmod(p, 0o755)
    return p


def make_mock_mailx(tmpdir):
    p = os.path.join(tmpdir, "mock-mail")
    with open(p, "w") as fp:
        fp.write("""#!/bin/sh

echo "From: $2" > %(tmp)s/mail.txt
echo "Subject: $4" >> %(tmp)s/mail.txt
cat - -- >> %(tmp)s/mail.txt
        """ % {'tmp': tmpdir})
    os.chmod(p, 0o755)
    return p


class SendmailTestCase(CommonTestsForMailxAndSendmail, TestBase):

    def setUp(self):
        TestBase.setUp(self)
        self.common_setup()
        unattended_upgrade.SENDMAIL_BINARY = make_mock_sendmail(self.tempdir)

    def _verify_common_mail_content(self, mail_txt):
        CommonTestsForMailxAndSendmail._verify_common_mail_content(
            self, mail_txt)

        msg = Parser().parsestr(mail_txt)
        content_type = msg["Content-Type"]
        self.assertEqual(content_type, 'text/plain; charset="utf-8"')

    def test_mail_quoted_printable(self):
        """Regression test for debian bug #700178"""
        send_summary_mail(*self._return_mock_data())
        with open(os.path.join(self.tempdir, "mail.txt"), "rb") as fp:
            log_data = fp.read().decode("utf-8")
        needle = "Allowed origins are: ['o=3DDebian,n=3Dwheezy', "\
            "'o=3DDebian,n=3Dwheezy-updat=\n"\
            "es', 'o=3DDebian,n=3Dwheezy,l=3DDebian-Security', "\
            "'origin=3DDebian,archive=\n"\
            "=3Dstable,label=3DDebian-Security']"
        self.assertTrue(needle in log_data)


class SendmailAndMailxTestCase(SendmailTestCase):

    def setUp(self):
        SendmailTestCase.setUp(self)
        self.common_setup()
        unattended_upgrade.MAIL_BINARY = make_mock_mailx(self.tempdir)
        unattended_upgrade.SENDMAIL_BINARY = make_mock_sendmail(self.tempdir)


if __name__ == "__main__":
    # logging.basicConfig(level=logging.DEBUG)
    unittest.main()

#!/usr/bin/python3

import json
import os
import shutil

from unittest.mock import patch

import unattended_upgrade
from test.test_base import TestBase, MockOptions


class TestPlugins(TestBase):

    def setUp(self):
        TestBase.setUp(self)
        # XXX: copy/clean to root.plugins
        self.rootdir = self.make_fake_aptroot(
            template=os.path.join(self.testdir, "root.unused-deps"),
            fake_pkgs=[("test-package", "1.0.test.pkg", {})],
        )
        # create a fake plugin dir, our fake plugin just writes a json
        # dump of it's args
        fake_plugin_dir = os.path.join(self.tempdir, "plugins")
        os.makedirs(fake_plugin_dir, 0o755)
        example_plugin = os.path.join(
            os.path.dirname(__file__), "../examples/plugins/simple.py")
        shutil.copy(example_plugin, fake_plugin_dir)
        os.environ["UNATTENDED_UPGRADES_PLUGIN_PATH"] = fake_plugin_dir
        self.addCleanup(lambda: os.environ.pop("UNATTENDED_UPGRADES_PLUGIN_PATH"))
        # go to a tempdir as the simple.py plugin above will just write a
        # file into cwd
        os.chdir(self.tempdir)

    @patch("unattended_upgrade.reboot_required")
    @patch("unattended_upgrade.host")
    def test_plugin_happy(self, mock_host, mock_reboot_required):
        mock_reboot_required.return_value = True
        mock_host.return_value = "some-host"
        options = MockOptions()
        options.debug = False
        unattended_upgrade.main(options, rootdir=self.rootdir)
        with open("simple-example-postrun-res.json") as fp:
            arg1 = json.load(fp)
        # the log text needs extra processing
        log_dpkg = arg1.pop("log_dpkg")
        log_uu = arg1.pop("log_unattended_upgrades")
        self.assertEqual(arg1, {
            "plugin_api": "1.0",
            "hostname": "some-host",
            "success": True,
            "result": "All upgrades installed",
            "packages_upgraded": ["test-package"],
            # XXX: add test for pkgs_kept_back
            "packages_kept_back": [],
            # XXX: add test for pkgs_kept_installed
            "packages_kept_installed": [],
            # XXX: add test for pkgs_removed
            "packages_removed": [],
            "reboot_required": True,
        })
        self.assertTrue(log_dpkg.startswith("Log started:"))
        self.assertTrue(
            "Starting unattended upgrades script" in log_uu)
        self.assertIn("Packages that will be upgraded: test-package", log_uu)

    def test_plugin_data_postrun(self):
        res = unattended_upgrade.PluginDataPostrun({
            "plugin_api": "1.0",
            "hostname": "some-host",
            "success": True,
            "result": "some result str",
            "packages_upgraded": ["upgrade-pkg1", "upgrade-pkg2"],
            "packages_kept_back": ["kept-pkg1"],
            "packages_removed": ["rm-pkg1"],
            "packages_kept_installed": ["kept-installed-pkg1"],
            "reboot_required": False,
            "log_dpkg": "a very long dpkg log",
        })
        # ensure properties keep working
        self.assertEqual(res.plugin_api, "1.0")
        self.assertEqual(res.hostname, "some-host")
        self.assertEqual(res.success, True)
        self.assertEqual(res.result, "some result str")
        self.assertEqual(
            res.packages_upgraded, ["upgrade-pkg1", "upgrade-pkg2"])
        self.assertEqual(res.packages_kept_back, ["kept-pkg1"])
        self.assertEqual(res.packages_removed, ["rm-pkg1"])
        self.assertEqual(res.packages_kept_installed, ["kept-installed-pkg1"])
        self.assertEqual(res.reboot_required, False)
        self.assertEqual(res.log_dpkg, "a very long dpkg log")

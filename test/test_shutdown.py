#!/usr/bin/python3

from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
import os
from optparse import Values
import unittest
from unittest.mock import patch

import apt_pkg

from test.test_base import TestBase


loader = SourceFileLoader("unattended_upgrade_shutdown", os.path.join(
    os.path.dirname(__file__), "..", "unattended-upgrade-shutdown"))
spec = spec_from_loader(loader.name, loader)
assert spec is not None
shutdown = module_from_spec(spec)
loader.exec_module(shutdown)


class TestShutdown(TestBase):
    def test_shutdown_trigger(self):
        helper_class = shutdown.UnattendedUpgradesShutdown
        for configured, pending, stop_only, stopped, starts in (
                (False, False, False, False, False),
                (False, True, False, False, True),
                (True, False, False, False, True),
                (True, True, True, False, False),
                (False, True, True, False, False),
                (False, True, False, True, False)):
            with self.subTest(configured=configured, pending=pending,
                              stop_only=stop_only, stopped=stopped):
                apt_pkg.config.set("Unattended-Upgrade::InstallOnShutdown",
                                   str(configured))
                with patch.object(helper_class, "get_inhibit_shutdown_lock"), \
                        patch.object(helper_class, "get_inhibit_max_delay",
                                     return_value=30):
                    helper = helper_class(Values({"delay": 25,
                                                  "stop_only": stop_only}))
                helper.apt_pkg_reinit_done = True
                if stopped:
                    helper.stop_signal_received.set()
                with patch.dict(os.environ), \
                        patch.object(shutdown.os.path, "isfile",
                                     return_value=pending), \
                        patch.object(shutdown.subprocess, "Popen") as popen, \
                        patch.object(shutdown, "log_msg"), \
                        patch.object(shutdown, "log_progress"):
                    popen.return_value.poll.return_value = None
                    self.assertEqual(helper.try_iter_on_shutdown(), starts)
                    self.assertEqual(popen.called, starts)
                    if starts:
                        self.assertEqual(popen.call_args.args,
                                         (["unattended-upgrade"],))
                        self.assertEqual(popen.call_args.kwargs["env"][
                            "UNATTENDED_UPGRADES_FORCE_INSTALL_ON_SHUTDOWN"], "1")


if __name__ == "__main__":
    unittest.main()

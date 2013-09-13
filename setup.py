#!/usr/bin/env python

from setuptools import setup
from DistUtilsExtra.command import (
    build_extra,
    build_i18n,
)

if __name__ == "__main__":
    setup(
        name='unattended-upgrades',
        version='0.1',
        scripts=['unattended-upgrade'],
        data_files=[
            ('../etc/apt/apt.conf.d/',
                ["data/50unattended-upgrades"]),
            ('../etc/logrotate.d/',
                ["data/logrotate.d/unattended-upgrades"]),
            ('../usr/share/unattended-upgrades/',
                ["data/20auto-upgrades",
                 "data/20auto-upgrades-disabled",
                 "unattended-upgrade-shutdown"]),
            ('../usr/share/man/man8/',
                ["man/unattended-upgrade.8"]),
            ('../etc/pm/sleep.d/',
                ["pm/sleep.d/10_unattended-upgrades-hibernate"])
        ],
        cmdclass={"build": build_extra.build_extra,
                  "build_i18n":  build_i18n.build_i18n},
        test_suite="test",
    )

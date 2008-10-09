#!/usr/bin/env python

from distutils.core import setup
from DistUtilsExtra.command import *
import glob
import os

    
setup(name='unattended-upgrades', version='0.1',
      scripts=['unattended-upgrade'],
      data_files=[
		  ('../etc/apt/apt.conf.d/',
                   ["data/50unattended-upgrades"]),
                  ('../etc/logrotate.d/',
                   ["data/logrotate.d/unattended-upgrades"]),
                  ('../usr/share/unattended-upgrades/',
                   ["data/10auto-upgrades"])
                  ],
      cmdclass = { "build" : build_extra.build_extra,
                   "build_i18n" :  build_i18n.build_i18n }
      )



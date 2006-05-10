#!/usr/bin/env python

from distutils.core import setup
import glob
import os

    
setup(name='unattended-upgrades', version='0.1',
      scripts=['unattended-upgrade'],
      data_files=[
		  ('../etc/apt/apt.conf.d/',
                   ["data/50unattended-upgrades"]),
                  ('../etc/logrotate.d/',
                   ["data/logrotate.d/unattended-upgrades"])
                  ]
      )



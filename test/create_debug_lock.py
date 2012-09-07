#!/usr/bin/python3
#
# create a lock file so that unattended-upgrades-shutdown pauses
# on shutdown -- useful for testing

import apt_pkg
import os
import time


pid = os.fork()
if pid == 0:
    os.setsid()
    lock = apt_pkg.get_lock("/var/run/unattended-upgrades.lock")
    time.sleep(500)

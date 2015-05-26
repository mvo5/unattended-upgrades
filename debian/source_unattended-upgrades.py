"""
unattended-upgrades apport hook

Collects the following log file:
  - /var/log/unattended-upgrades/unattended-upgrades.log
Check to see if either of these conffiles has been modified:
  - /etc/apt/apt.conf.d/50unattended-upgrades
  - /etc/apt/apt.conf.d/10periodic
"""

from apport.hookutils import (
    attach_conffiles,
    attach_file_if_exists)


def add_info(report, ui):
    # always attach these files
    attach_conffiles(report, 'unattended-upgrades', ui=ui)
    attach_conffiles(report, 'update-notifier-common', ui=ui)
    attach_file_if_exists(
        report, '/var/log/unattended-upgrades/unattended-upgrades.log')

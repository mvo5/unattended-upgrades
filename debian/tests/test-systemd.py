#!/usr/bin/python3

import os
import sys
import subprocess


def test_systemd_service():
    '''
    Verify that the unattended-upgrades.service unit is started
    correctly. The unit must be started in order for the ExecStop=
    to work correctly
    '''
    Service = 'unattended-upgrades.service'
    try:
        subprocess.check_output(['systemctl', '--quiet', 'is-active', Service])
    except subprocess.CalledProcessError:
        out = subprocess.getoutput(
            'systemctl status unattended-upgrades.service')
        print('test_systemd_service() FAILED\n%s' % out)
        return False
    return True


def enable_install_on_shutdown():
    '''
    Enable InstallOnShutdown to verify that the command runs correctly
    upon reboot
    '''
    apt_conf_file = '/etc/apt/apt.conf.d/50unattended-upgrades'
    param = 'Unattended-Upgrade::InstallOnShutdown'
    sed_cmd = 's/\\/\\/%s.*/%s "true";/' % (param, param)

    try:
        subprocess.check_output(['/bin/sed', '-i', sed_cmd, apt_conf_file])
    except subprocess.CalledProcessError:
        print("Unable to edit %s" % apt_conf_file)
        return False
    return True


def check_log_files():
    '''
    Verify that the logfiles are correctly produced by the InstallOnShutdown
    run upon reboot. This will confirm that it did run correctly when we
    rebooted.
    '''
    logdir = '/var/log/unattended-upgrades/'
    logfiles = ['unattended-upgrades.log', 'unattended-upgrades-shutdown.log']

    for file in logfiles:
        if not os.path.exists(logdir + file):
            print("File missing : %s" % (logdir + file))
            return False
    return True


if __name__ == '__main__':
    autopkgtest_reboot_mark = os.getenv('AUTOPKGTEST_REBOOT_MARK')

    if autopkgtest_reboot_mark is None:
        if not test_systemd_service():
            sys.exit(1)

        if enable_install_on_shutdown():
            print('Rebooting to test InstallOnShutdown...')
            subprocess.check_call(['/tmp/autopkgtest-reboot-prepare',
                                   'InstallOnShutdown'])
            subprocess.check_call(['dbus-send', '--system', '--print-reply',
                                   '--dest=org.freedesktop.login1',
                                   '/org/freedesktop/login1',
                                   'org.freedesktop.login1.Manager.Reboot',
                                   'boolean:false'])
        else:
            sys.exit(1)

    if autopkgtest_reboot_mark == 'InstallOnShutdown':
        if not check_log_files():
            print("InstallOnShutdown did not run")
            sys.exit(1)
    else:
        print('Invalid autopkgtest_reboot_mark value')
        sys.exit(1)

    sys.exit(0)

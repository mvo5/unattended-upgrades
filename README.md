
Unattended upgrades
===================

This script upgrades packages automatically and unattended.

If you would prefer to disable it from the command line, run
"sudo dpkg-reconfigure -plow unattended-upgrades".

It will not install packages that require dependencies that can't be
fetched from allowed origins, and it will check for conffile prompts
before the install and holds back any package that requires them. 

Setup
-----

By default unattended-upgrades runs an update every day.

The main way to specify which packages will be auto-upgraded is by
means of their "origin" and "archive".  These are taken respectively
from the Origin and Suite fields of the repository's Release file,
or can be found in the output of:
```
$ apt-cache policy
```
in the "o" and "a" fields for the given repository.

The default setup auto-updates packages in the main and security
archives, which means that only stable and security updates are
applied.

This can be changed either with the
"Unattended-Upgrade::Allowed-Origins" or the 
"Unattended-Upgrade::Origins-Pattern" apt configuration lists, which
are listed in /etc/apt/apt.conf.d/50unattended-upgrades.
Also in this file are a range of other options that can be configured.

To override the configuration it is recommended to create an other APT
configuration file fragment which overrides the shipped default
value because updates to to shipped configuration file may conflict
with the local changes blocking updating unattended-upgrades itself.
The new file should sort later than 50unattended-upgrades to be
parsed later than the one shipping the default values, it can
be e.g. 52unattended-upgrades-local.

Allowed-Origins is a simple list of patterns of the form
"origin:archive".

Origins-Pattern allows you to give a list of
(glob-style) patterns to match against.  For example:
```
 Unattended-Upgrade::Origins-Pattern {
        "origin=Google\, Inc.,suite=contrib";
        "site=www.example.com,component=main";
 };
```
will upgrade a package if either the origin is "Google, Inc." and
suite is "contrib" or if it comes from www.example.com and is in
component "main".  The apt-cache policy short identifiers
(e.g. "o" for "origin") are also supported.

If you already configure what to install via apt pinning, you can
simply use "origin=*", e.g.:
```
 Unattended-Upgrade::Origins-Pattern {
        "origin=*";
 };
```

All operations are logged in /var/log/unattended-upgrades/. This
includes the dpkg output as well. The file
/etc/logrotate.d/unattended-upgrades controls how long logfiles are
kept, and how often they are rotated. See the `logrotate` manpage for
details.

If you want mail support you need to have a mail-transport-agent (e.g
postfix) or mailx installed.

Debugging
---------

If something goes wrong, or if you want to report a bug about the way
the script works, it's a good idea to run:
```
$ sudo unattended-upgrade --debug --dry-run
```
and look at the resulting logfile in:
/var/log/unattended-upgrades/unattended-upgrades.log 
It will also contain additional debug information.


Manual Setup
------------

To activate this script manually you need to ensure that the apt
configuration contains the following lines (this can be done via the
graphical "Software Source" program or via dpkg-reconfigure as well):
```
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
```
This means that it will check for updates every day, and install them
(if that is possible). If you have update-notifier installed, it will
setup /etc/apt/apt.conf.d/10periodic. Just edit this file then to fit
your needs. If you do not have this file, just create it or
create/edit /etc/apt/apt.conf - you can check your configuration by
running "apt-config dump".


Supported Options Reference
---------------------------

* `Unattended-Upgrade::Allowed-Origins` - list of (origin:archive) pairs
 
 Only packages from this origin:archive pair will be installed. You
 can see all available origin:archive pairs by running `apt-cache policy`
 and checking the "o=" and "a=" fields. Variable substitution is supported
 for ${distro_id} that contains the output of `lsb_release -i` and
 ${distro_codename} that contains the output of `lsb_release -c`.
 
 Example:
 ```
 Unattended-Upgrade::Allowed-Origins {
	"${distro_id}:${distro_codename}-security";
 ```

* `Unattended-Upgrade::Package-Blacklist` - list of regular expressions
 
 No packages that match the regular expressions in this list will be
 marked for upgrade. If a package A has a blacklisted package B as a
 dependency then both packages A and B will not be upgraded. Note
 that it's a list of regular expressions, so you may need to escape special
 characters like "+" as "\\+".
 
 Example:
 ```
 Unattended-Upgrade::Package-Blacklist {
     "libstdc\+\+6$";
 };
 ```

* `Unattended-Upgrade::Package-Whitelist` - list of regular expressions
 
 Only packages that match the regular expressions in this list will be
 marked for upgrade. By default dependencies of whitelisted packages
 are allowed. This can be changed to only ever allow whitelisted
 packages with the `Unattended-Upgrade::Package-Whitelist-Strict`
 boolean option.
 `Unattended-Upgrade::Package-Blacklist` still applies, thus blacklisted
 packages covered by the whitelist will still not be upraded nor will be
 installed or upgraded as dependencies of whitelisted packages.

 Example:
 ```
 Unattended-Upgrade::Package-Whitelist {
     "bash";
 };
 ```

* `Unattended-Upgrade::Package-Whitelist-Strict` - boolean (default:False)
 
 When set, allow only packages in `Unattended-Upgrade::Package-Whitelist`
 to be upgraded. This means that you also need to list all the dependencies
 of a whitelisted package, e.g. if A depends on B and only A is
 whitelisted, it will be held back.
 
 Example:
 ```
 Unattended-Upgrade::Package-Whitelist-Strict "true";
 ```

* `Unattended-Upgrade::AutoFixInterruptedDpkg` - boolean (default:True)
 
 Run `dpkg --force-confold --configure -a` if a unclean dpkg state is
 detected. This defaults to true to ensure that updates get installed
 even when the system got interrupted during a previous run.

* `Unattended-Upgrade::MinimalSteps` - boolean (default:True)
 
 Optimize for safety against e.g. power failure by performing the upgrade
 in minimal self-contained chunks. This also allows sending a SIGTERM to
 unattended-upgrades, and it will stop the upgrade when it finishes the
 current upgrade step.

* `Unattended-Upgrade::InstallOnShutdown` - boolean (default:False)
 
 Perform the upgrade when the machine is shutting down instead of
 doing it in the background while the machine is running.

* `Unattended-Upgrade::Mail` - string (default:"")

 Send an email to this address with information about the packages
 upgraded. If empty or unset no email is sent. This option requires
 a working local mail setup.
 
  Example:
 ```
 Unattended-Upgrade::Mail "user@example.com";
 ```

* `Unattended-Upgrade::Sender` - string (default:"root")

 Use the specified value in the "From" field of outgoing mails.
 
  Example:
 ```
 Unattended-Upgrade::Sender "server@example.com";
 ```

* `Unattended-Upgrade::MailReport` - string (default: "on-change")
 
 Possible values are "always", "only-on-error" or "on-change".
 If this value is not set then the value is set by using the legacy
 option `Unattended-Upgrade::MailOnlyOnError` (default:False) to choose
 between "only-on-error" and "on-change".

 NOTE that "never" is achieved by not setting any `Unattended-Upgrade::Mail`

* `Unattended-Upgrade::Remove-Unused-Dependencies` - boolean (default:False)
 
 Remove all unused dependencies after the upgrade has finished.

* `Unattended-Upgrade::Remove-New-Unused-Dependencies` - boolean (default:True)

 Remove any new unused dependencies after the upgrade has finished.

* `Unattended-Upgrade::Automatic-Reboot` - boolean (default:False)
 
 Automatically reboot *WITHOUT CONFIRMATION* if the file
 /var/run/reboot-required is found after the upgrade.

* `Unattended-Upgrade::Automatic-Reboot-WithUsers` - boolean (default:True)

 Automatically reboot even if users are logged in.

* `Unattended-Upgrade::Keep-Debs-After-Install` - boolean (default:False)

 Keep the downloaded deb packages after successful installs. By default
 these are removed after successful installs.

* `Acquire::http::Dl-Limit` - integer (default:0)

 Use apt bandwidth limit feature when fetching the upgrades. The
 number is how many kb/sec apt is allowed to use.

 Example - limit the download to 70kb/sec:
 ```
 Acquire::http::Dl-Limit "70";
 ```

* `Dpkg::Options` - list of strings

 Set a dpkg command-line option. This is useful to e.g. force conffile
 handling in dpkg.

 Example - force dpkg to keep the old configuration files:
 ```
 Dpkg::Options {"--force-confold"};
 ```
 Note that unattended-upgrades detects this option, and ensures that
 packages with configuration prompts will never be held back.

* `Unattended-Upgrade::Update-Days` - list of strings (default:empty)

 Set the days of the week that updates should be applied. The days
 can be specified as localized abbreviated or full names. Or as
 integers where "0" is Sunday, "1" is Monday etc.

 Example - apply updates only on Monday and Friday:
 ```
 Unattended-Upgrade::Update-Days {"Mon";"Fri"};
 ```
 The default is an empty list which means updates are applied every day.


* `Unattended-Upgrade::SyslogEnable` - boolean (default:False)

 Write events to syslog, which is useful in environments where
 syslog messages are sent to a central store.

 Example - Enable writing to syslog:
 ```
 Unattended-Upgrade::SyslogEnable true;
 ```
 The default is False - events will not be written to syslog.

* `Unattended-Upgrade::SyslogFacility` - string (default:"daemon")

 Write events to the specified syslog facility, or the daemon facility if not specified.
 Requires the `Unattended-Upgrade::SyslogEnable` option to be set to true.

 Example - Use the syslog auth facility:
 ```
 Unattended-Upgrade::SyslogFacility "auth";
 ```
 The default is the daemon facility.


![](https://github.com/mvo5/unattended-upgrades/workflows/build/badge.svg)

Unattended upgrades
===================

This script can upgrade packages automatically and unattended.  
However, it is not enabled by default.  Most users enable it via the
Software Sources program (available in System/Administration). 

If you would prefer to enable it from the command line, run 
"sudo dpkg-reconfigure -plow unattended-upgrades".

It will not install packages that require dependencies that can't be
fetched from allowed origins and it will check for conffile prompts
before the install and holds back any package that requires them. 

Setup
-----

The unattended-upgrades package is normally activated by
software-properties or via debconf. By default this runs an update
every day.

The main way to specify which packages will be auto-upgraded is by
means of their "origin" and "archive".  These are taken respectively
from the Origin and Suite fields of the respository's Release file,
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
can be configured in /etc/apt/apt.conf.d/50unattended-upgrades.
Also in this file are a range of other options that can be configured.

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

All operations are be logged in /var/log/unattended-upgrades/. This
includes the dpkg output as well. The file
/etc/logrotate.d/unattended-upgrades controls how long logfiles are
kept and how often they are rotated. See the `logrotate` manpage for
details.

If you want mail support you need to have a mail-transport-agent (e.g
postfix) or mailx installed.

Debugging
---------

If something goes wrong or if you want to report a bug about the way
the script works its a good idea to run:
```
$ sudo unattended-upgrade --debug --dry-run
```
and look at the resulting logfile in:
/var/log/unattended-upgrades/unattended-upgrades.log 
then. It will contain additional debug information.


Manual Setup
------------

To activate this script manually you need to ensure that the apt
configuration contains the following lines (this can be done via the
graphical "Software Source" program or via dpkg-reconfigure as well):
```
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
```
This means that it will check for upates every day and install them
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
 that its a list of regular expressions so you may need to escape special
 charackters like "+" as "\+".
 
 Example:
 ```
 Unattended-Upgrade::Package-Blacklist {
     "libstdc\+\+6";
 };
 ```

* `Unattended-Upgrade::Package-Whitelist` - list of regular expressions
 
 Only packages that match the regular expressions in this list will be
 marked for upgrade. By default dependencies of whitelisted packages
 are allowed. This can be changed to allow only ever allow whitelisted
 packages with the `Unattended-Upgrade::Package-Whitelist-Strict`
 boolean option.
 
 Example:
 ```
 Unattended-Upgrade::Package-Whitelist {
     "bash";
 };
 ```

* `Unattended-Upgrade::Package-Whitelist-Strict` - boolean
 
 When set, allow only packages in `Unattended-Upgrade::Package-Whitelist`
 to be upgraded. This means that you also need to list all dependencies
 of a whitelisted packages, e.g. if A depends on B and only A is
 whitelisted, it will be held back.
 
 Example:
 ```
 Unattended-Upgrade::Package-Whitelist-Strict "true";
 ```

* `Unattended-Upgrade::AutoFixInterruptedDpkg` - boolean (default:True)
 
 Run `dpkg --force-confold --configure -a` if a unclean dpkg state is
 detected. This defaults to true to ensure that updates get installed
 even when the system got interrupted during a previous run.

* `Unattended-Upgrade::MinimalSteps` - boolean (default:False)
 
 Optimize for safety against e.g. power failure by performing the upgrade
 in minimal self-contained chunks. This also allows sending a SIGINT to
 unattended-upgrades and it will stop the upgrade when it finishes the
 current upgrade step.

* `Unattended-Upgrade::InstallOnShutdown` - boolean (default:False)
 
 Perform the upgrade when the machine is shutting down instead of
 doing it in he background while the machine is running.

* `Unattended-Upgrade::Mail` - string (default:"")

 Send an email to this address with information about the packages
 upgraded. If empty or unset no email is send. This option requires
 a working local mail setup.
 
  Example:
 ```
 Unattended-Upgrade::Mail "user@example.com";
 ```

* `Unattended-Upgrade::MailOnlyOnError` - boolean (default:False)
 
 Only generate a email if some problem occured during the 
 unattended-upgrades run.

* `Unattended-Upgrade::Remove-Unused-Dependencies` - boolean (default:False)
 
 Remove all new unused dependencies after the upgrade finished.

* `Unattended-Upgrade::Automatic-Reboot` - boolean (default:False)
 
 Automatically reboot *WITHOUT CONFIRMATION* if the file
 /var/run/reboot-required is found after the upgrade.

* `Acquire::http::Dl-Limit` - integer (default:0)

 Use apt bandwidth limit feature when fetching the upgrades. The
 number is how many kb/sec apt is allowed to use

 Example - limit the download to 70kb/sec:
 ```
 Acquire::http::Dl-Limit "70";
 ```


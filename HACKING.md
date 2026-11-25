Hacking on unattended-upgrades
==============================

Hacking on unattended-upgrades should be straightforward.
If you plan to fix bugs or add features, please consider
adding tests.

Running tests
-------------

Please run:

    $ PYTHONPATH=. python3 -m unittest

Or

	$ PYTHONPATH=. python3 -m pytest

Changing the 50unattended-upgrades templates
--------------------------------------------

The files `data/50unattended-upgrades.*` are installed as
`/etc/apt/apt.conf.d/50unattended-upgrades` and managed by ucf. Any
change to them, including a comment-only change such as a typo fix,
makes ucf prompt every user who has edited their copy of the file on the
next package upgrade. Avoid cosmetic-only changes to these templates and
fold them into the next functional change instead.

Every change to a template also needs its new md5sum added to
`data/50unattended-upgrades.md5sum`, otherwise the Debian package build
fails for a release.

Only the sums of templates that were shipped in a release are needed.
The sums of the release in development live below a `# <version>`
comment at the end of the file and are regenerated, not appended to, so
that intermediate states of the templates do not pile up. Replace them
with (use the version of the next release):

    $ sed -i '/^# 2.15$/q' data/50unattended-upgrades.md5sum
    $ md5sum data/50unattended-upgrades.* | grep -v md5sum | cut -d" " -f1 \
        | while read sum; do \
            grep -q $sum data/50unattended-upgrades.md5sum \
                || echo $sum >> data/50unattended-upgrades.md5sum; \
          done

The first template change after a release adds the comment for the next
version. Do not add blank lines or repeat a comment, the package build
rejects duplicate lines.

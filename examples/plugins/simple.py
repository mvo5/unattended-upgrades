import json


# Note the plugin name must start with UnattendedUpgradesPlugin*
# Copy the file into any of:
#
#     /etc/unattended-upgrades/plugins/
#     /usr/share/unattended-upgrades/plugins
#
# or modify UNATTENDED_UPGRADES_PLUGIN_PATH to use a custom location.
class UnattendedUpgradesPluginExample:
    """Example plugin for unattended-upgrades"""

    def postrun(self, result):
        """
        The postrun function is run after an unattended-upgrades run
        that generated some result. The result is a dict that is
        kept backward compatible.
        """
        # The data in result is a python class called PluginDataPostrun.
        # It can be viewed via "pydoc3 /usr/bin/unattended-upgrades"
        # and then searching for PluginDataPostrun.
        #
        # It also acts as a simple python dict that can easily
        # be serialized to json. It contains information like what
        # packages got upgraded, removed and kept back. Also the
        # full u-u log and the dpkg log (if any).
        #
        # Here an example that serialized the data as json to a file
        with open("simple-example-postrun-res.json", "w") as fp:
            json.dump(result, fp)

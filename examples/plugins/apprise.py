"""
This plugin uses the apprise python module to allow sending
the output of u-u in json format to almost any webhook you want.

You may configure parts of this plugin by using the following
variables which should be placed in /etc/apt/apt.conf.d/51uu-apprise.

<code>
// Webhooks
// Enable Webhooks: true, false
//Unattended-Upgrade::Webhook "false";

// Where do you want to send the json?
//Unattended-Upgrade::WebhookUrl {
//  "";
//  "";
//};

// When for the webhook to execute
// Set this value to one of: "always", "only-on-error" or "on-change"
//Unattended-Upgrade::WebhookReport "only-on-error";

// Set character limit for the JSON payload
// Default: 2000; If set to 0 there is no limit.
//Unattended-Upgrade::WebhookCharacterLimit 2000;
</code>

"""

import apt_pkg
import json
import logging
import logging.handlers
logged_msgs = set()  # type: AbstractSet[str]

def log_once(msg):
    # type: (str) -> None
    global logged_msgs
    if msg not in logged_msgs:
        logging.info(msg)
        logged_msgs.add(msg)  # type: ignore

try:
    import apprise
except NameError:
    log_once(_("Notifiying Webhook is skipped. Please "
               "install the python module apprise to send webhooks."))

# Note the plugin name must start with UnattendedUpgradesPlugin*
class UnattendedUpgradesPluginApprise:
    """Apprise plugin for unattended-upgrades"""

    def __init__(self):
        self.webhooks = self.get_webhookurls()
        self.charlimit = self.get_charlimit()
        self.reporttype = self.get_reporttype()
        self.is_enabled = self.get_enabled()

    def postrun(self, result):
        """
        The postrun function is run after an unattended-upgrades run
        that generated some result. The result is a dict that is
        kept backward compatible.
        """
        # The data in result is a simple python dict that can easily
        # be serialized to json. It contains information like what
        # packages got upgraded, removed and kept back. Also the
        # full u-u log and the dpkg log (if any).

        if self.is_enabled:
            self.send_summary_webhook(result)

    def get_reporttype(self):
        """
        Returns the value from Unattended-Upgrade::WebhookReport
        If the value does not exist or its a value it does not recognize
        it returns 'only-on-error'
        Default: only-on-error
        """
        val = apt_pkg.config.find("Unattended-Upgrade::WebhookReport",
                                  "only-on-error")
        if val in ['always', 'only-on-error', 'on-change']:
            return val
        else:
            return "only-on-error"

    def get_enabled(self):
        """
        Boolean enables or disables this plugin
        Default: disabled == False
        """
        return apt_pkg.config.find_b("Unattended-Upgrade::Webhook", False)

    def get_charlimit(self):
        """
        Set a character limit for the payload.
        Default: 2000
        """
        return int(apt_pkg.config.find("Unattended-Upgrade::WebhookCharacterLimit", "2000"))

    def get_webhookurls(self):
        """ Return a list of webhook urls from apt.conf
        """
        webhook_urls = []
        key = "Unattended-Upgrade::WebhookUrl"
        try:
            # apt_pkg.config.value_list(key): returns two of the same value.
            # work around make the list a set to make the urls unique.
            for s in set(apt_pkg.config.value_list(key)):
                webhook_urls.append(s)
        except ValueError:
            logging.error(_("Unable to parse %s." % key))
            raise
        return webhook_urls

    def create_payload(self, data):
        """
        Create the payload that will put into the webhook
        Usually this is just a string with information
        """
        # This is a weak attempt at ensuring we can send something to the webhook
        # in case we go over a character limit.
        if (len(str(data)) > self.charlimit) and (self.charlimit > 0):
            # Replacing data['log_dpkg'] and data['log_unattended_upgrades']
            # It's more likely the character limit will be met
            data['log_dpkg'] = "R"
            data['log_unattended_upgrades'] = "R"
            payload = json.dumps(data)

            # If we are still above the limit set by the user: stop and log the failure.
            # It is up to the user to set a reasonable value.
            # The default value is meant to be reasonable for most use cases.
            if len(payload) > self.charlimit:
                log_once(_("Notifiying Webhook is skipped. Please "
                           "set the character limit to higher value."))
                return False
            else:
                return payload

        else:
            return json.dumps(data)

    def webhook_notify(self, data):
        payload = self.create_payload(data)

        if payload:
            # Create an Apprise instance
            apobj = apprise.Apprise()

            # Add all of the notification services by their server url.
            for url in self.webhooks:
                apobj.add(url)

            # Then notify these services any time you desire. The below would
            # notify all of the services loaded into our Apprise object.
            apobj.notify(
                body=payload,
                title='Unattended-Upgrades',
            )
        else:
            # TODO 20230105 Maybe we want to actually do something if its false
            pass

    def send_summary_webhook(self, data):
        # If webhook is not enabled or there is no webhook url, exit here
        if (not self.is_enabled) or (not self.webhooks):
            return

        # If the operation was successful and the user has requested to get
        # webhooks only on errors, just exit here
        if (data['success'] and (self.reporttype == "only-on-error")):
            return

        # If the run was successful but nothing had to be done skip sending the webhook
        # unless the admin wants it anyway
        if (((self.reporttype != "always") and data['success']
                and not data['packages_upgraded']
                and not data['packages_kept_back']
                and not data['packages_kept_installed']
                and not data['reboot_required'])):
            return

        # Notify webhook
        self.webhook_notify(data)

#    * "plugin_api": the API version as string of the form "1.0"
#    * "hostname": The hostname of the machine that run u-u.
#    * "success": A boolean that indicates if the run was successful
#    * "result": A string with a human readable (and translated) status message
#    * "packages_upgraded": A list of packages that got upgraded.
#    * "packages_kept_back": A list of packages kept back.
#    * "packages_kept_installed": A list of packages not auto-removed.
#    * "reboot_required": Indicates a reboot is required.
#    * "log_dpkg": The full dpkg log output.
#    * "log_unattended_upgrades": The full unattended-upgrades log.


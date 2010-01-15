#!/usr/bin/python

import logging
import sys
from unattended_upgrade import conffile_prompt


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    test_pkg = sys.argv[1]
    has_conffile_prompt = conffile_prompt(test_pkg)
    logging.debug("will have conf file prompt: %s" % has_conffile_prompt)

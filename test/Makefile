#!/usr/bin/make

all: check

test-packages:
	$(MAKE) -C packages

check: test-packages
	#PYTHONPATH=.. python3 -m unittest
	PYTHONPATH=.. python3 -m coverage run -a -m unittest

clean:
	$(MAKE) -C packages clean
	rm -rf ./aptroot/var/cache/
	rm -rf ./aptroot/var/lib/apt
	rm -rf ./aptroot/var/run
	find .. -type d -name __pycache__ | xargs rm -rf

coverage-html:
	python3 -m coverage html

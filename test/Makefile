#!/usr/bin/make

all: check

check:
	set -e; \
	find . -name 'test_*.py' | \
	while read file; do \
	    if [ -x $$file ]; then \
		echo "Running $$file"; \
	    	python3 $$file ; \
	    fi \
	done

clean:
	rm -rf ./aptroot/var/cache/
	rm -rf ./aptroot/var/lib/apt
	rm -rf ./aptroot/var/run


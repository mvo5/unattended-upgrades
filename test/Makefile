#!/usr/bin/make

all: check

check:
	find . -name 'test_*.py' | \
	while read file; do \
	    if [ -x $$file ]; then \
	    	python $$file ; \
	    fi \
	done

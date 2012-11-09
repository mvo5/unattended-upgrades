#!/usr/bin/make

all: check

check:
	# test with both py2 and py3 for now and also use coverage for the py2
	set -e; \
	find . -name 'test_*.py' | \
	while read file; do \
	    if [ -x $$file ]; then \
		echo "Running $$file with python3"; \
	    	python3 $$file 2>&1; \
		echo "Running $$file with python"; \
		python-coverage run -a $$file 2>&1; \
	    fi \
	done

clean:
	rm -rf ./aptroot/var/cache/
	rm -rf ./aptroot/var/lib/apt
	rm -rf ./aptroot/var/run
	find .. -type d -name __pycache__ | xargs rm -rf

coverage-html:
	echo "output in htmlcov/
	python-coverage html

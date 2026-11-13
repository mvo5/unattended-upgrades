DEBS = $(patsubst %.equivs,%.deb,$(wildcard *.equivs))

# conf-test-package_1.0.deb repacked with its data.tar members stored as
# "etc/..." instead of "./etc/...", as some third-party tools write them
# (GH: #426)
NO_DOT_PREFIX = conf-test-package-no-dot-prefix_1.0.deb

all: $(DEBS) $(NO_DOT_PREFIX)

%.deb: %.equivs
	equivs-build $<
	@echo " Conffiles:"
	dpkg-deb -I $@ conffiles

$(NO_DOT_PREFIX): conf-test-package_1.0.deb
	rm -rf no-dot-prefix.tmp && mkdir -p no-dot-prefix.tmp/data
	cd no-dot-prefix.tmp && ar x ../$< \
	    && tar -C data -xzf data.tar.gz && rm data.tar.gz \
	    && (cd data && tar -czf ../data.tar.gz --owner=0 --group=0 *) \
	    && ar rc ../$@ debian-binary control.tar.gz data.tar.gz
	rm -rf no-dot-prefix.tmp

clean:
	rm -f $(DEBS) $(NO_DOT_PREFIX) *.buildinfo *.changes

.PHONY: clean

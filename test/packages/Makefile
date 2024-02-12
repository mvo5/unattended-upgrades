DEBS = $(patsubst %.equivs,%.deb,$(wildcard *.equivs))

all: $(DEBS)

%.deb: %.equivs
	equivs-build $<
	@echo " Conffiles:"
	dpkg-deb -I $@ conffiles

clean:
	rm -f $(DEBS) *.buildinfo *.changes

.PHONY: clean

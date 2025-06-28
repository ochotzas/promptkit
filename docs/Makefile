# Documentation Makefile

# You can set these variables from the command line
SPHINXBUILD   = sphinx-build
SOURCEDIR     = .
BUILDDIR      = _build

help:
	@echo "Please use \`make <target>\` where <target> is one of"
	@echo "  html       to make standalone HTML files"
	@echo "  clean      to clean the build directory"
	@echo "  livehtml   to run autobuild for development"

html:
	$(SPHINXBUILD) -b html $(SOURCEDIR) $(BUILDDIR)/html
	@echo
	@echo "Build finished. The HTML pages are in $(BUILDDIR)/html."

clean:
	rm -rf $(BUILDDIR)/*

livehtml:
	sphinx-autobuild $(SOURCEDIR) $(BUILDDIR)/html

.PHONY: help html clean livehtml

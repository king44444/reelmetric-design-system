.PHONY: build test clean help

help:
	@echo "Targets:"
	@echo "  make build   Compile src/*.css into dist/ (deterministic, no deps)"
	@echo "  make test    Run the test suite (installs pytest if missing)"
	@echo "  make clean   Remove build output"

build:
	python3 build/build.py

test:
	python3 -m pip install -q pytest
	python3 -m pytest tests/ -q

clean:
	rm -rf dist

.PHONY: all clean test build docs

help:
	@echo "                               _ "
	@echo "  __ _  ___ _ __   ___ _ __ __| |"
	@echo " / _\` |/ _ \ '_ \ / _ \ '__/ _\` |"
	@echo "| (_| |  __/ | | |  __/ | | (_| |"
	@echo " \__, |\___|_| |_|\___|_|  \__,_|"
	@echo " |___/                          "
	@echo ""
	@echo "Choose a command to run:"
	@echo ""
	@echo " build        		builds the wheel and sdist"
	@echo " install      		installs the package in the current environment"
	@echo " install-dev  		installs the package in editable mode with all dev dependencies"
	@echo " test         		runs the tests"
	@echo " format       		runs black and isort"
	@echo " lint         		runs the linters"
	@echo " type-check   		runs mypy"
	@echo " check        		runs all checks"
	@echo " docs         		builds the documentation"
	@echo " clean        		cleans the build artifacts"
	@echo " data         		downloads and builds the latest timezone data"
	@echo " flatbuf      		(re-)compiles the flatbuffer schema"
	@echo " speedtest      	runs the speedtests"


# makes the venv available to the make commands
VIRTUAL_ENV ?= $(shell poetry env info --path)
PATH := $(VIRTUAL_ENV)/bin:$(PATH)


all: install

install:
	pip install .[all]

install-dev:
	pip install -e .[all,dev,test,docs]

test:
	pytest

format:
	black .
	isort .

lint:
	# stop the build if there are Python syntax errors or undefined names
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	# exit-zero treats all errors as warnings. The GitHub editor is 127 chars wide
	flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

type-check:
	mypy .

check: lint test type-check

clean:
	rm -rf timezonefinder.egg-info
	rm -rf dist
	rm -rf build
	rm -rf .cache
	rm -rf .pytest_cache
	rm -rf .mypy_cache

build: clean
	python3 -m build

flatbuf:
	@flatc --python --gen-mutable timezonefinder/flatbuf/polygon_schema.fbs
	@flatc --python --gen-mutable timezonefinder/flatbuf/shortcut_schema.fbs
	@flatc --python --gen-mutable timezonefinder/flatbuf/hex_zone_schema.fbs

data:
	./parse_data.sh

docs:
	$(MAKE) -C docs clean
	$(MAKE) -C docs html

speedtest:
	pytest scripts/check_speed_timezone_finding.py

.PHONY: clean test build docs
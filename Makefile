SHELL := /bin/bash
PATH := $(PWD)/env/bin:$(PATH)
python_version := 2.6
cov_report := html
pip_args :=

.PHONY: test clean

env:
ifndef local_env
	PATH=/usr/bin/:/usr/local/bin virtualenv env --no-site-packages -p python$(python_version)
	env/bin/pip install -U setuptools $(pip_args)
	env/bin/pip install -U pip $(pip_args)
endif

develop: env
	test -a paylogic/settings_local.py || cp paylogic/settings_local_example.py paylogic/settings_local.py
	pip install -r requirements-testing.txt $(pip_args)
	pip install -r requirements.txt $(pip_args)
ifndef skip_syncdb
	python manage.py syncdb
endif

test: env
	pip install tox
	tox --recreate

coverage: develop
	py.test --cov=paylogic --cov=codereview --cov-report=$(cov_report) tests

coveralls:
	pip install python-coveralls
	make coverage cov_report=term-missing skip_syncdb=1
	coveralls

clean:
	-rm -rf ./build

build: clean
	mkdir -p ./build
	echo "`git rev-parse --abbrev-ref HEAD`: `git rev-parse HEAD`" > ./build/VERSION
	pip install -r requirements.txt --target=./build $(pip_args)
	cp -R codereview paylogic *.py rietveld_helper static templates ./build/
	cd build; python manage.py collectstatic --noinput --settings=paylogic.settings_build

dependencies:
	sudo apt-get install `cat DEPENDENCIES* | grep -v '#'`

WHEEL_DIR=$(HOME)/.pip/wheels
DOWNLOAD_CACHE_DIR=$(HOME)/.pip/downloads
SHELL := /bin/bash
PATH := $(PWD)/env/bin:$(PATH)
python_version := 2.6
cov_report := html
index_url := https://pypi.python.org/simple/
extra_index_url := $(index_url)
wheel_args := --use-wheel
pip_args := $(wheel_args) --index-url=$(index_url) --extra-index-url=$(extra_index_url) --allow-all-external --download-cache "$(DOWNLOAD_CACHE_DIR)"

.PHONY: test clean

env:
ifndef local_env
	PATH=/usr/bin/:/usr/local/bin virtualenv env --no-site-packages -p python$(python_version)
	env/bin/pip install -U pip wheel --index-url=$(index_url) --extra-index-url=$(extra_index_url)
	env/bin/pip install -U setuptools --index-url=$(index_url) --extra-index-url=$(extra_index_url)
	env/bin/pip install -U devpi-client==2.0.3 --index-url=$(index_url) --extra-index-url=$(extra_index_url)
endif

develop: env
	test -a paylogic/settings_local.py || cp paylogic/settings_local_example.py paylogic/settings_local.py
	pip install -r requirements-testing.txt $(pip_args)
	pip install -r requirements.txt $(pip_args)
ifndef skip_syncdb
	python manage.py syncdb
	python manage.py collectstatic --noinput
endif

test: env
	pip install tox
	tox --recreate -vv

coverage: develop
	py.test --cov=paylogic --cov=codereview --cov-report=$(cov_report) tests

coveralls:
	pip install python-coveralls
	make coverage cov_report=term-missing skip_syncdb=1
	coveralls

clean:
	-rm -rf ./env ./build /tmp/pip_build_root

build: clean env
	mkdir -p ./build
	echo "`git rev-parse --abbrev-ref HEAD`: `git rev-parse HEAD`" > ./build/VERSION
	pip install -r requirements.txt --target=./build $(pip_args)
	cp -R codereview paylogic *.py rietveld_helper static templates ./build/
	cd build; python manage.py collectstatic --noinput --settings=paylogic.settings_build

dependencies:
	sudo apt-get install `cat DEPENDENCIES* | grep -v '#'` -y

wheel: clean env
	$(eval pip_args := --no-use-wheel --index-url=$(index_url) --extra-index-url=$(extra_index_url) --allow-all-external)
	rm -rf $(DOWNLOAD_CACHE_DIR)
	rm -rf $(WHEEL_DIR)
	mkdir -p $(DOWNLOAD_CACHE_DIR)
	pip wheel -w "$(WHEEL_DIR)" -r requirements-testing.txt $(pip_args)
	for x in `ls "$(DOWNLOAD_CACHE_DIR)/"| grep \.whl` ; do \
		-mv "$$x" "$(WHEEL_DIR)/$${x$(pound)$(pound)*%2F}"; done
	-rm -rf $(WHEEL_DIR)/Django-* # django of early versions doesn't work out of the box with wheels

upload-wheel: wheel
	devpi use $(devpi_url)
	devpi use $(devpi_path)
	devpi login $(devpi_login) --password=$(devpi_password)
	devpi upload --no-vcs --formats=bdist_wheel $(WHEEL_DIR)/*

PY ?= python3

.PHONY: ci test compile help

ci:
	$(PY) --version
	$(PY) -m compileall scripts
	$(PY) -m unittest discover -s scripts -t scripts -p "test_*.py" -v

test:
	$(PY) -m unittest discover -s scripts -t scripts -p "test_*.py" -v

compile:
	$(PY) -m compileall scripts

help:
	@echo "Targets: ci (version + compileall + unittest discover scripts/test_*.py), test, compile"

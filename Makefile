.SILENT:

.PHONY: wget-repo-db default prepare-repo pprecheck mypy pylint \
	format-check format

default: prepare-repo

wget-repo-db:
	wget https://repo-1.dds.pizza/repo.db -P _ports-repo

precheck: pylint mypy format-check

mypy:
	echo Checking with mypy...
	poetry run mypy dds_ports/ ports/
	echo Checking with mypy... OK

pylint:
	echo Checking with pylint...
	poetry run pylint -rno dds_ports ports/
	echo Checking with pylint... OK

format-check:
	echo Checking code formatting...
	poetry run yapf --diff --recursive  dds_ports/ ports/
	echo Checking code formatting... OK

format:
	poetry run yapf --in-place --recursive dds_ports/ ports/

prepare-repo:
	poetry run dds-ports-mkrepo \
		--ports-dir=ports/ \
		--repo-dir=_ports-repo/

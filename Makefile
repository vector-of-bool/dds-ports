.SILENT:

.PHONY: wget-repo-db default prepare-repo pprecheck mypy pylint \
	format-check format

default: prepare-repo

init-repo:
	./bpt repo init _ports-repo --name repo-2.dds.pizza --if-exists=ignore

wget-repo-db:
	mkdir -p _ports-repo
	wget https://repo-2.dds.pizza/repo.db -O _ports-repo/repo.db || \
		$(MAKE) init-repo

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

prepare-repo: init-repo
	poetry run dds-ports-mkrepo \
		--ports-dir=ports/ \
		--repo-dir=_ports-repo/

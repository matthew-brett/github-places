update-repos:
	git submodule update --init --recursive
	python scripts/update_repos.py

MIN_COMMITS = 25

update-gh-user-map:
	python find_gh_users.py --start-from=LAST --min-commits=$(MIN_COMMITS)

update-repos:
	git submodule update --init --recursive
	python scripts/update_repos.py

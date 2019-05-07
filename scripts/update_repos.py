#!/usr/bin/env python
""" Update repositories
"""

import sys
from os.path import join as pjoin, abspath, dirname
from subprocess import check_call

sys.path.append(abspath(pjoin(dirname(__file__), '..')))

from gputils import ORGS_REPOS

for org, repo in ORGS_REPOS:
    url = f'https://github.com/{org}/{repo}'
    check_call(f'(cd {repo} && git remote set-url origin {url})', shell=True)
    check_call(f'(cd {repo} && git remote -v)', shell=True)
    check_call(f'(cd {repo} && git fetch origin)', shell=True)

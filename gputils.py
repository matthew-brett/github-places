""" Utilities for github places processing.
"""

import requests
import json

from github3 import login

GRAPHQL_URL = 'https://api.github.com/graphql'

ORGS_REPOS = (
    ('numpy', 'numpy'),
    ('scipy', 'scipy'),
    ('matplotlib', 'matplotlib'),
    ('scikit-learn', 'scikit-learn'),
    ('scikit-image', 'scikit-image'),
    ('statsmodels', 'statsmodels'),
    ('pandas-dev', 'pandas'),
    ('h5py', 'h5py'),
    ('cython', 'cython'),
    ('sympy', 'sympy'),
)

REPO2ORG = {repo: org for org, repo in ORGS_REPOS}

GH_TOKEN_FNAME = '.gh_token'


def get_gh_token(fname):
    with open(fname, 'rt') as fobj:
        for line in fobj:
            line = line.strip()
            if line == '' or line.startswith('#'):
                continue
            return line


GH_TOKEN = get_gh_token(GH_TOKEN_FNAME)
GH = login(token=GH_TOKEN)


def get_repo(repo_name):
    return GH.repository(REPO2ORG[repo_name], repo_name)


def graphql_query(query, token=None):
    token = token if token else GH_TOKEN
    headers = {'Authorization': f'token {GH_TOKEN}'}
    answer = requests.post(url=GRAPHQL_URL,
                           json={'query': query},
                           headers=headers)
    return json.loads(answer.text)



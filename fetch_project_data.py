""" Get repository data for projects, write as JSON

Usage:

    python fetch_project_data.py my-gh-username my-gh-password

The project data is all public, but you'll need your Github credentials to
overcome the rate limits on anonymous queries.
"""

import sys
import json
import math

import github3


PROJECTS = (
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


class GHGetter:

    def __init__(self, username, passwd):
        self.username = username
        self.passwd = passwd
        self.GH = github3.GitHub(username, passwd)

    def get_repo(self, org_name, repo_name):
        org = self.GH.organization(org_name)
        matches = [r for r in org.repositories() if r.name == repo_name]
        if len(matches) == 1:
            return matches[0]
        raise ValueError(
            f'Could not find repository {repo_name} in org {org_name}')

    def repo_to_dict(self, repo, n_users=20):
        repo_dict = repo.as_dict()
        repo_dict['contributors'] = {}
        last_contrib = math.inf
        contrib_gen = repo.contributors()
        for c_no in range(n_users):
            c = next(contrib_gen)
            assert c.contributions <= last_contrib
            last_contrib = c.contributions
            c_dict = c.as_dict()
            c_dict['user'] = self.GH.user_with_id(c.id).as_dict()
            repo_dict['contributors'][c.login] = c_dict
        return repo_dict

    def save_json(self, repos, fname):
        repos_d = {}
        for repo in repos:
            repos_d[repo.name] = self.repo_to_dict(repo)
        with open(fname, 'wt') as fobj:
            json.dump(repos_d, fobj)


def get_save_repos(projects, username, passwd):
    gg = GHGetter(username, passwd)
    repos = [gg.get_repo(*params) for params in projects]
    gg.save_json(repos, 'projects.json')
    return repos


def main():
    get_save_repos(PROJECTS, *sys.argv[1:3])


if __name__ == '__main__':
    main()

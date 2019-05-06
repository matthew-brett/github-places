""" Get repository data for projects, write as JSON

Usage:

    python fetch_project_data.py my-gh-username my-gh-password out.json

The project data is all public, but you'll need your Github credentials to
overcome the rate limits on anonymous queries.
"""

import sys
import json
import math
from argparse import ArgumentParser

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
        return self.GH.repository(org_name, repo_name)

    def get_userdata(self, contrib):
        c_dict = contrib.as_dict()
        user = self.GH.user(contrib.login)
        u_dict = user.as_dict()
        u_dict['commit_email'] = None
        c_dict['user'] = u_dict
        return c_dict

    def repo_to_dict(self, repo, n_commits=50):
        repo_dict = repo.as_dict()
        repo_dict['contributors'] = {}
        last_contrib = math.inf
        contrib_gen = repo.contributors()
        while True:
            c = next(contrib_gen)
            if c.contributions < n_commits:
                break
            assert c.contributions <= last_contrib
            assert c.type == 'User'
            last_contrib = c.contributions
            repo_dict['contributors'][c.login] = self.get_userdata(c)
        return repo_dict

    def save_json(self, repos, fname, n_commits):
        repos_d = {}
        for repo in repos:
            repos_d[repo.name] = self.repo_to_dict(repo, n_commits)
        with open(fname, 'wt') as fobj:
            json.dump(repos_d, fobj)

    def _query2user(self, query):
        iterator = self.GH.search_commits(query)
        try:
            commit = next(iterator)
        except (TypeError, StopIteration):
            return None
        return commit.author.login

    def email2user(self, email):
        user = self._query2user(f'author-email:{email}')
        return user if user else self._query2user(f'committer-email:{email}')


def get_save_repos(projects, username, passwd,
                   out_fname, n_commits=50):
    gg = GHGetter(username, passwd)
    repos = [gg.get_repo(*params) for params in projects]
    gg.save_json(repos, out_fname, n_commits=n_commits)
    return repos


def main():
    parser = ArgumentParser()
    parser.add_argument(
        "gh_user", help="Github username")
    parser.add_argument(
        "gh_passwd", help="Github password")
    parser.add_argument(
        "output", help="Path for output file")
    parser.add_argument(
        "-n", "--n-commits", type=int,
        help="Minimum mumber of commits")
    args = parser.parse_args()
    get_save_repos(PROJECTS,
                   args.gh_user,
                   args.gh_passwd,
                   args.output,
                   args.n_commits)


if __name__ == '__main__':
    main()

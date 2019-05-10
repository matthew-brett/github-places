""" Utilities for github places processing.
"""

from os.path import abspath
import requests
import json
import re
from subprocess import check_output
from collections import namedtuple, OrderedDict, Counter
from datetime import datetime

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


def get_repo(repo_name, org=None):
    org = org if org else REPO2ORG[repo_name]
    return GH.repository(org, repo_name)


def graphql_query(query, token=None):
    token = token if token else GH_TOKEN
    headers = {'Authorization': f'token {GH_TOKEN}'}
    answer = requests.post(url=GRAPHQL_URL,
                           json={'query': query},
                           headers=headers)
    return json.loads(answer.text)



def ordered_unique(sequence, out=None):
    out = [] if out is None else list(out)
    for e in sequence:
        if e not in out:
            out.append(e)
    return tuple(out)


class RepoContributor:

    # Number of PRs to try when searching for GH user
    n_prs = 10

    def __init__(self, commits, repo, gh_user=None):
        self.commits = commits
        self.repo = repo
        self.gh_user = gh_user

    def __eq__(self, other):
        return (self.commits == self.commits)

    @property
    def name(self):
        return self.names[0]

    @property
    def email(self):
        return self.emails[0]

    @property
    def names(self):
        names = ordered_unique(c.c_name for c in self.commits)
        return ordered_unique([c.o_name for c in self.commits], names)

    @property
    def emails(self):
        emails = ordered_unique(c.c_email for c in self.commits)
        return ordered_unique([c.o_email for c in self.commits], emails)

    @property
    def timezone_counts(self):
        timezones = [c.dt.tzname() for c in self.commits]
        unique = ordered_unique(timezones)
        return tuple((tz, timezones.count(tz)) for tz in unique)

    @property
    def shas_by_email(self):
        shas_emails = OrderedDict()
        for email in self.emails:
            shas = [c.sha for c in self.commits if c.o_email == email]
            if shas:
                shas_emails[email] = shas
        return shas_emails

    def shas2gh_user(self):
        for shas in self.shas_by_email.values():
            gh_user = sha2gh_user(shas[0], self.repo.gh_repo)
            if gh_user:
                return gh_user

    def sha_prs2gh_user(self, n_prs=None, token=None):
        # Try tracking PRs for commits.
        # Try a few PRs for each email address
        n_prs = self.n_prs if n_prs is None else n_prs
        author_shas = tuple(c.sha for c in self.commits)
        repo = self.repo.gh_repo
        for shas in self.shas_by_email.values():
            for i in range(self.n_prs):
                # Modifies shas in-place
                pr = track_pr(shas, repo, author_shas, token)
                if len(shas) == 0:
                    break
                elif pr:
                    return pr.user.login

    def guess_gh_user(self, n_prs=None, token=None):
        """ Guess Github user from various data sources

        Parameters
        ----------
        n_prs : None or int, optional
            Number of pull-requests to interrogate for Github user.  Default
            None gets value from class attribute.
        token : None or str, optional
            Github token for authentication.  Default is to read from local
            `.gh_token` file.

        Returns
        -------
        gh_user : str or None
            Found Github user name, or None if no certain match found.

        Notes
        -----

        Algorithm:

        * If any contributor email is a Github no-reply email, it gives the
          Github user name, otherwise:
        * Query on Github for commit SHA of most recent commit matching each email
          to see whether it gives a username, otherwise:
        * Go through SHAs for each email, to find matching Pull Request (PR)
          on Github. If all commits for that PR match one a commit from this
          contributor, return Github user of PR, otherwise:
        * Repeat step above nine times (by default) to look for more PRs,
          otherwise:
        * Return None
        """
        # Look for a github email address
        gh_user = emails2gh_user(self.emails)
        if gh_user:
            return gh_user
        # Search for login attached to most recent SHA for each email address
        gh_user = self.shas2gh_user()
        if gh_user:
            return gh_user
        return self.sha_prs2gh_user(n_prs, token)

    def __len__(self):
        return len(self.commits)


def parse_sl_line(line):
    fields = re.split(r'\|\|', line.strip())
    fields[-1] = datetime.fromisoformat(fields[-1])
    return Commit(*fields)


Commit = namedtuple('Commit', ('sha', 'c_name', 'c_email', 'o_name', 'o_email',
                               'dt'))


def parse_shortlog(output):
    res = re.split(r'^.*\s+\(\d+\):$', output, flags=re.M)
    contribs = []
    for auth_info in res[1:]:
        contribs.append([parse_sl_line(L) for L in auth_info.splitlines() if L])
    return contribs


def emails2gh_user(emails):
    gh_emails = [e for e in emails
                if e.endswith('@users.noreply.github.com')]
    if gh_emails:
        gh_user = gh_emails[0].split('@')[0]
        if '+' in gh_user:
            gh_user = gh_user.split('+')[1]
        return gh_user


class Repo:

    contrib_maker = RepoContributor

    def __init__(self, name, org=None, path=None):
        self.name = name
        self.org = org if org else REPO2ORG[name]
        self.path = abspath(path if path else name)
        self._gh_repo = None

    @property
    def gh_repo(self):
        self._gh_repo = (self._gh_repo if self._gh_repo else
                         get_repo(self.name, self.org))
        return self._gh_repo

    def cmd_in_repo(self, cmd):
        return check_output(cmd,
                            cwd=self.path,
                            text=True)

    def contributors(self):
        out = self.cmd_in_repo(
            ['git', 'shortlog', '-n', "--format=%H||%aN||%aE||%an||%ae||%aI"])
        parsed = parse_shortlog(out)
        return [self.contrib_maker(commits, self) for commits in parsed]


def sha2gh_user(sha, repo):
    commit = repo.commit(sha)
    author = commit.author
    return author.get('login') if author else None


class NoPR:
    """ Class indicates there were no PRs for this list of commits """


def track_pr(shas_to_try, repo, author_shas, token=None):
    """ Get PR from SHAs in `shas_to_try`, return GH user if visible in merge

    Reject PRs where not all commits are in full list of authors commit shas
    `author_shas`.
    """
    pr = sha2pr(shas_to_try[0], repo, token)
    if pr is None:
        shas_to_try.pop(0)
        return None
    for c in pr.commits():
        # PRs can contain commits by other authors
        if not c.sha in author_shas:
            pr = None
        if c.sha in shas_to_try:
            shas_to_try.remove(c.sha)
    return pr


def sha2pr(sha, repo, token=None):
    query = """\
{
  repository(name: "%s", owner: "%s") {
    commit: object(expression: "%s") {
      ... on Commit {
        associatedPullRequests(first:2){
          edges{
            node{
              title
              number
              body
            }
          }
        }
      }
    }
  }
}""" % (repo.name, repo.owner, sha)
    answer = graphql_query(query, token)
    prs = (answer['data']['repository']['commit']
           ['associatedPullRequests']['edges'])
    if len(prs) > 1:
        raise ValueError(f'Too many PRs for {sha}')
    return repo.pull_request(prs[0]['node']['number']) if prs else None


def gh_user2ev_emails(gh_user):
    """ Read any emails in pushes in `gh_user`'s event feed

    These can easily be someone else's commits, but it often shows the user's
    email(s).
    """
    user = GH.user(gh_user)
    emails = []
    for e in user.events():
        if e.type != 'PushEvent':
            continue
        for c in e.payload['commits']:
            emails.append(c['author'].get('email'))
    return Counter(emails)


def merge_dicts(first, second):
    """ Get keys in `second` dict missing in `first`

    Modifies `first` in-place and returns None.
    """
    for key in second:
        if key not in first:
            first[key] = second[key]


def update_subdicts(target, source):
    """ Update `target` subdict values from `source` subdict values

    Modifies `target` in-place and returns None.
    """
    for key, value in source.items():
        if not key in target:
            target[key] = value
        else:
            target[key].update(value)


def lupdate(left, right):
    """ Update values from `right` for keys present in `left`

    Modifies `left` in-place and returns None.
    """
    for key in left:
        if key in right:
            left[key] = right[key]

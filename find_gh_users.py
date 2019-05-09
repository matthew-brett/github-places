""" Find Github users for contributors to repository (or allocate fake user)

Algorithm:

* Analyze repository via git shortlog to find name, email and
  sha of commits for top N contributors.
* Look for first contribotor email in NAME2GH_USER dictionary; this contains a
  manual mapping from email to Github user.  Return user if found, otherwise:
* If any contributor email is a Github no-reply email, it gives the Github user
  name, otherwise:
* Query on Github for commit SHA of most recent commit matching each email
  to see whether it gives a username, otherwise:
* Go through SHAs for each email, to find matching Pull Request (PR) on Github.
  If all commits for that PR match one of this contributor commits, return
  Github user of PR, otherwise:
* Repeat step above nine times (by default) to look for more PRs, otherwise:
* Return None
"""

from os.path import abspath
import re
from subprocess import check_output
from collections import namedtuple, OrderedDict
from datetime import datetime

from gputils import graphql_query, get_repo, REPO2ORG


# For contributors where automated detection of Github user fails.
# Email is via mailmap from git shortlog -nse
NAME2GH_USER = {
    # https://codereclaimers.com/resume mentions Numpy / Scipy
    # and neat-python.  Leads to:
    'Alan McIntyre': 'CodeReclaimers',
    # https://www.linkedin.com/in/davidmcooke/
    # https://mail.python.org/pipermail/scipy-dev/2008-April/008873.html
    # with email cookedm@physics.mcmaster.ca
    # Probably https://twitter.com/dmcooke (location Chilliwack CAN)
    # and therefore
    # https://github.com/dmcooke (location Chilliwack CAN)
    'David M Cooke': 'dmcooke',
    'cookedm': 'dmcooke',
    # Git log shows William Spotz <wfspotz@sandia.gov@localhost> matching
    'William Spotz': 'wfspotz',
    # Log has Oscar Villellas <oscar.villellas@continuum.io>
    # https://www.linkedin.com/in/oscar-villellas-38bb241
    # has worked at Anaconda Inc (successor to Continuum).
    'Óscar Villellas Guillén': 'ovillellas',
    # I worked with Chris in Berkeley
    'Chris Burns': 'cburns',
    'Christopher Burns': 'cburns',
    # https://mail.python.org/pipermail/scipy-user/2009-March/020175.html
    # mentions PyAMG:
    # https://github.com/pyamg/pyamg/graphs/contributors
    'Nathan Bell': 'wnbell',
    # As for Numpy.
    # https://www.linkedin.com/in/pierre-g%C3%A9rard-marchant-1322a028
    'Pierre GM': 'pierregm',
    # No signs of this person
    'Matt Knox': '+matt_knox',
    # https://www.linkedin.com/in/damianeads
    # Same picture as
    # https://github.com/deads
    'Damian Eads': 'deads',
    # https://pythoncharmers.com/about
    # Linked to from:
    # https://github.com/edschofield
    'Ed Schofield': 'edschofield',
    # No Github account I can see.
    'Tom Waite': '+tom_waite',
    # https://mail.python.org/pipermail/scipy-user/2007-May/012415.html
    # Name Albert Strasheim leads to:
    # https://github.com/alberts
    # Notice Twitter handle "fullung"
    'fullung': 'alberts',
    ## Matplotlib
    # No signs I could see.
    'Steve Chaplin': '+steve_chaplin',
    # See merge commit b9bc7d16dc5c60cc83f2c9ce8866343cf3432afa
    # Merging user jrevans, with PR mixing commits, but mainly from
    # James Evans <jrevans1@earthlink.net>
    'James R. Evans': 'jrevans',
    ### Sympy
    # https://github.com/sympy/sympy/wiki/GSoC-2007-Report-Jason-Gedge:-Geometry
    # https://www.gedge.ca/about.html
    # Contributions seem to pre-date Github
    'Jason Gedge': 'thegedge',
    # https://api.github.com/users/b33j0r/events
    'Brian Jorgensen': 'b33j0r',
    ## Scikit-learn
    # PR merge commit 2b60c815a0c9467b28766eac3371f25ed3c3c7a0
    # Merge pull request #2290 from dengemann/more_ica_improvements
    # Commits are from dengemann <d.engemann@fz-juelich.de>
    'dengemann': 'dengemann',
    ## Statsmodels
    # Tim wokred on Nipy as a consultant, from Australia
    # THis Github page lists many Python skills, based in Australia.
    # http://www.timl.id.au/#skills
    'tim.leslie': 'timleslie',
    ## Cython
    # Commit 315efe4ca11f2965dbdc064cad00ee455f1296c9
    # Merge branch '_numpy' of git://github.com/dagss/cython
    # I have met Dag Sverre - Github picture matches
    'Dag Sverre Seljebotn': 'dagss',
    # https://partiallattice.wordpress.com/about
    # Gives email as
    # smith (dot) daniel (dot) br gmail (dot) com
    # and points to:
    # https://github.com/Daniel-B-Smith
    # Actuall, autodetected with current algorithm.
    'Daniel B. Smith': 'Daniel-B-Smith',
}


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
        assert len(gh_emails) == 1
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


def contributors_for(repo_name, min_commits=50):
    repo = Repo(repo_name)
    contribs = repo.contributors()
    contribs = [c for c in contribs if len(c) >= min_commits]
    for c in contribs:
        c.gh_user = NAME2GH_USER.get(c.name)
        if c.gh_user is None:
            c.gh_user = c.guess_gh_user()
    return contribs


def all_contributors():
    all_contribs = {}
    for repo_name in REPO2ORG:
        all_contribs[repo_name] = contributors_for(repo_name)
    return all_contribs


def save_all(contrib_map, fname):
    with open(fname, 'wt') as fobj:
        fobj.write('repo,name,email,gh_user\n')
        for repo_name, contribs in contrib_map.items():
            for c in contribs:
                fobj.write(
                    f'"{repo_name}","{c.name}","{c.email}","{c.gh_user}"\n')


def main():
    repo_contribs = all_contributors()
    save_all(repo_contribs, 'repo_contribs.csv')


if __name__ == '__main__':
    main()

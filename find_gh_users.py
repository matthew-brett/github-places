""" Find Github users for contributors to repository (or allocate fake user)

Algorithm:

* Analyze repository via git shortlog to find name, email and
  number of commits for top N contributors.
* Analyze repository .mailmap file, if present, for alternative emails of each
  contributor.
* Eliminate emails that are not unique to that contributor (this can happen
  when contributors have different names but the same email address).
* If any contributor email is a Github no-reply email, it gives the Github user
  name, otherwise:
* Use git to query for all commit SHAs for each candidate email.
* Query commit matching first SHA for each email on Github, to see whether it
  gives a username, otherwise:
* Go through SHAs for each email, to find matching Pull Request (PR) on Github.
  If all commits for that PR match one of this contributor's emails, or they all
  have the same contributor name, return Github user of PR, otherwise:
* Repeat step above twice (by default) to look for more PRs, otherwise:
* Look for first contribotor email in EMAIL2USER dictionary; this contains a
  manual mapping from email to Github user.  Return user if found, otherwise:
* Return modified version of contributor name, prepended with '+', to indicate
  invalid Github user.
"""

from os.path import basename, exists, join as pjoin, abspath
import re
from subprocess import check_output
from collections import defaultdict
from validate_email import validate_email
import json

import pandas as pd

from gputils import graphql_query, get_repo, REPO2ORG


NAME_EMAIL_REGEX = r'(.*?)\s+<(.*)>'


# For contributors where automated detection of Github user fails.
# Email is via mailmap from git shortlog -nse
EMAIL2USER = {
    # https://github.com/sympy/sympy/wiki/GSoC-2007-Report-Jason-Gedge:-Geometry
    # https://www.gedge.ca/about.html
    # Contributions seem to pre-date Github
    'inferno1386@gmail.com': 'thegedge',
    # https://api.github.com/users/b33j0r/events
    'brian.jorgensen@gmail.com': 'b33j0r',
    # No signs I could see.
    'stevech1097@yahoo.com.au': '+steve_chaplin',
    # https://codereclaimers.com/resume mentions Numpy / Scipy
    # and neat-python.  Leads to:
    'alan.mcintyre@local': 'CodeReclaimers',
    # https://www.linkedin.com/in/davidmcooke/
    # https://mail.python.org/pipermail/scipy-dev/2008-April/008873.html
    # with email cookedm@physics.mcmaster.ca
    # Probably https://twitter.com/dmcooke (location Chilliwack CAN)
    # and therefore
    # https://github.com/dmcooke (location Chilliwack CAN)
    'cookedm@localhost': 'dmcooke',
    # Git log shows Bill Spotz <wfspotz@sandia.gov>, matching
    'wfspotz@sandia.gov@localhost': 'wfspotz',
    # I worked with Chris
    'chris.burns@localhost': 'cburns',
    # https://mail.python.org/pipermail/scipy-user/2009-March/020175.html
    # mentions PyAMG:
    # https://github.com/pyamg/pyamg/graphs/contributors
    'wnbell@localhost': 'wnbell',
    # As for Numpy.
    # https://www.linkedin.com/in/pierre-g%C3%A9rard-marchant-1322a028
    'pierregm@localhost': 'pierregm',
    # No signs of this person
    'mattknox.ca': '+matt_knox',
    # https://www.linkedin.com/in/damianeads
    # Same picture as
    # https://github.com/deads
    'damian.eads@localhost': 'deads',
    # https://pythoncharmers.com/about
    # Linked to from:
    # https://github.com/edschofield
    'edschofield@localhost': 'edschofield',
    # No Github account I can see.
    'tom.waite@localhost': '+tom_waite',
    # https://mail.python.org/pipermail/scipy-user/2007-May/012415.html
    # Name Albert Strasheim leads to:
    # https://github.com/alberts
    # Notice Twitter handle "fullung"
    'fullung@localhost': 'alberts',
    # https://partiallattice.wordpress.com/about
    # Gives email as
    # smith (dot) daniel (dot) br gmail (dot) com
    # and points to:
    # https://github.com/Daniel-B-Smith
    'smith.daniel.br@gmail.com': 'Daniel-B-Smith',
}


class Contributor:

    def __init__(self, names, emails, repo_commits=None):
        self.names = [names] if isinstance(names, str) else list(names)
        self.emails = [emails] if isinstance(emails, str) else list(emails)
        self.repo_commits = dict(repo_commits) if repo_commits else {}

    def __eq__(self, other):
        return (self.names == self.names and
                self.emails == self.emails and
                self.repo_commits == self.repo_commits)

class Repo:

    contributor_maker = Contributor

    def __init__(self, name, org=None, path=None):
        self.name = name
        self.org = org if org else REPO2ORG[name]
        self.path = abspath(path if path else name)
        self._gh_repo = None

    @property
    def gh_repo(self):
        self._gh_repo = (self._gh_repo if self.gh_repo else
                         get_repo(self.name, self.org))
        return self._gh_repo

    def _cmd_in_repo(self, cmd):
        return check_output(cmd,
                            cwd=self.path,
                            text=True)

    def contributors(self):
        out = self._cmd_in_repo(['git', 'shortlog', '-nse'])
        lines = out.splitlines()
        for line in lines:
            match = re.match(rf'\s*(\d+)\s+{NAME_EMAIL_REGEX}', line)
            n_commits, name, email = match.groups()
            yield self.contributor_maker(name, email, {self.name: n_commits})


def find_users(repo_name):
    contributors = get_contributors(repo_name)
    canonical_map = {email: [] for (name, email, no) in contributors}
    alternative_map = get_email_map(repo_name)
    full_map = merge_maps(canonical_map, alternative_map)
    full_map = deduplicate(full_map)
    return get_usernames(full_map, repo_name)


def get_contributors(repo_path):
    out = check_output(f'(cd {repo_path} && git shortlog -nse)',
                       shell=True, text=True)
    vals = []
    for line in out.splitlines():
        match = re.match(rf'\s*(\d+)\s+{NAME_EMAIL_REGEX}', line)
        vals.append(match.groups())
    nos, names, emails = zip(*vals)
    df = pd.DataFrame()
    df['name'] = names
    df['no'] = [int(n) for n in nos]
    df['repo'] = basename(repo_path)
    df.index = emails
    return df


def _ok_address(address):
    if not validate_email(address):
        return False
    name, location = address.split('@')
    location = location.lower()
    if location in ('', 'localhost') or name == '':
        return False
    if location.endswith('.local') or location.endswith('.(none)'):
        return False
    return True


def email2shas(email, repo_dir):
    log_cmd = f'git log --use-mailmap --author={email} --format="%H"'
    return _cmd_in_repo(log_cmd, repo_dir).strip().splitlines()


def sha2login(sha, repo):
    commit = repo.commit(sha)
    author = commit.author
    return author.get('login') if author else None


def get_email_map(repo_path):
    """ Analyze ``.mailmap`` file for altnerative emails

    Parameters
    ----------
    repo_path : str
        Path to repository.

    Returns
    -------
    remapper : dict
        Dict with (key, value) pairs of (canonical email, list of alternative
        emails).
    """
    fname = pjoin(repo_path, '.mailmap')
    if not exists(fname):
        return {}
    mapper = parse_mailmap(fname)
    remapper = defaultdict(list)
    for find, replace in mapper.items():
        if replace is None:
            continue
        remapper[replace].append(find)
    return remapper


def parse_mailmap(fileish):
    """ Analyze ``.mailmap`` file `fileish`

    Parameters
    ----------
    fileish : str or file-like object
        Path to repository or file-like object implementing `read` to return
        string.

    Returns
    -------
    mapper : dict
        Dict with (key, value) pairs of (not-canonical email, canonical email).
    """
    mapper = {}
    if hasattr(fileish, 'read'):
        content = fileish.read()
    else:
        with open(fileish, 'rt') as fobj:
            content = fobj.read()
    for line in content.splitlines():
        line = line.strip()
        if line == '' or line.strip().startswith('#'):
            continue
        emails = re.findall('<(.*?)>', line)
        if len(emails) == 1:
            continue
        replace = emails[0]
        if replace not in emails:
            continue
        if len(emails) > 2:
            raise ValueError('Too many emails')
        find = emails[1]
        if not _ok_address(find):
            continue
        if find in mapper:  # Not unique to user
            mapper[find] = None
        elif find != replace:
            mapper[find] = replace
    return mapper


def get_username(to_try, email_lookup, repo, token=None, n_prs=3):
    gh_emails = [e for e in to_try
                if e.endswith('@users.noreply.github.com')]
    if gh_emails:
        assert len(gh_emails) == 1
        gh_user = gh_emails[0].split('@')[0]
        if '+' in gh_user:
            gh_user = gh_user.split('+')[1]
        return gh_user
    for email in to_try:
        if email in EMAIL2USER:
            return EMAIL2USER[email]
        if email in email_lookup:
            return email_lookup[email]
    sha_lists = [email2shas(email, repo.name) for email in to_try]
    sha_lists = [sha_list for sha_list in sha_lists if sha_list]
    # Try getting username from first commits for this email
    for sha_list in sha_lists:
        user = sha2login(sha_list[0], repo)
        if user:
            return user
    # Try tracking PRs for commits.
    for sha_list in sha_lists:
        # Try a few PRs
        for i in range(n_prs):
            # Modifies sha_list in-place
            pr = track_pr(sha_list, repo, to_try, token)
            if pr:
                return pr.user.login


class NoValue:
    """ Indicates missing value """


def pr2shas(pr):
    return [c.sha for c in pr.commits()]


def track_pr(sha_list, repo, emails, token=None):
    # Only return PR if all commits have same author name
    # Remove all PR commits from input commit list.
    pr = sha2pr(sha_list[0], repo, token)
    if pr is None:
        return
    name = NoValue
    result = pr
    for c in pr.commits():
        if c.sha in sha_list:  # PR can contain commits by other authors
            sha_list.remove(c.sha)
        if result is None:
            continue
        if name is NoValue:
            name = c.commit.author['name']
        elif not (c.commit.author['name'] == name or
                  c.commit.author['email'] in emails):
            result = None
    return result


def get_email2login(repo_data):
    lookup = {}
    for login, cdata in repo_data['contributors'].items():
        email = cdata['user']['commit_email']
        if email:
            lookup[email] = login
    return lookup


def get_usernames(emails, mapper, email_lookup, repo, token=None):
    usernames = []
    for email in emails:
        if email in EMAIL2USER:
            user = EMAIL2USER[email]
        else:
            to_try = [email] + mapper[email]
            user = get_username(to_try, email_lookup, repo, token)
        usernames.append(user)
    return usernames


def _cmd_in_repo(cmd, repo_dir):
    return check_output(f'(cd {repo_dir} && {cmd})',
                        shell=True,
                        text=True)


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


def get_user_data(org_name, repo_name, gh):
    # Get contributors
    pass


def main(repo_name, min_commits=50):
    authors = get_authors(repo_name)
    gte_50 = authors[authors['no'] >= 50]
    emails = gte_50.index
    with open('projects_50_emails.json', 'rt') as fobj:
        data = json.load(fobj)
    email_map = get_email_map(repo_name, emails)
    email2login = get_email2login(data[repo_name])
    repo = get_repo(repo_name)
    # usernames = get_usernames(emails, email_map, email2login, repo, token)
    usernames = get_usernames(emails, email_map, {}, repo)
    return usernames

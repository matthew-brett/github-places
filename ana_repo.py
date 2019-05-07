""" Analyze repository commits """

from os.path import basename, exists, join as pjoin
import re
from subprocess import check_output
from collections import defaultdict
from validate_email import validate_email
import json

import pandas as pd

from gputils import graphql_query, get_repo


NAME_EMAIL = r'(.*?)\s+<(.*)>'


# For contributors where automated detection of Github user fails.
# Email is via mailmap from git shortlog -nse
EMAIL2USER = {
    'inferno1386@gmail.com': 'thegedge',
    # https://api.github.com/users/b33j0r/events
    'brian.jorgensen@gmail.com': 'b33j0r',
    # Nothing but email to go on here
    'stevech1097@yahoo.com.au': '__steve_chaplin__',
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
    # I know Chris
    'chris.burns@localhost': 'cburns',
    # https://mail.python.org/pipermail/scipy-user/2009-March/020175.html
    # mentions PyAMG:
    # https://github.com/pyamg/pyamg/graphs/contributors
    'wnbell@localhost': 'wnbell',
    # As for Numpy.
    # https://www.linkedin.com/in/pierre-g%C3%A9rard-marchant-1322a028
    'pierregm@localhost': 'pierregm',
    # No signs of this person
    'mattknox.ca': '__matt_knox__',
    # https://www.linkedin.com/in/damianeads
    # Same picture as
    # https://github.com/deads
    'damian.eads@localhost': 'deads',
    # https://pythoncharmers.com/about
    # Linked to from:
    # https://github.com/edschofield
    'edschofield@localhost': 'edschofield',
    # No Github account I can see
    'tom.waite@localhost': '__tom_waite__',
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


def get_authors(repo_path):
    out = check_output(f'(cd {repo_path} && git shortlog -nse)',
                       shell=True, text=True)
    vals = []
    for line in out.splitlines():
        match = re.match(rf'\s*(\d+)\s+{NAME_EMAIL}', line)
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


def get_email_map(repo_path, emails):
    mailmap_fname = pjoin(repo_path, '.mailmap')
    mapper = {}
    if not exists(mailmap_fname):
        return mapper
    with open(mailmap_fname, 'rt') as fobj:
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
    remapper = defaultdict(list)
    for find, replace in mapper.items():
        if replace is None:
            continue
        remapper[replace].append(find)
    return remapper


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

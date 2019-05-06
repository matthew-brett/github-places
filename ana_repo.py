""" Analyze repository commits """

from os.path import basename, exists, join as pjoin
import re
import requests
from subprocess import check_output
from collections import defaultdict
from validate_email import validate_email
import json

import pandas as pd

import github3

GRAPHQL_URL = 'https://api.github.com/graphql'

NAME_EMAIL = r'(.*?)\s+<(.*)>'


# For contributors where automated detection of Github user fails.
# Email is via mailmap from git shortlog -nse
EMAIL2USER = {
    'inferno1386@gmail.com': 'thegedge',
    # https://api.github.com/users/b33j0r/events
    'brian.jorgensen@gmail.com': 'b33j0r',
    # Nothing but email to go on here
    'stevech1097@yahoo.com.au': '__steve_chaplin__',
}


def get_gh_token(fname='.gh_token'):
    with open(fname, 'rt') as fobj:
        return next(fobj).strip()


def get_gh(fname='.gh_token'):
    return github3.login(token=get_gh_token(fname))


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


def email2sha(email, repo_dir):
    log_cmd = f'git log -1 --use-mailmap --author={email} --format="%H"'
    out = _cmd_in_repo(log_cmd, repo_dir).strip()
    return out if out else None


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


def get_username(to_try, email_lookup, repo, token):
    gh_emails = [e for e in to_try
                if e.endswith('@users.noreply.github.com')]
    if gh_emails:
        assert len(gh_emails) == 1
        return gh_emails[0].split('@')[0]
    for email in to_try:
        if email in EMAIL2USER:
            return EMAIL2USER[email]
        if email in email_lookup:
            return email_lookup[email]
    shas = [email2sha(email, repo.name) for email in to_try]
    shas = [sha for sha in shas if sha]
    # Try getting username from commits
    for sha in shas:
        user = sha2login(sha, repo)
        if user:
            return user
    # Try tracking PRs for commits.
    for sha in shas:
        pr = sha2pr(sha, repo, token)
        if pr:
            return pr.user.login


def get_email2login(repo_data):
    lookup = {}
    for login, cdata in repo_data['contributors'].items():
        email = cdata['user']['commit_email']
        if email:
            lookup[email] = login
    return lookup


def get_usernames(emails, mapper, email_lookup, repo, token):
    usernames = []
    for email in emails:
        to_try = [email] + mapper[email]
        user = get_username(to_try, email_lookup, repo, token)
        usernames.append(user)
    return usernames


def _cmd_in_repo(cmd, repo_dir):
    return check_output(f'(cd {repo_dir} && {cmd})',
                        shell=True,
                        text=True)


def graphql_query(query, token):
    headers = {'Authorization': f'token {token}'}
    answer = requests.post(url=GRAPHQL_URL,
                           json={'query': query},
                           headers=headers)
    return json.loads(answer.text)


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


def main(org_name, repo_name):
    authors = get_authors(repo_name)
    gte_50 = authors.query('no >= 50')
    emails = gte_50.index
    with open('projects_50_emails.json', 'rt') as fobj:
        data = json.load(fobj)
    email_map = get_email_map(repo_name, emails)
    email2login = get_email2login(data[repo_name])
    token = get_gh_token()
    gh = github3.login(token=token)
    repo = gh.repository(org_name, repo_name)
    # usernames = get_usernames(emails, email_map, email2login, repo, token)
    usernames = get_usernames(emails, email_map, {}, repo, token)
    return usernames

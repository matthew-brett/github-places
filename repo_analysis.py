""" Analyze repositories for commits not attributed, etc
"""

import pandas as pd

from gputils import RepoGetter

REPO_GETTER = RepoGetter()

# Load user data
users = pd.read_csv('users_locations.csv')
users.head()

# Review users where country is N/K (not known).
nk_users = users[users['country_code'] == 'N/K']
nk_users = nk_users[['repo', 'n_commits', 'gh_user']]

pct_users_nk = len(nk_users) / len(users)

pct_sc_missing = nk_users['n_commits'].sum() / users['n_commits'].sum() * 100

# For what percentage of Github users do I have to specify the location?

from contrib_countries import GH_USER2LOCATION

pct_loc_specified = len(GH_USER2LOCATION) / len(users) * 100

from find_gh_users import NAME2GH_USER
n_specified = sum(len(v) for k, v in NAME2GH_USER.items())
pct_gh_specified = n_specified / len(users) * 100

nnk_users = users[users['country_code'] != 'N/K']
repo_missing_pcts = {}
for repo_name in users['repo'].unique():
    repo_contribs = REPO_GETTER.get_contributors(repo_name)
    total_commits = sum(len(c) for c in repo_contribs)
    found_commits = (nnk_users
                     [nnk_users['repo'] == repo_name]
                     ['n_commits'].sum())
    repo_missing_pcts[repo_name] = found_commits / total_commits * 100

print(f"""\
I could not find the location for {pct_users_nk:.2f}% of SCs, and
therefore {pct_sc_missing:.2f}% of SC contributor commits.

For {pct_gh_specified:.1f}% of SCs, I had to work out the corresponding
Github user manually.

I had to identify the locations of {pct_loc_specified:.1f}% of SC Github users
manually by various searches.

Percentage of total repository commits included in the analysis, by repository:
""")

for repo, pct in repo_missing_pcts.items():
    print(f'*   {repo}: {pct:.1f}')

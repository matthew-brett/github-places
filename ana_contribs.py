""" Analyze contributions data
"""

import pandas as pd

# Run contrib_countries.py first.
users = pd.read_csv('users_locations.csv')
country_data = pd.read_csv('country_data.csv')

# Merge by Github user
merged = users.groupby('gh_user').sum()

# Sort by commits
merged = merged.sort_values('n_commits', ascending=False)
print(merged.head(20))

# Merge by Country
by_country = (users.groupby('country_code').sum().
              sort_values('n_commits', ascending=False))
print(by_country.head(20))

# Show UK commits
uk = (users[users['country_code'] == 'GBR'].
      groupby('gh_user').sum().
      sort_values('n_commits', ascending=False))
print(uk.head(20))

by_country_gdp = by_country.merge(country_data, on='country_code')
by_country_gdp['commits_per_million'] = (by_country_gdp['n_commits'] /
                                         by_country_gdp['population'])
print(by_country_gdp.head(10).sort_values(
    'commits_per_million',
    ascending=False))

from tablulate import tabulate

tab = tabulate(by_country_pop,
         headers='Country,Commits,Population (millions),Commits/million'.split(','),
         tablefmt='pipe', 
         floatfmt='0.1f',
        showindex=False)
print(tab)

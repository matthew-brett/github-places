""" Analysis of commits by country
"""

import pandas as pd

from tabulate import tabulate

# Load user data
users = pd.read_csv('users_locations.csv')
users.head()

# Load country data
country_data = pd.read_csv('country_data.csv')

# Aggregate over Github user:

def aggregate_user(sub_df):
    first = sub_df.iloc[0]
    out = sub_df.iloc[0][['name', 'country_code']]
    out['n_commits'] = sub_df['n_commits'].sum()
    out['repos'] = '; '.join(f"{row['repo']}: {row['n_commits']}"
                    for i, row in sub_df.iterrows())
    return out

by_gh_user = users.groupby('gh_user').apply(aggregate_user)
by_gh_user = by_gh_user.sort_values('n_commits', ascending=False)

by_country = (by_gh_user.groupby('country_code').sum()
              .sort_values('n_commits', ascending=False))

# Merge population in millions.
population = country_data[['country_code', 'country_name', 'population']]
by_country_pop = by_country.merge(population, on='country_code')
by_country_pop = by_country_pop[
    ['country_name', 'n_commits', 'population']]

# Calculate commits per million in population
by_country_pop['commits_per_million'] = (by_country_pop['n_commits'] /
                                         by_country_pop['population'])

# Top 10 countries by commit numbers, ordered by commits per million.
by_country_pop = (by_country_pop
                  .head(10)
                  .sort_values('commits_per_million', ascending=False))

# Make nice Markdown table therefrom
tab = tabulate(by_country_pop,
         headers='Country,Commits,Population (millions),Commits/million'.split(','),
         tablefmt='pipe', 
         floatfmt='0.1f',
        showindex=False)
print(tab)

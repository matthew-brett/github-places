""" Analyze project data
"""
import json
import re

import numpy as np

import pandas as pd

""" The standard list of countries from the [UN statistics division
website](https://unstats.un.org/unsd/methodology/m49/overview).
"""

un_countries = pd.read_csv('un_stats_division_countries.csv')
iso3 = un_countries['ISO-alpha3 Code']
countries = un_countries['Country or Area']


LOCATIONS = {
    # https://www.ocf.berkeley.edu/~antonyl/research.html
    'anntzer': 'Bordeaux, France',
    # https://www.oreilly.com/people/ben-root
    # https://www.bloomberg.com/research/stocks/private/snapshot.asp?privcapId=4640588
    'WeatherGod': 'Lexington, MA, USA',
    # https://www.physics.utoronto.ca/%7Eesalesde/
    # https://twitter.com/QuLogic
    'QuLogic': 'Toronto, Canada',
    # Probably
    # https://www.researchgate.net/profile/Jae-Joon_Lee
    # See: https://github.com/astropy/pyregion/graphs/contributors
    'leejjoon': 'Daejeon, South Korea',
    # iki.fi email address
    'pv': 'Finland',
    # I've stayed in his house
    'eric-jones': 'Austin, TX',
    # https://vorpus.org/
    'njsmith': 'Berkeley, CA',
    # Works at Enthought, based in Texas
    'rkern': 'Austin, TX',
    # I know him via BIDS
    'mattip': 'Israel',
}


COUNTRY_REGEXPS = (
    (r'Seattle', 'USA'),
    (r'Berkeley', 'USA'),
    (r'Austin', 'USA'),
)


def get_countrish(location):
    if ';' in location:
        return location.split(';')[-1]
    parts = [p.strip() for p in location.split(',')]
    return parts[-1]


def get_country(location):
    if location is None:
        return
    for reg, country in COUNTRY_REGEXPS:
        if re.search(reg, location):
            return country
    country = get_countrish(location)
    is_iso = iso3 == country
    if np.any(is_iso):
        return iso3.loc[is_iso].item()
    is_country = countries == country
    if np.any(is_country):
        return iso3.loc[is_country].item()
    return country


with open('projects.json', 'rt') as fobj:
    data = json.load(fobj)

proj = data['numpy']

for login, c_data in proj['contributors'].items():
    location = LOCATIONS.get(login, c_data['user']['location'])
    country = get_country(location)
    print(f"""{login}; {c_data['contributions']}; {location}; {country}""")

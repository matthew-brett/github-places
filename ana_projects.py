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
    # https://www.linkedin.com/in/allan-haldane-486510131/
    'ahaldane': 'Philadelphia, Pennsylvania, USA',
    # Works at Enthought, based in Texas
    'rkern': 'Austin, TX',
    # Was in Berlin in 2011.
    # https://wiki.kubuntu.org/JulianTaylor/MOTUApplication
    # Now seems to be in the European Southern Observatory near Munich
    # www.eso.org/~jagonzal/ADASS-2016/P6-11/P6-11.tex
    'juliantaylor': 'Bayern, Germany',
    # I know him via BIDS
    'mattip': 'Israel',
    # Stefan vdW told me
    'seberg': 'Göttingen, Germany',
    # Warren is very difficult to track down.  He had an Enthought
    # address until 2012 in the Scipy logs.  Also this:
    # https://www.instantcheckmate.com/people/warren-weckesser/
    'WarrenWeckesser': 'Austin, Texas',
    # Found: alex <argriffi@ncsu.edu>, author of
    # https://github.com/scipy/scipy/commit/3e8cb71f0118b1603f42b8aafb97aa0452401a1e
    'alexbrc': 'North Carolina, USA',
    # https://brae.calpoly.edu/faculty-and-staff-haberland
    'mdhaber': 'San Luis Obispo, CA, USA',
    # In git log: Lars Buitinck <larsmans@gmail.com>
    # https://www.linkedin.com/in/larsbuitinck/
    'larsmans': 'Amsterdam, Netherlands',
    # http://staff.washington.edu/larsoner/
    'larsoner': 'Seattle, USA',
    # http://www.ajoly.org/
    'arjoly': 'Liège, BEL',
    # https://team.inria.fr/parietal/loic-esteve-takes-a-permanent-position-at-inria-paris/
    'lesteve': 'Paris, FRA',
    # https://jmetzen.github.io/pages/about.html
    'jmetzen': 'Renningen, Germany',
    # https://demuc.de
    'ahojnnes': 'Zurich, Switzerland',
    # http://svi.cnrs.fr/spip/spip.php?article27
    'emmanuelle': 'Aubervilliers, FRA',
    # https://www.lfd.uci.edu/~gohlke/
    'cgohlke': 'Irvine, California, USA',
    # https://brage.bibsys.no/xmlui/handle/11250/247388
    'josteinbf': 'Oslo, Norway',
    # https://www.linkedin.com/in/chris-colbert-89699b7/
    'sccolbert': 'Austin, Texas',
    # http://warmspringwinds.github.io/about/
    'warmspringwinds': 'Baltimore, Maryland, USA',
    # http://www.chadfulton.com/
    'ChadFulton': 'USA',
    # Via Google: http://dept.stat.lsa.umich.edu/~kshedden/
    'kshedden': 'Michigan, USA',
    # https://www.linkedin.com/in/brock-mendel-76287a83/
    'jbrockmendel': 'San Francisco, USA',
    # In git log: Justin Grana <jg3705a@student.american.edu>
    'j-grana6': 'Washington DC, USA',
    # https://www.linkedin.com/in/pquackenbush/
    # Location "Baghdad on the Bayou" could be Houston, which fits above.
    # https://www.houstonpress.com/news/houston-101-yet-another-new-nickname-for-the-bayou-city-er-space-city-um-h-town-6738937
    'thequackdaddy': 'Houston, Texas',
    # https://www.bartonbaker.us
    'bartbkr': 'Rhode Island, USA',
    # THis commit by yogabonito has email aleksandar.karakas@student.tugraz.at
    # https://github.com/statsmodels/statsmodels/commit/bf2d2b0d0cf76d99149503aee17925eaf4d117c4
    'yogabonito': 'Graz, Austria',
    # https://tomaugspurger.github.io/pages/about.html
    'TomAugspurger': 'Des Moines, USA',
    # https://www.linkedin.com/in/jeff-reback-3a20876/
    'jreback': 'NYC, USA',
    # https://jorisvandenbossche.github.io/pages/about.html
    'jorisvandenbossche': 'Paris, France',
    # Has email terji78@gmail.com . Gives Terji Petersen
    # https://mail.python.org/pipermail/tutor/2005-May/038446.html
    # Discussing a chess program, suggesting
    # https://chess-db.com/public/pinfo.jsp?id=7200293
    'topper-123': 'Faroe Islands',
    # https://www.linkedin.com/in/smichr/
    'smichr': 'Minneapolis, USA',
}


COUNTRY_REGEXPS = (
    (r'Seattle', 'USA'),
    (r'Berkeley', 'USA'),
    (r'Austin', 'USA'),
    (r'Chicago', 'USA'),
    (r'New York', 'USA'),
    (r'NYC', 'USA'),
    (r'Texas', 'USA'),
    (r'Arizona', 'USA'),
    (r'Denver', 'USA'),
    ('Cincinnati', 'USA'),
    ('Philadelphia', 'USA'),
    (r'Ithaca', 'USA'),
    (r'Hawaii', 'USA'),
    (r'Boston', 'USA'),
    (r'Nashville', 'USA'),
    (r'California', 'USA'),
    (r'Bay Area', 'USA'),
    (r'San Francisco', 'USA'),
    (r'San Diego', 'USA'),
    (r'Los Alamos', 'USA'),
    ('ABQ$', 'USA'),
    ('London', 'GBR'),
    ('Bristol', 'GBR'),
    ('United Kingdom', 'GBR'),
    ('UK$', 'GBR'),
    (r'Pasadena', 'USA'),
    (r'Mountain View', 'USA'),
    (r'Copenhagen', 'DNK'),
    ('Helsinki', 'FIN'),
    (r'Korea', 'KOR'),
    (r'Seoul', 'KOR'),
    ('Paris', 'FRA'),
    (r'Russia', 'RUS'),
    (r'Saint Petersburg', 'RUS'),
    (r'Perm', 'RUS'),
    ('Mumbai', 'IND'),
    (r'Sydney', 'AUS'),
    (r'Minsk', 'BLR'),
    (r'Bologna', 'ITA'),
    ('Brazil$', 'BRA'),
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


def dump_project(proj_name):
    proj = data[proj_name]
    for login, c_data in proj['contributors'].items():
        location = LOCATIONS.get(login, c_data['user']['location'])
        country = get_country(location)
        print(f"""{login}; {c_data['contributions']}; {location}; {country}""")

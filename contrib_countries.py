""" Detect and analyze countries for Git / Github contributors
"""

from os.path import exists
import json
import re
import github3
from subprocess import check_call
from collections import zip_longest

import numpy as np

import pandas as pd

from gputils import GH, lupdate

""" The standard list of countries from the [UN statistics division
website](https://unstats.un.org/unsd/methodology/m49/overview).
"""

un_countries = pd.read_csv('un_stats_division_countries.csv')
iso3 = un_countries['ISO-alpha3 Code']
countries = un_countries['Country or Area']


""" Standard list of states in US and Canada
"""
na_states = pd.read_csv('state_table.csv')

# Locations for Github users where location string is not useful or absent.
# Data from web-stalking.
# Keys are Github users.
# Values are location strings, to be processed by location2country

GH_USER2LOCATION = {
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
    # I know Eric.
    'eric-jones': 'Austin, TX',
    # https://vorpus.org/
    'njsmith': 'Berkeley, CA',
    # https://www.linkedin.com/in/allan-haldane-486510131/
    'ahaldane': 'Philadelphia, Pennsylvania, USA',
    # Works at Enthought. Enthought based in Austin, Texas. Most
    # recent commits UTC-8.
    'rkern': 'Austin, TX',
    # Was in Berlin in 2011.
    # https://wiki.kubuntu.org/JulianTaylor/MOTUApplication
    # Now seems to be in the European Southern Observatory near Munich
    # www.eso.org/~jagonzal/ADASS-2016/P6-11/P6-11.tex
    'juliantaylor': 'Bayern, Germany',
    # I know him via BIDS.
    'mattip': 'Israel',
    # Stefan vdW told me.
    'seberg': 'Göttingen, Germany',
    # Warren had an Enthought address until 2012 in the Scipy logs.  Also this:
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
    # Github location "Baghdad on the Bayou" could be Houston, which fits
    # above:
    # https://www.houstonpress.com/news/houston-101-yet-another-new-nickname-for-the-bayou-city-er-space-city-um-h-town-6738937
    'thequackdaddy': 'Houston, Texas',
    # https://www.bartonbaker.us
    'bartbkr': 'Rhode Island, USA',
    # This commit by yogabonito has email aleksandar.karakas@student.tugraz.at
    # https://github.com/statsmodels/statsmodels/commit/bf2d2b0d0cf76d99149503aee17925eaf4d117c4
    'yogabonito': 'Graz, Austria',
    # https://tomaugspurger.github.io/pages/about.html
    'TomAugspurger': 'Des Moines, USA',
    # https://www.linkedin.com/in/jeff-reback-3a20876/
    'jreback': 'NYC, USA',
    # I emailed them and they replied.
    'gfyoung': 'USA',
    # https://jorisvandenbossche.github.io/pages/about.html
    'jorisvandenbossche': 'Paris, France',
    # Has email terji78@gmail.com . Gives T Petersen from:
    # https://mail.python.org/pipermail/tutor/2005-May/038446.html
    # Discussing a chess program, suggesting
    # https://chess-db.com/public/pinfo.jsp?id=7200293
    # Above profile has 1978 birth year matching terji78.
    'topper-123': 'Faroe Islands',
    # https://directory.science.mq.edu.au/users/tjames
    'aragilar': 'Sydney, AUS',
    # https://www.linkedin.com/in/smichr/
    'smichr': 'Minneapolis, USA',
    # Thomas tells me via email he's based in the UK though working for
    # https://www.xfel.eu
    'takluyver': 'UK',
    # Lists the HDF group as employer
    'ajelenak-thg': 'Urbana-Champaign, USA',
    # Email listed as <aaron.parsons@diamond.ac.uk>
    # https://www.diamond.ac.uk/Home/ContactUs.html
    'aaron-parsons': 'Didcot, UK',
    # Probably
    # https://www.xfel.eu/facility/instruments/scs/scs_group_members/index_eng.html
    'tecki': 'Schenefeld, Germany',
    # Lists employer as Oak Ridge National Laboratory
    'sethrj': 'Tennessee, USA',
    # Git log has email John Kirkham <kirkhamj@janelia.hhmi.org>
    # https://www.janelia.org/
    'jakirkham': 'Virginia, USA',
    # http://consulting.behnel.de/
    'scoder': 'München, Germany',
    # https://www.linkedin.com/in/robert-bradshaw-1b48a07/
    'robertwb': 'Seattle, USA',
    # Github page lists noodle-app.io, which fits with
    # https://www.linkedin.com/in/mark-florisson-742a0175/
    'markflorisson': 'London, UK',
    # By looking at git shortlog on the Cython repository, this
    # appears to be Kurt Smith.  Last email address in log was
    # Enthought
    'invalid-email-address': 'USA',
    # Email in git log is "zaur <aintellimath@gmail.com>"
    # We also see "intellimath" Zaur Shibzukhov <szport@gmail.com>
    # Github user intellimath based in Moscow
    'aintellimath': 'Moscow, Russia',
    # Affiliation listed as Faculty of Physics, Moscow State University,
    # Moscow, Russia in https://peerj.com/preprints/2083
    # https://skirpichev.github.io blog has me@skirpichev.msk.ru as contact
    # address.
    'skirpichev': 'Moscow, Russia',
    # Maybe https://theorie.physik.uni-konstanz.de/jrioux/pdf/Rioux_cv.pdf
    # Thesis mentions sympy
    # https://tspace.library.utoronto.ca/bitstream/1807/31919/1/Rioux_Julien_201108_PhD_thesis.pdf
    'jrioux': 'Konstanz, Germany',
    # Email address in git log is Raoul Bourquin <raoulb@bluewin.ch>
    # Does not appear to this guy, who is Github user raoulbq (from Scipy
    # commit log):
    # https://www.research-collection.ethz.ch/handle/20.500.11850/183094
    'raoulb': 'Switzerland',
    # Github repo leads to Math 405 lectures, which leads to
    # http://www.math.ubc.ca/~cbm/
    'cbm755': 'Canada',
    # Git log has jegerjensen <jensen.oyvind@gmail.com> and
    # Øyvind Jensen <jensen.oyvind@gmail.com>
    # Github has fork of AMGXqGPU library. An 'Øyvind Jensen" is an author on 
    # https://www.researchgate.net/publication/318949247_GPU_implementation_of_Kampmann-Wagner_numerical_precipitation_models
    # and works in the Institute of Energy Technology, in Norway.
    'jegerjensen': 'Lillestrøm, Norway',
    # Google search first hit: https://users.isy.liu.se/en/es/oscarg/
    # Photo matches Github profile
    'oscargus': 'Linköping, Sweden',
    # Second pass, back to Numpy again
    # https://www.linkedin.com/in/jay-bourque-214b3341/
    'jayvius': 'Austin, Texas',
    # UTC-6
    # Xoviat appears to be Paul Dao:
    # http://vtk.1045678.n5.nabble.com/PYPI-wheels-td5745394.html
    # Maybe USA.
    'xoviat': 'N/K',
    # https://www.linkedin.com/in/han-genuit-0b125253
    # Working at:
    # https://www.differ.nl/about-us/people/search?name=Han+Genuit
    # Probably same as J.W.Genuit from:
    # https://sourceforge.net/p/pytables/mailman/message/26926819/
    '87': 'Eindhoven, Netherlands',
    # UTC-5
    # Going with:
    # https://www.linkedin.com/in/eric-moore-18292032
    # because he has forked the NRRD reading repository
    'ewmoore': 'Pennsylvania, USA',
    # Note same user name on LinkedIn
    # https://www.linkedin.com/in/adbugger/?originalSubdomain=in
    'adbugger': 'Telangana, India',
    # Says he works with Google on Github page, and
    # https://www.linkedin.com/in/paul-van-mulbregt-bb00412/
    'pvanmulbregt': 'Boston, USA',
    # https://www.linkedin.com/in/abraham-escalante-68538691/
    # Profile photo is the same.  Did his Scipy work from Mexico.
    'aeklant': 'Ontario, Canada',
    # http://panm19.math.cas.cz/prednasky/PANM19_Robert_Cimrman.pdf
    'rc': 'Czechia',
    # Matches Github email address
    # https://www.algopt.informatik.uni-kiel.de/en/team/m.sc.-joscha-reimer
    'jor-': 'Kiel, Germany',
    # https://www.uva.nl/en/profile/a/r/a.archibald/a.archibald.html?1556896598934
    'aarchiba': 'Amsterdam, Netherlands',
    # I worked with Chris
    'cburns': 'Berkeley, USA',
    # https://mail.python.org/pipermail/scipy-user/2009-March/020175.html has
    # email is from http://cs.uiuc.edu, matches:
    # https://www.linkedin.com/in/nathan-bell-65963915
    'wnbell': 'San Francisco, USA',
    # https://groups.google.com/d/msg/pydata/kPAg3l9vLQI/gAusKjYxQUIJ
    # Address is mattknox.ca@gmail.com. Mentions https://github.com/keeganmccallum
    # who give location as Canada.  UTC-8 in 2008.
    # Maybe https://www.linkedin.com/in/matt-knox-37537217
    '+matt_knox': 'CAN',
    # I know Tom
    # https://www.linkedin.com/in/thomas-waite-04354a4/
    '+tom_waite': 'Berkeley, USA',
    # From email address stevech1097@yahoo.com.au
    '+steve_chaplin': 'AUS',
    # Universitat Bremen as employer
    'andreas-h': 'Bremen, Germany',
    # http://www.tonysyu.com
    'tonysyu': 'Austin, Texas',
    # UTC+3. Python, C++. Maybe:
    # https://www.linkedin.com/in/kniazevnikita/?locale=en_US
    'Kojoley': 'Russia',
    # UTC+1. Maybe Peter Wurtz writing thesis on this page:
    # https://www.physik.uni-kl.de/en/ag-ott/publications/phd-and-diploma-thesis
    'pwuertz': 'Kaiserslautern, Germany',
    # Could be author on https://www.nature.com/articles/s41598-018-26267-x
    # at Institute for Theoretical Physics, TU Wien.  UTC+1 commits.
    'thisch': 'Vienna, AUT',
    # I know Paul.
    'ivanov': 'Berkeley, CA',
    # https://www.esrl.noaa.gov/psd/people/jeffrey.s.whitaker/
    'jswhit': 'Colorado, USA',
    # Probably https://digitalfellows.commons.gc.cuny.edu/?team=hannah-aizenman
    # because of cs102 repository mentioning CCNY, and
    # https://www.ccny.cuny.edu/compsci/faculty-office-hours
    'story645': 'NY, USA',
    # From git log: Michiel de Hoon
    # One entry in git log has: Michiel de Hoon
    # <mdehoon@tkx294.genome.gsc.riken.jp> - so:
    # https://acgt.riken.jp/?page_id=115
    'mdehoon': 'Yokohama, Japan',
    # https://www2.le.ac.uk/departments/physics/people/victorzabalza
    'zblz': 'Leicester, UK',
    # I can't find him now, but at the time of contribution, he
    # was an astronomer in Bonn
    # https://academic.oup.com/mnras/article/394/4/2223/1207223
    # https://astro.uni-bonn.de/~rschaaf/Python2008/
    'mmetz-bn': 'Bonn, Germany',
    # http://www.kemaleren.com/
    # https://www.linkedin.com/in/kemaleren/
    'kemaleren': 'Pennsylvania, USA',
    # https://www.linkedin.com/in/diemert/
    # via https://scikit-learn.org/stable/testimonials/testimonials.html
    'oddskool': 'Grenoble, FRA',
    # Google search for Bertrand Thirion
    'bthirion': 'Saclay, FRA',
    # Right there on the Github page
    'NicolasHug': 'New York, USA',
    # https://www.linkedin.com/in/maheshakya/
    'maheshakya': 'Utah, USA',
    # UTC-6.  Maybe
    # https://wearerivet.com/about-us/
    'chris-b1': 'N/K',
    # https://pietrobattiston.it/Curriculum_Vitae_en.pdf
    'toobaz': 'Trento, Italy',
    # https://en.wikipedia.org/wiki/Lord_Vetinari
    # UTC+1
    'h-vetinari': 'N/K',
    # Mario Pernici <mario.pernici@gmail.com> in git log.
    # https://arxiv.org/pdf/1805.04037.pdf mentions Python / SageMath
    'pernici': 'Milano, ITA',
    # https://www.ibisc.univ-evry.fr/~sivanov
    'scolobb': 'Saclay, FRA',
    # http://parsoyaarihant.github.io/
    'parsoyaarihant': 'Mumbai, IND',
    # By number of cmmmits this should be Github user normalhuman
    # with name (in git log) Leonid Kovalev
    # https://normalhuman.github.io/progress/report refers to
    # mathematics courses at http://coursecatalog.syr.edu
    # https://github.com/drlvk/drlvk.github.io/blob/master/bookmarklets.html
    # also refers to syr.edu.
    # Sure enough:
    # http://thecollege.syr.edu/people/faculty/pages/math/kovalev-leonid.html
    # Dr Leonid V. Kovalev (drvlk)
    'drlvk': 'New York, USA',
    # https://sidhantnagpal.com/
    'sidhantnagpal': 'Dehli, IND',
    # https://valglad.github.io/ : was at Oxford in 2017
    # https://github.com/sympy/sympy/wiki/GSoC-2017-Application-Valeriia-Gladkova:-Group-Theory
    # https://arxiv.org/abs/1810.08792
    # Email for paper above still Oxford
    'valglad': 'Oxford, GBR',
    # UTC+1.  Git log has oscar.j.benjamin@gmail.com . Probably
    # http://www.bristol.ac.uk/engineering/people/oscar-j-benjamin/index.html
    'oscarbenjamin': 'Bristol, UK',
    # https://jashan498.github.io/blog/
    'jashan498': 'Patiala, IND',
    # https://blog.krastanov.org/staticprerenders/resume.html
    'Krastanov': 'Yale, USA',
    # Via Google: http://www.math.toronto.edu/siefkenj/homepage/index.html
    # Link back to Github page
    # http://www.math.toronto.edu/siefkenj/homepage/index.html#software
    'siefkenj': 'Toronto, CAN',
    # Brian Granger (co-lead on Jupyter)
    # Was teaching Physics at CalPoly, now works for AWS
    # https://www.linkedin.com/in/brian-granger-b9998662
    'ellisonbg': 'Los Osos, USA',
    # http://rpmuller.github.io/
    # https://cs.sandia.gov/~rmuller/
    'rpmuller': 'Albuquerque, USA',
    # https://yathartha22.github.io/about
    'Yathartha22': 'Dwarahat, IND',
    #
    'KaTeX-bot': 'N/K',
    #
    'vks': 'N/K',
    #
    'gilbertgede': 'N/K',
    #
    'vperic': 'N/K',
    #
    'hargup': 'N/K',
    #
    'akash9712': 'N/K',
    #
    'ethankward': 'N/K',
    #
    'addisonc': 'N/K',
    #
    'abaokar-07': 'N/K',
    #
    'hacman': 'N/K',
    #
    'ArifAhmed1995': 'N/K',
    # avishrivastava11.github.io
    'avishrivastava11': 'Goa, IND',
    #
    'jmig5776': 'N/K',
    #
    'RituRajSingh878': 'N/K',
    #
    'lazovich': 'N/K',
    #
    'RavicharanN': 'N/K',
    #
    'Subhash-Saurabh': 'N/K',
    #
    'divyanshu132': 'N/K',
    #
    'postvakje': 'N/K',
    #
    'vramana': 'N/K',
    #
    'arghdos': 'N/K',
    # https://www.linkedin.com/in/briangregoryjorgensen
    # Same photo as github
    'b33j0r': 'Phoenix, USA',
    # Email address; nothing else go on.
    'stevech1097@yahoo.com.au': 'AUS',
    # See find_gh_users.
    # https://www.linkedin.com/in/dmitrey-kroshko-a729aa22/
    '+dmitrey_kroshko': 'Ukraine',
    # See find_gh_users.  Workst at NIST Center for Neutron Research.
    "pkienzle": "Gaithersburg, USA",
    # Matplotlib git log records email as "pado@passoire.fr"
    '+alexis_bienvenue': 'FRA',
    # See find_gh_users.
    # From https://team.inria.fr/parietal/schwarty/
    '+yannick_schwartz': 'Saclay, France',
    # I know Brian
    '+brian_hawthorne': 'USA',
    # LinkedIn page with same photo as Github page
    # https://www.linkedin.com/in/matthieu-perrot-225ab01b/
    'MatthieuPerrot': 'Paris, France',
    # See find_gh_user
    # https://web.archive.org/web/20110826071405/http://robert-code.blogspot.com/2007/05/grbner-basis-hey-my-first-blog-entry-so.html
    "+robert_schwarz": "Heidelberg, Germany",
}

# Regular expressions to apply to location string, resulting in 3-letter ISO
# country code.
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
    ('Cleveland', 'USA'),
    ('Philadelphia', 'USA'),
    (r'Ithaca', 'USA'),
    (r'Hawaii', 'USA'),
    (r'Boston', 'USA'),
    (r'Nashville', 'USA'),
    (r'California', 'USA'),
    (r'Bay Area', 'USA'),
    (r'San Francisco', 'USA'),
    (r'Oakland', 'USA'),
    (r'Merced', 'USA'),
    (r'Irvine', 'USA'),
    (r'San Diego', 'USA'),
    (r'Los Alamos', 'USA'),
    (r'Michigan', 'USA'),
    (r'Los Angeles', 'USA'),
    ('Pittsburgh', 'USA'),
    ('ABQ$', 'USA'),
    (r'Pasadena', 'USA'),
    ('Urbana', 'USA'),
    (r'Mountain View', 'USA'),
    ('Albuquerque', 'USA'),
    ('Stanford', 'USA'),
    ('Atlanta', 'USA'),
    ('Cambridge, MA', 'USA'),
    ('Madison', 'USA'),
    ('Darnestown', 'USA'),
    ('Silver Spring', 'USA'),
    ('Colbert', 'USA'),
    ('Montreal', 'CAN'),
    ('London', 'GBR'),
    ('Bristol', 'GBR'),
    ('United Kingdom', 'GBR'),
    ('UK$', 'GBR'),
    (r'Copenhagen', 'DNK'),
    ('Helsinki', 'FIN'),
    (r'Korea$', 'KOR'),
    (r'Seoul', 'KOR'),
    ('Paris', 'FRA'),
    (r'Russia$', 'RUS'),
    (r'Saint Petersburg', 'RUS'),
    (r'Perm', 'RUS'),
    (r'Moscow', 'RUS'),
    ('Mumbai', 'IND'),
    ('Bengaluru', 'IND'),
    ('Kharagpur', 'IND'),
    ('Andhra Pradesh', 'IND'),
    ('Kanpur', 'IND'),
    ('Hyderabad', 'IND'),
    (r'Sydney', 'AUS'),
    (r'Minsk', 'BLR'),
    (r'Bologna', 'ITA'),
    ('Brazil$', 'BRA'),
    ('Zurich', 'CHE'),
    ('Bordeaux', 'FRA'),
    ('Bremen$', 'DEU'),
    ('Saclay$', 'FRA'),
    ('United States$', 'USA'),
    ('Berlin$', 'DEU'),
    ('Poznan', 'POL'),
    ('Tokyo', 'JPN'),
    ('Oslo', 'NOR'),
    ('Amersfoort', 'NLD'),
)


def get_fields(obj):
    return getattr(obj, 'fields', ())


class pretty_dict(dict):

    fields = (
        'login',
        'avatar_url',
        'gravatar_id',
        'name',
        'company',
        'blog',
        'location',
        'email',
        'bio',
        'other_emails',
        'timezone_counts',
        'created_at',
        'updated_at')

    def _all_fields(self):
        fields = get_fields(self)
        other_fields = tuple(
            f for f in self if f not in fields)
        return fields + other_fields

    def __str__(self, indent=''):
        fields = self._all_fields()
        field_len = max(len(f) for f in fields) + 2
        fmt = '%s{f:<%d}: {v}' % (indent, field_len)
        lines = []
        for f in fields:
            lines.append(fmt.format(f=f, v=self[f]))


def location2countrish(location):
    if ';' in location:
        return location.split(';')[-1].strip()
    parts = [p.strip() for p in location.split(',')]
    return parts[-1]


def location2country(location):
    if location is None:
        return None
    for reg, country in COUNTRY_REGEXPS:
        if re.search(reg, location):
            return country
    country = location2countrish(location)
    if country == 'N/K':
        return country
    is_iso = iso3 == country
    if np.any(is_iso):
        return iso3.loc[is_iso].item()
    is_country = countries == country
    if np.any(is_country):
        return iso3.loc[is_country].item()
    raise ValueError(f"{country} doesn't seem to be a country")


def user_report(gh_user, user_data):
    user_data = dict(zip_longest(
        DEFAULT_USER_FIELDS, [None]))
    gh_data = USER_GETTER(gh_user)
    if gh_data:
        lupdate(user_data, gh_data)
    # Get repository data
    # Add to user_data
    check_call(['open', user_data['avatar_url']])


def print_dict(d):
    indent = max(len(f) for f in d) + 2
    fmt = '{f:<%d}: {v}' % indent
    for k, v in d.items():
        print(fmt.format(f=k, v=v))

    gh_pages = []
    for ext in ('io', 'com'):
        repo = f'{login}.github.{ext}'
        try:
            gh.repository(login, repo)
        except github3.exceptions.NotFoundError:
            pass
        else:
            gh_pages.append(repo)
    if gh_pages:
        print('gh_pages:', ', '.join(gh_pages))
        check_call(['open', 'https:' + gh_pages[0]])


class UserGetter:

    def __init__(self, cache_fname=None):
        self._GH = GH
        self.cache_fname = cache_fname
        if cache_fname:
            self.load_cache()
        else:
            self.clear_cache()

    def load_cache(self):
        if self.cache_fname is None:
            raise ValueError('No cache_fname to load from')
        if not exists(self.cache_fname):
            self._cache = {}
            return
        with open(self.cache_fname, 'rt') as fobj:
            self._cache = json.load(fobj)

    def save_cache(self):
        if self.cache_fname is None:
            raise ValueError('No cache_fname to save to')
        with open(self.cache_fname, 'wt') as fobj:
            json.dump(self._cache, fobj)

    def clear_cache(self):
        self._cache = {}

    def __call__(self, gh_user):
        if gh_user not in self._cache:
            self._cache[gh_user] = self._get_gh_user(gh_user)
        return self._cache[gh_user]

    def _get_gh_user(self, gh_user):
        if gh_user.startswith('+') or gh_user == 'ghost':
            return None
        return self._GH.user(gh_user).as_dict()


USER_GETTER = UserGetter('.user_cache.json')


def gh_user2location(gh_user):
    if gh_user in GH_USER2LOCATION:
        return GH_USER2LOCATION[gh_user]
    user_data = USER_GETTER(gh_user)
    if user_data:
        return user_data['location']


users = pd.read_csv('gh_user_map_e811f56.csv')
users['location'] = users['gh_user'].apply(gh_user2location)
users['country'] = users['location'].apply(location2country)

users.to_csv('users_locations.csv', index=False)
USER_GETTER.save_cache()

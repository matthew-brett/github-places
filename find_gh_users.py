""" Find Github users for contributors to repository (or allocate fake user)

See the `guess_gh_user` method of :class:`RepoContributor` for the algorithm.
"""

from argparse import ArgumentParser

import pandas as pd

from gputils import (Repo, REPO2ORG, merge_dicts, update_subdicts, get_sha7,
                     get_last_gh_users)

DEFAULT_MIN_COMMITS=25


# For contributors where automated detection of Github user fails.
# Name via mailmap from git shortlog
NAME2GH_USER = {
    'numpy': {
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
        # Git log shows William Spotz <wfspotz@sandia.gov@localhost> matching
        'William Spotz': 'wfspotz',
        # Log has Oscar Villellas <oscar.villellas@continuum.io>
        # https://www.linkedin.com/in/oscar-villellas-38bb241
        # has worked at Anaconda Inc (successor to Continuum).
        'Óscar Villellas Guillén': 'ovillellas'},
    'scipy': {
        # I worked with Chris in Berkeley
        'Chris Burns': 'cburns',
        # As above for numpy
        'cookedm': 'dmcooke',
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
        # I have worked with Jonathan. He worked on statistics in Scipy.
        'Jonathan Taylor': 'jonathan-taylor',
        # I know Ilan; address ilan@enthought.com; website from Github page:
        # http://ilan.schnell-web.net.
        "Ilan Schnell": 'ilanschnell',
        # I know Prabhu; website from Github page:
        # https://www.aero.iitb.ac.in/~prabhu/
        'prabhu': 'prabhuramachandran',
        # One hit for this name on Github, and LinkedIn; lists Python skills
        # https://www.linkedin.com/in/tim-at-bitsofbits/
        # All Numpy and Scipy contributions in 2006
        # Numpy list emails from ieee.org address:
        # https://mail.python.org/pipermail/numpy-discussion/2007-July/028358.html
        # LinkedIn profile has "I'm a scientific programmer with an electrical
        # engineering / physics background".
        # User with same name, Github icon writing Python recipes in 2007
        # http://code.activestate.com/recipes/117119-sieve-of-eratosthenes/
        "Tim Hochberg": 'bitsofbits',
        # Author of OpenOpt
        # https://openopt.blogspot.com/
        # LinkedIn page lists OpenOpt site as personal site
        # https://www.linkedin.com/in/dmitrey-kroshko-a729aa22/
        # No obvious Github email.
        "Dmitrey Kroshko": '+dmitrey_kroshko',
    },
    'matplotlib': {
        # No signs I could see.
        'Steve Chaplin': '+steve_chaplin',
        # See merge commit b9bc7d16dc5c60cc83f2c9ce8866343cf3432afa
        # Merging user jrevans, with PR mixing commits, but mainly from
        # James Evans <jrevans1@earthlink.net>
        'James R. Evans': 'jrevans',
        # I have this email in my email archive, lists email address at nist.gov
        # https://sourceforge.net/p/matplotlib/mailman/message/20367498
        # Leading to Github user with same username, leading to
        # http://pkienzle.github.io leading to
        # https://scholar.google.com/citations?user=IWD0kUQAAAAJ - NIST again.
        "pkienzle": "pkienzle",
        # Git log email is pebarret@gmail.com, listed on this Github user page.
        "Paul Barret": 'barrettp',
        # No obvious Github user
        'Alexis Bienvenüe': '+alexis_bienvenue',
    },
    'scikit-learn': {
        # PR merge commit 2b60c815a0c9467b28766eac3371f25ed3c3c7a0
        # Merge pull request #2290 from dengemann/more_ica_improvements
        # Commits are from dengemann <d.engemann@fz-juelich.de>
        'dengemann': 'dengemann',
        # https://team.inria.fr/parietal/schwarty from email inria.fr
        "Yannick Schwartz": '+yannick_schwartz',
        # Search for name gives this Github user page, where website leads
        # to CV, listing contribution to scikit-learn.
        "Yann N. Dauphin": 'ynd',
        # Github search gives one hit for name, with 4 repos, one of which is
        # fork of scikit-learn
        "Matthieu Perrot": 'MatthieuPerrot',
    },
    'scikit-image': {
        # Ralf is a big contributor to numpy and scipy. Github user found
        # there.
        "Ralf Gommers": 'rgommers',
    },
    'statsmodels': {
        # I worked with Chris; these are contributions via the Nipy project
        'Christopher Burns': 'cburns',
        # Tim worked on Nipy as a consultant, from Australia.  Github has two
        # users matching "Tim Leslie", they are two accounts for the same
        # person. His Github page links to a site listing many Python skills;
        # he is based in Australia.
        # http://www.timl.id.au/#skills
        'tim.leslie': 'timleslie',
        # I know Brian; he worked with me on Nipy.
        "brian.hawthorne": '+brian_hawthorne',
    },
    'pandas': {
        # Gives 'ghost' user otherwise.
        'y-p': '+y_p',
    },
    'sympy': {
        # https://github.com/sympy/sympy/wiki/GSoC-2007-Report-Jason-Gedge:-Geometry
        # https://www.gedge.ca/about.html
        # Contributions seem to pre-date Github
        'Jason Gedge': 'thegedge',
        # https://api.github.com/users/b33j0r/events
        'Brian Jorgensen': 'b33j0r',
        # From Numpy, Scipy
        "Pearu Peterson": "pearu",
        # From git log, GH user was siddhanathan, now deleted.
        # E.g. https://github.com/sympy/sympy/pull/883
        "Siddhanathan Shanmugam": '+siddhanathan_shanmugam',
        # Github page pins Sympy repository
        "Jorn Baayen": 'jbaayen',
        # Two Sanket Agarwals on Github, of which only one has a fork of Sympy
        'Sanket Agarwal': 'snktagarwal',
        # Commits all from 2007, look like GSoC, leading to this page
        # https://straightupcoding.blogspot.com/2007/04/google-summer-of-code-2007-with-sympy.html
        # From a broken link, we reach
        # https://web.archive.org/web/20110826071405/http://robert-code.blogspot.com/2007/05/grbner-basis-hey-my-first-blog-entry-so.html
        # "I am a student of mathematics and computer science at the university
        # of Heidelberg, Germany"
        # One hit for Github user search, but not clear it's the same person;
        # no Sympy clone, works with Julia.
        "Robert Schwarz": "+robert_schwarz",
        # Mis-labelled as KaTeX-bot by GH information from
        # commit 3b2b8ef9c1d84075ada028e95c37ba1000a58082
        # In fact:
        # https://github.com/sympy/sympy/pull/14443
        'ylemkimon': 'ylemkimon',
    },
    'cython': {
        # Commit 315efe4ca11f2965dbdc064cad00ee455f1296c9
        # Merge branch '_numpy' of git://github.com/dagss/cython
        # I have met Dag Sverre - Github picture matches
        'Dag Sverre Seljebotn': 'dagss',
    },
    'other': {  # Notes on research that I'm reluctant to delete.
        # https://partiallattice.wordpress.com/about
        # Gives email as
        # smith (dot) daniel (dot) br gmail (dot) com
        # and points to:
        # https://github.com/Daniel-B-Smith
        # Actually, autodetected with current algorithm.
        'Daniel B. Smith': 'Daniel-B-Smith',
    }
}


# Numpy and Scipy share contributors
merge_dicts(NAME2GH_USER['scipy'], NAME2GH_USER['numpy'])
merge_dicts(NAME2GH_USER['numpy'], NAME2GH_USER['scipy'])


def contributors_for(repo_name, org_name=None,
                     start_from=None,
                     min_commits=DEFAULT_MIN_COMMITS):
    start_from = {} if start_from is None else start_from
    update_subdicts(start_from, NAME2GH_USER)
    repo = Repo(repo_name, org_name)
    contribs = repo.contributors()
    contribs = [c for c in contribs if len(c) >= min_commits]
    repo_map = start_from.get(repo_name, {})
    for c in contribs:
        c.gh_user = repo_map.get(c.name)
        if c.gh_user is None:
            c.gh_user = c.guess_gh_user()
    return contribs


def all_contributors(start_from=None, min_commits=DEFAULT_MIN_COMMITS):
    all_contribs = {}
    for repo_name in REPO2ORG:
        all_contribs[repo_name] = contributors_for(repo_name,
                                                   start_from=start_from,
                                                   min_commits=min_commits)
    return all_contribs


def save_all(contrib_map, fname=None):
    fname = f'gh_user_map_{get_sha7()}.csv' if fname is None else fname
    with open(fname, 'wt') as fobj:
        fobj.write('repo,n_commits,name,email,gh_user\n')
        for repo_name, contribs in contrib_map.items():
            for c in contribs:
                fobj.write(
                    f'"{repo_name}",{len(c)},"{c.name}","{c.email}","{c.gh_user}"\n')


def df2gh_map(df):
    if not hasattr(df, 'iloc'):
        df = pd.read_csv(df)
    mapping = {}
    for i in range(len(df)):
        repo_name, n, name, _, gh_user = df.iloc[i][:5]
        if not repo_name in mapping:
            mapping[repo_name] = {}
        mapping[repo_name][name] = gh_user
    return mapping


def main():
    parser = ArgumentParser()
    parser.add_argument(
        '-n', '--min-commits',
        type=int,
        default=DEFAULT_MIN_COMMITS,
        help='Minimum number of commits per repo to qualify for GH user check')
    parser.add_argument(
        '-o', '--out-fname',
        help='Output filename')
    parser.add_argument(
        '-s', '--start-from',
        help='Path to CSV file with established mappings to start from'
        'or LAST to start from most recent in Git history')
    args = parser.parse_args()
    start_from = args.start_from
    if start_from == 'LAST':
        start_from = get_last_gh_users()
    start_from = df2gh_map(start_from) if start_from else None
    repo_contribs = all_contributors(start_from=start_from,
                                     min_commits=args.min_commits)
    save_all(repo_contribs, fname=args.out_fname)


if __name__ == '__main__':
    main()

""" Find Github users for contributors to repository (or allocate fake user)

See the `guess_gh_user` method of :class:`RepoContributor` for the algorithm.
"""

from argparse import ArgumentParser
from subprocess import check_output

from gputils import Repo, REPO2ORG


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
        'fullung': 'alberts'
    },
    'matplotlib': {
        # No signs I could see.
        'Steve Chaplin': '+steve_chaplin',
        # See merge commit b9bc7d16dc5c60cc83f2c9ce8866343cf3432afa
        # Merging user jrevans, with PR mixing commits, but mainly from
        # James Evans <jrevans1@earthlink.net>
        'James R. Evans': 'jrevans',
    },
    'sympy': {
        # https://github.com/sympy/sympy/wiki/GSoC-2007-Report-Jason-Gedge:-Geometry
        # https://www.gedge.ca/about.html
        # Contributions seem to pre-date Github
        'Jason Gedge': 'thegedge',
        # https://api.github.com/users/b33j0r/events
        'Brian Jorgensen': 'b33j0r',
    },
    'scikit-learn': {
        # PR merge commit 2b60c815a0c9467b28766eac3371f25ed3c3c7a0
        # Merge pull request #2290 from dengemann/more_ica_improvements
        # Commits are from dengemann <d.engemann@fz-juelich.de>
        'dengemann': 'dengemann',
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


def contributors_for(repo_name, org_name=None, min_commits=50):
    repo = Repo(repo_name, org_name)
    contribs = repo.contributors()
    contribs = [c for c in contribs if len(c) >= min_commits]
    repo_map = NAME2GH_USER.get(repo_name, {})
    for c in contribs:
        c.gh_user = repo_map.get(c.name)
        if c.gh_user is None:
            c.gh_user = c.guess_gh_user()
    return contribs


def all_contributors(min_commits=50):
    all_contribs = {}
    for repo_name in REPO2ORG:
        all_contribs[repo_name] = contributors_for(repo_name, min_commits)
    return all_contribs


def save_all(contrib_map, fname=None):
    if fname is None:
        sha7 = check_output(['git', 'log', '-1', '--format=%h'],
                            text=True).strip()
        fname = f'gh_user_map_{sha7}.csv'
    with open(fname, 'wt') as fobj:
        fobj.write('repo,n_commits,name,email,gh_user\n')
        for repo_name, contribs in contrib_map.items():
            for c in contribs:
                fobj.write(
                    f'"{repo_name}",{len(c)},"{c.name}","{c.email}","{c.gh_user}"\n')


def main():
    parser = ArgumentParser()
    parser.add_argument(
        '-n', '--min-commits',
        type=int,
        default=50,
        help='Minimum number of commits per repo to qualify for GH user check')
    parser.add_argument(
        '-o', '--out-fname',
        help='Output filename')
    args = parser.parse_args()
    repo_contribs = all_contributors(args.min_commits)
    save_all(repo_contribs, fname=args.out_fname)


if __name__ == '__main__':
    main()

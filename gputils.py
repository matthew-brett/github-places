""" Utilities for github places processing.
"""

from github3 import login


PROJECTS = (
    ('numpy', 'numpy'),
    ('scipy', 'scipy'),
    ('matplotlib', 'matplotlib'),
    ('scikit-learn', 'scikit-learn'),
    ('scikit-image', 'scikit-image'),
    ('statsmodels', 'statsmodels'),
    ('pandas-dev', 'pandas'),
    ('h5py', 'h5py'),
    ('cython', 'cython'),
    ('sympy', 'sympy'),
)

GH_TOKEN_FNAME = '.gh_token'


def get_gh_token(fname):
    with open(fname, 'rt') as fobj:
        for line in fobj:
            line = line.strip()
            if line == '' or line.startswith('#'):
                continue
            return line


GH_TOKEN = get_gh_token(GH_TOKEN_FNAME)
GH = login(token=GH_TOKEN)

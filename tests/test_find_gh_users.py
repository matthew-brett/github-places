""" Tests for find_gh_users module
"""

import sys
from os.path import join as pjoin, abspath, dirname

HERE = dirname(__file__)
DATA_PATH = pjoin(HERE, 'data')
sys.path.append(abspath(pjoin(HERE, '..')))

from find_gh_users import Repo, Contributor


def test_Reop():
    repo = Repo('h5py', path=pjoin(DATA_PATH, 'h5py'))
    contribs = list(repo.contributors())
    assert len(contribs) == 128

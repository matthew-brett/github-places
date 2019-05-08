""" Tests for find_gh_users module
"""

import sys
from os.path import join as pjoin, abspath, dirname

HERE = dirname(__file__)
DATA_PATH = pjoin(HERE, 'data')
sys.path.append(abspath(pjoin(HERE, '..')))

from find_gh_users import Repo, Contributor, parse_shortlog

TEST_REPO = Repo('h5py', path=pjoin(DATA_PATH, 'h5py'))


def test_parse_shortlog():
    eg_out = TEST_REPO.cmd_in_repo(
        ['git', 'shortlog', '-n', "--format=%H,%aN,%aE,%an,%ae,%aI"])
    parsed = parse_shortlog(eg_out)
    assert len(parsed) == 117
    first, second, third, last = parsed[0:3] + [parsed[-1]]
    assert [len(c) for c in (first, second, third, last)] == [940, 233, 212, 1]
    for c in first:
        assert c.c_name == 'andrewcollette'
        assert c.c_email == 'andrew.collette@gmail.com'
    for c in second:
        assert c.c_name == 'Andrew Collette'
        assert c.c_email == 'andrew.collette@gmail.com'
    for c in third:
        assert c.c_name == 'Thomas A Caswell'
        assert c.c_email == 'tcaswell@bnl.gov'
        assert c.o_email in ('tcaswell@bnl.gov', 'tcaswell@gmail.com',
                             'tcaswell@uchicago.edu')
    for c in last:
        assert c.c_name == 'joydeep bhattacharjee'
        assert c.c_email == 'joydeepubuntu@gmail.com'


def test_Repo_contributors():
    contribs = list(TEST_REPO.contributors())
    assert len(contribs) == 117
    first, second, third, last = contribs[0:3] + [contribs[-1]]
    assert ([len(c.commits) for c in (first, second, third, last)] ==
            [940, 233, 212, 1])
    assert first.name == 'andrewcollette'
    assert first.email == 'andrew.collette@gmail.com'
    assert first.names == ('andrewcollette',)
    assert first.emails == ('andrew.collette@gmail.com',)
    assert second.name == 'Andrew Collette'
    assert second.email == 'andrew.collette@gmail.com'
    assert second.names == ('Andrew Collette',)
    assert second.emails == ('andrew.collette@gmail.com',)
    assert third.name == 'Thomas A Caswell'
    assert third.email == 'tcaswell@bnl.gov'
    assert third.names == ('Thomas A Caswell',)
    assert third.emails == ('tcaswell@bnl.gov',
                            'tcaswell@gmail.com',
                            'tcaswell@uchicago.edu')
    assert last.name == 'joydeep bhattacharjee'
    assert last.email == 'joydeepubuntu@gmail.com'
    assert last.names == ('joydeep bhattacharjee',)
    assert last.emails == ('joydeepubuntu@gmail.com',)

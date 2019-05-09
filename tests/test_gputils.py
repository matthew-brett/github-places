""" Tests for gputils module
"""

import sys
from os.path import join as pjoin, abspath, dirname
from datetime import datetime

HERE = dirname(__file__)
DATA_PATH = pjoin(HERE, 'data')
sys.path.append(abspath(pjoin(HERE, '..')))

from gputils import (Repo, parse_shortlog, ordered_unique,
                     emails2gh_user, parse_sl_line, sha2gh_user)

TEST_REPO = Repo('h5py', path=pjoin(DATA_PATH, 'h5py'))


def test_ordered_unique():
    assert ordered_unique([3, 2, 1]) == (3, 2, 1)


def test_sha2gh_user():
    gh_repo = TEST_REPO.gh_repo
    gh_user = sha2gh_user('1a9d0d6868e7279799a208f07e54cc860793e31a', gh_repo)
    assert gh_user is None
    gh_user = sha2gh_user('acb19b07998d4fe61140aa81cae71e663bb19c4a', gh_repo)
    assert gh_user == 'KwatME'
    gh_user = sha2gh_user('0445cd39f427263b2ef015f09f776038bb5b55d0', gh_repo)
    assert gh_user == 'andrewcollette'


def test_sha_prs2gh_user():
    contribs = TEST_REPO.contributors()
    # A simple one commit PR merge
    newton = [c for c in contribs if c.name == 'Jason Newton'][0]
    gh_user = newton.sha_prs2gh_user()
    assert gh_user == 'nevion'
    # First PR is mixed, second is pure
    kirkham = [c for c in contribs if c.name == 'John Kirkham'][0]
    gh_user = kirkham.sha_prs2gh_user()
    assert gh_user == 'jakirkham'


def test_parse_sl_line():
    L = ('bcdd3e7e11b||M Brett, no Ph.D||mb@foo.com||'
         'M Brett, not Ph.D||mb@bar.org||2018-08-28T23:27:25-04:00')
    commit = parse_sl_line(L)
    assert commit.sha == 'bcdd3e7e11b'
    assert commit.c_name == 'M Brett, no Ph.D'
    assert commit.c_email == 'mb@foo.com'
    assert commit.o_name == 'M Brett, not Ph.D'
    assert commit.o_email == 'mb@bar.org'
    assert commit.dt == datetime.fromisoformat('2018-08-28T23:27:25-04:00')


def test_parse_shortlog():
    eg_out = TEST_REPO.cmd_in_repo(
        ['git', 'shortlog', '-n', "--format=%H||%aN||%aE||%an||%ae||%aI"])
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
    for c in contribs:
        tz_total = sum(no for tz, no in c.timezone_counts)
        assert tz_total == len(c.commits)
    first, second, third, last = contribs[0:3] + [contribs[-1]]
    n_commits = [940, 233, 212, 1]
    assert [len(c.commits) for c in (first, second, third, last)] == n_commits
    assert [len(c) for c in (first, second, third, last)] == n_commits
    assert first.name == 'andrewcollette'
    assert first.email == 'andrew.collette@gmail.com'
    assert first.names == ('andrewcollette',)
    assert first.emails == ('andrew.collette@gmail.com',)
    assert first.timezone_counts == (
        ('UTC', 480),
        ('UTC-06:00', 196),
        ('UTC-07:00', 122),
        ('UTC-08:00', 9),
        ('UTC-05:00', 28),
        ('UTC-04:00', 105),
    )
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
    assert last.timezone_counts == (('UTC', 1),)


def test_find_gh_users():
    all_contribs = TEST_REPO.contributors()
    contribs_50 = [c for c in all_contribs if len(c) >= 50]
    assert len(contribs_50) == 5
    gh_users = [c.guess_gh_user() for c in contribs_50]
    assert gh_users == ['andrewcollette', 'andrewcollette', 'tacaswell',
                        'aragilar', 'takluyver']
    assert emails2gh_user(all_contribs[2].emails) is None
    assert emails2gh_user(all_contribs[9].emails) == 'andreabedini'
    assert emails2gh_user(all_contribs[10].emails) is None
    # This one has a + in it:
    # 38358698+stanwest@users.noreply.github.com
    assert emails2gh_user(all_contribs[22].emails) == 'stanwest'



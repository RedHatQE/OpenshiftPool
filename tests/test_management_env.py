import os
import shutil

import pytest

from openshift_pool.openshift.management_env import ManagementEnv, PickleShelf
from openshift_pool.env import config_workspace_as_cwd


TEST_FILES = ['a.txt', 'b.yaml', 'c.config']


config_workspace_as_cwd()


@pytest.yield_fixture(scope='module')
def mgmt_env():
    mgmt_e = ManagementEnv('some-mgmt-env')
    yield mgmt_e
    # In case that the deletion test failed - cleaning up:
    if os.path.isdir(mgmt_e.path):
        shutil.rmtree(mgmt_e.path)


@pytest.fixture(scope='module')
def pickle_shelf(mgmt_env):
    return PickleShelf(os.path.join(mgmt_env.path, '.metadata'))


def test_mgmt_env_create(mgmt_env):
    mgmt_env.create()
    assert os.path.isdir(mgmt_env.path)


def test_pickle_shelf_exists(pickle_shelf):
    assert os.path.exists(pickle_shelf.path)


def test_pickle_shelf_rw(pickle_shelf, mgmt_env):
    pickle_shelf['a'] = 1
    pickle_shelf['b'] = {'foo': 1}
    pickle_shelf['mgmt_env'] = mgmt_env
    pickle_shelf.save()
    pickle_shelf_new = PickleShelf(os.path.join(mgmt_env.path, '.metadata'))
    assert pickle_shelf_new == {'a': 1, 'b': {'foo': 1}, 'mgmt_env': mgmt_env}


def test_mgmt_env_write_file(mgmt_env):
    for tf in TEST_FILES:
        mgmt_env.write_file(tf, tf)  # We are writing the file name as content
    for tf in TEST_FILES:
        ap = mgmt_env.file_abspath(tf)
        assert os.path.exists(ap)
        with open(ap, 'r') as f:
            assert f.read() == tf


def test_mgmt_env_delete(mgmt_env):
    mgmt_env.delete()
    assert not os.path.isdir(mgmt_env.path)

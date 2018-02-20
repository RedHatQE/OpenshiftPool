import os

import pytest

from openshift_pool.openshift.management_env import ManagementEnv


TEST_FILES = ['a.txt', 'b.yaml', 'c.config']


@pytest.fixture(scope='module')
def management_env():
    return ManagementEnv('some-mgmt-env')


def test_mgmt_env_create(management_env):
    management_env.create()
    assert os.path.isdir(management_env.path)


def test_mgmt_env_write_file(management_env):
    for tf in TEST_FILES:
        management_env.write_file(tf, tf)  # We are writing the file name as content
    for tf in TEST_FILES:
        ap = management_env.file_abspath(tf)
        assert os.path.exists(ap)
        with open(ap, 'r') as f:
            assert f.read() == tf


def test_mgmt_env_delete(management_env):
    management_env.delete()
    assert not os.path.isdir(management_env.path)

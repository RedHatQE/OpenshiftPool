'''
Created on Feb 20, 2018

@author: gshefer
'''
import pytest

from openshift_pool.openshift.cluster import OpenshiftClusterFactory
from openshift_pool.env import config_workspace_as_cwd


config_workspace_as_cwd()


@pytest.mark.parametrize('version', ['3.5', '3.6', '3.7'])
def test_openshift_cluster_factory(version):
    cluster = OpenshiftClusterFactory().create('test-cluster-{}'.format(version), 3, version)
    assert cluster.exists
    OpenshiftClusterFactory().delete(cluster)
    assert not cluster.exists

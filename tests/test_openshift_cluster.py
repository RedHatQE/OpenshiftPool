'''
Created on Feb 20, 2018

@author: gshefer
'''
import pytest

from openshift_pool.openshift.cluster import OpenshiftClusterBuilder
from openshift_pool.env import config_workspace_as_cwd
from openshift_pool.exceptions import StackNotFoundException
from openshift_pool.common import NodeType

config_workspace_as_cwd()


@pytest.mark.parametrize('node_types', [
    [NodeType.INFRA, NodeType.COMPUTE, NodeType.COMPUTE],  # For missing master
    [NodeType.MASTER]                                      # For missing at least one compute
])
def test_bad_node_types(node_types):
    with pytest.raises(AssertionError):
        OpenshiftClusterBuilder().create('foo', node_types, '3.7')


@pytest.mark.parametrize('version', ['3.7'])
def test_openshift_cluster_factory(version):
    cluster_name = 'ocp-cluster-{}-test'.format(version)
    try:
        cluster = OpenshiftClusterBuilder().get(cluster_name)
        OpenshiftClusterBuilder().delete(cluster)
        assert not cluster.exists
    except StackNotFoundException:
        pass
    cluster = OpenshiftClusterBuilder().create(
        cluster_name,
        [NodeType.MASTER, NodeType.INFRA, NodeType.COMPUTE, NodeType.COMPUTE],
        version
    )
    assert cluster.exists
    OpenshiftClusterBuilder().delete(cluster)
    assert not cluster.exists

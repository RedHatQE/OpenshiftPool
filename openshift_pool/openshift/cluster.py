from cached_property import cached_property

from openshift_pool.common import Singleton, NodeType
from openshift_pool.openshift.stack import Stack, StackBuilder, StackInstance
from openshift_pool.openshift.templates import templates
from openshift_pool.ansible import run_ansible_playbook
from config import CONFIG_DIR, CONFIG_DATA
from openshift_pool.exceptions import StackNotFoundException, CannotDetectNodeTypeException


class OpenshiftClusterBuilder(object):
    __metaclass__ = Singleton
    NODE_NAME_BASE_PATTERN = 'ocp-{node_type}'
    NODE_NAME_INDEX_PATTERN = '-{n}'

    def _run_pre_install(self, cluster, version):
        cluster.management_env.write_file(
            'pre_install_inventory',
            templates.pre_install_inventory.render(**cluster.stack.hosts_data)
        )
        return run_ansible_playbook(
            'pre_install', cluster.management_env.file_abspath('pre_install_inventory'), extra_vars=dict(
                subscription_username=CONFIG_DATA['subscription_manager']['username'],
                subscription_password=CONFIG_DATA['subscription_manager']['password'],
                pool_id=CONFIG_DATA['subscription_manager']['pool'],
                auth_server=CONFIG_DATA['subscription_manager']['auth_server'],
                ocp_version=version,
                config_dir=CONFIG_DIR
            )
        )

    def _run_install(self, cluster, version):
        cluster.management_env.write_file(
            'install_inventory',
            # TODO: find a better way to label master
            templates.install_inventory.render(
                deployer_host_fqdn=[node.fqdn for node in cluster.nodes if node.type == NodeType.MASTER].pop())
        )
        return run_ansible_playbook(
            'install', cluster.management_env.file_abspath('install_inventory'),
            extra_vars=dict(
                ocp_version=version,
                logs_directory=cluster.management_env.path,
                openshift_master_default_subdomain='apps.{}'.format(cluster.stack.hosts_data['ocp_servers_domain']),
                master_nodes=[node.fqdn for node in cluster.nodes if node.type == NodeType.MASTER],
                infra_nodes=[node.fqdn for node in cluster.nodes if node.type == NodeType.INFRA],
                compute_nodes=[node.fqdn for node in cluster.nodes if node.type == NodeType.COMPUTE]
            )
        )

    def get(self, name):
        """Getting a cluster by name.
        Args:
            :param `str` name: The name of the cluster.
        Raises:
            ClusterNotFoundException
        Returns:
            :rtype `OpenshiftCluster`.
        """
        stack = Stack(name)
        if not stack.exists:
            raise StackNotFoundException(name)
        return OpenshiftCluster(stack, self._fetch_nodes_from_stack_instances(stack))

    def deploy(self, cluster, version):
        """Deploying Openshift on the cluster
        Args:
            :param `OpenshiftCluster` cluster: The Openshift cluster to deploy.
            :param `str` version: The Openshift version to deploy.
        Returns:
            :return `OpenshiftCluster` cluster: The cluster
        """
        result = self._run_pre_install(cluster, version)
        assert result == 0, 'Ansible playbook "{}" returned with status code: {}'.format(
            'pre_install', result)  # TODO: better exception
        result = self._run_install(cluster, version)
        assert result == 0, 'Ansible playbook "{}" returned with status code: {}'.format(
            'install', result)
        return cluster

    def _gen_node_names(self, node_types):
        names = []
        for node_type in node_types:
            base_name = self.NODE_NAME_BASE_PATTERN.format(node_type=node_type.value)
            full_pattern = base_name + self.NODE_NAME_INDEX_PATTERN
            i = 0
            while full_pattern.format(n=i) in names:
                i += 1
            names.append(full_pattern.format(n=i))
        return names

    def _fetch_nodes_from_stack_instances(self, stack):
        nodes = []
        outputs = stack.stack_outputs
        for instance in stack.instances:
            instance_type = next(filter(bool, [
                output.get('output_value')
                for output in outputs
                if output['output_key'] == '{}_instance_type'.format(instance.fqdn.split('.')[0])
            ]))
            node = None
            for node_type in NodeType:
                if instance_type == node_type.value:
                    node = Node(node_type, instance)
                    break
            if not node:
                raise CannotDetectNodeTypeException(instance.fqdn)
            nodes.append(node)
        return nodes

    def create(self, name, node_types, version):
        """Creating a new openshift cluster. Creating the stack and deploy Openshift.
        Args:
            :param `str` name: The name of the cluster.
            :param `list`: List of the node types in the cluster.
                           e.g. [NodeType.MASTER, NodeType.INFRA, NodeType.COMPUTE, NodeType.COMPUTE]
            :param `str` version: The Openshift version to deploy.
        Returns:
            :return `OpenshiftCluster` cluster: The created cluster.
        """
        assert isinstance(name, str)
        assert NodeType.MASTER in node_types, 'Cluster must include at least 1 master'
        assert any(filter(lambda t: t in node_types, [NodeType.INFRA, NodeType.COMPUTE])), \
            'Cluster must include at least 1 additional node except master'
        stack = StackBuilder().create(name, self._gen_node_names(node_types), node_types)
        cluster = OpenshiftCluster(stack, self._fetch_nodes_from_stack_instances(stack))
        self.deploy(cluster, version)
        return cluster

    def delete(self, cluster):
        """Deleting the cluster and the stack"""
        return StackBuilder().delete(cluster.stack)


class Node(object):
    def __init__(self, node_type, stack_instance):
        assert isinstance(node_type, NodeType)
        assert isinstance(stack_instance, StackInstance)
        self._type = node_type
        self._stack_instance = stack_instance

    @property
    def fqdn(self):
        return self.stack_instance.fqdn

    @property
    def type(self):
        return self._type

    @property
    def stack_instance(self):
        return self._stack_instance


class OpenshiftCluster(object):

    def __init__(self, stack, nodes):
        assert isinstance(stack, Stack)
        assert all(isinstance(node, Node) for node in nodes)
        self._stack = stack
        self._nodes = nodes

    @cached_property
    def stack(self):
        return self._stack

    @cached_property
    def nodes(self):
        return self._nodes

    @property
    def exists(self):
        return self.stack.exists

    @property
    def management_env(self):
        return self.stack.management_env

    def status(self):
        pass  # TODO: implement status checking of the cluster (stack exists, connections, ocp running, etc.)

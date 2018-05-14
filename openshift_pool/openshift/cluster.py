import os
import re
from datetime import datetime

from cached_property import cached_property

from config import CONFIG_DIR, CONFIG_DATA
from openshift_pool.common import Singleton, NodeType, Loggable
from openshift_pool.openshift.stack import Stack, StackBuilder, StackInstance
from openshift_pool.openshift.templates import templates
from openshift_pool.playbooks import run_ansible_playbook
from openshift_pool.exceptions import StackNotFoundException, CannotDetectNodeTypeException
from openshift_pool.openshift.management_env import PickleShelf


class OpenshiftClusterBuilder(Loggable, metaclass=Singleton):
    NODE_NAME_BASE_PATTERN = 'ocp-{node_type}'
    NODE_NAME_INDEX_PATTERN = '-{n}'
    SUPPORTED_VERSIONS = ['3.5', '3.6', '3.7', '3.9']

    def __init__(self):
        Loggable.__init__(self)

    def _run_pre_install(self, cluster, version):
        """Running the pre-installation ansible tasks.
            @param cluster: `OpenshiftCluster`
            @param version: `str` the openshift version for the pre-installation.
        """
        self.log.info(f'Running pre-installation ansible script on cluster {cluster.name}.')
        cluster.mgmt_env.write_file(
            'pre_install_inventory',
            templates.pre_install_inventory.render(**cluster.stack.hosts_data)
        )
        return run_ansible_playbook(
            'pre_install', cluster.mgmt_env.file_abspath('pre_install_inventory'), self.log, extra_vars=dict(
                subscription_username=CONFIG_DATA['subscription_manager']['username'],
                subscription_password=CONFIG_DATA['subscription_manager']['password'],
                pool_id=CONFIG_DATA['subscription_manager']['pool'],
                auth_server=CONFIG_DATA['subscription_manager']['auth_server'],
                ocp_version=version,
                config_dir=CONFIG_DIR
            )
        )

    def _run_install(self, cluster, version):
        """Running the installation ansible tasks.
            @param cluster: `OpenshiftCluster`
            @param version: `str` the openshift version for the installation.
        """
        self.log.info(f'Running installation ansible script on cluster {cluster.name}.')
        cluster.mgmt_env.write_file(
            'install_inventory',
            templates.install_inventory.render(
                deployer_host_fqdn=[node.fqdn for node in cluster.nodes if node.type == NodeType.MASTER].pop())
        )
        return run_ansible_playbook(
            'install', cluster.mgmt_env.file_abspath('install_inventory'), self.log,
            extra_vars=dict(
                ocp_version=version,
                logs_directory=cluster.mgmt_env.path,
                openshift_master_default_subdomain='apps.{}'.format(cluster.stack.hosts_data['ocp_servers_domain']),
                master_nodes=[node.fqdn for node in cluster.nodes if node.type == NodeType.MASTER],
                infra_nodes=[node.fqdn for node in cluster.nodes if node.type == NodeType.INFRA],
                compute_nodes=[node.fqdn for node in cluster.nodes if node.type == NodeType.COMPUTE]
            )
        )

    def _fetch_nodes_from_stack_instances(self, stack):
        """Fetching the nodes from the stack outputs.
            @param stack: (`Stack`) the stack to fetch from.
            @rtype: (`list' of `Node`)
        """
        self.log.info(f'Fetching nodes from {stack.name} instances')
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
        self.log.debug(f'Fetched Nodes: {[node.type.value for node in nodes]}')
        return nodes

    def _create_metadata(self, cluster):
        """Building the metadata for the new created cluster.
            @param cluster: `OpenshiftCluster`
        """
        cluster.metadata['resource_type'] = 'OpenshiftCluster'
        cluster.metadata['name'] = cluster.name
        cluster.metadata['created_at'] = datetime.now()
        cluster.metadata['owner'] = None
        # cluster.metadata['version'] = cluster.version
        # cluster.metadata['xy_version'] = cluster.xy_version
        cluster.metadata['flavor'] = CONFIG_DATA['openstack']['parameters']['flavor']
        cluster.metadata.save()

    def gen_node_names(self, node_types):
        """Generate node names from node types.
            @param node_types: (`list`) of `NodeType` the node types
            @rtype: (`list` of `str`)
        """
        names = []
        for node_type in node_types:
            base_name = self.NODE_NAME_BASE_PATTERN.format(node_type=node_type.value)
            full_pattern = base_name + self.NODE_NAME_INDEX_PATTERN
            i = 0
            while full_pattern.format(n=i) in names:
                i += 1
            names.append(full_pattern.format(n=i))
        return names

    def get(self, name):
        """Getting a cluster by name.
            @param name: (`str`) The name of the cluster.
            @raise ClusterNotFoundException: When the cluster not found.
            @rtype: `OpenshiftCluster`.
        """
        self.log.debug(f'Getting a cluster by name: name={name}')
        stack = Stack(name)
        if not stack.create_complete and not stack.create_failed:
            raise StackNotFoundException(name)
        return OpenshiftCluster(stack, self._fetch_nodes_from_stack_instances(stack))

    def deploy(self, cluster, version):
        """Deploying Openshift on the cluster
            @param cluster: (`OpenshiftCluster`) The Openshift cluster to deploy.
            @param version: (`str`) The Openshift version to deploy.
            @rtype: `OpenshiftCluster`
        """
        self.log.info(f'Deploying openshift cluster: {cluster.name} version={version}')
        result = self._run_pre_install(cluster, version)
        assert result == 0, 'Ansible playbook "{}" returned with status code: {}'.format(
            'pre_install', result)  # TODO: better exception
        result = self._run_install(cluster, version)
        assert result == 0, 'Ansible playbook "{}" returned with status code: {}'.format(
            'install', result)
        return cluster

    def create(self, name, node_types, version):
        """Creating a new openshift cluster. Creating the stack and deploy Openshift.
            @param name: (`str`) The name of the cluster.
            @param node_types: (`list` of `NodeType`)  List of the node types in the cluster.
                           e.g. [NodeType.MASTER, NodeType.INFRA, NodeType.COMPUTE, NodeType.COMPUTE]
            @param version: (`str`) The Openshift version to deploy.
            @rtype: `OpenshiftCluster`.
        """
        assert isinstance(name, str)
        assert NodeType.MASTER in node_types, 'Cluster must include at least 1 master'
        assert any(filter(lambda t: t in node_types, [NodeType.INFRA, NodeType.COMPUTE])), \
            'Cluster must include at least 1 additional node except master'
        self.log.info(f'Creating cluster: {name} node_types={[t.value for t in node_types]}; version={version}')
        stack = StackBuilder().create(name, self.gen_node_names(node_types), node_types)
        cluster = OpenshiftCluster(stack, self._fetch_nodes_from_stack_instances(stack))
        self._create_metadata(cluster)
        self.deploy(cluster, version)
        return cluster

    def delete(self, cluster):
        """Deleting the cluster and the stack
            @param cluster: (`OpenshiftCluster`)
            @rtype: `Stack`
        """
        self.log.info(f'Deleting cluster: {cluster.name}')
        return StackBuilder().delete(cluster.stack)


class Node(object):
    """This class represents a Node.

    It contains all the function and properties that related to specific node.
    """

    def __init__(self, node_type: NodeType, stack_instance: StackInstance):
        """
        @param node_type: `NodeType` The type of the node.
        @param stack: `StackInstance` The stack instance.
        """
        assert isinstance(node_type, NodeType)
        assert isinstance(stack_instance, StackInstance)
        self._type = node_type
        self._stack_instance = stack_instance

    @property
    def ssh(self):
        return self._stack_instance.ssh

    @property
    def fqdn(self):
        return self._stack_instance.fqdn

    @property
    def type(self):
        return self._type

    @property
    def stack_instance(self):
        return self._stack_instance


class OpenshiftCluster(object):
    """
    The openshift cluster class.

    It contains all the related function and properties of the cluster.
    """

    def __init__(self, stack: Stack, nodes: list):
        """
        @param stack: `Stack` The stack.
        @param param: `list` of `Node` The nodes of the cluster.
        """
        assert isinstance(stack, Stack)
        assert all(isinstance(node, Node) for node in nodes)
        self._stack = stack
        self._nodes = nodes

    def __repr__(self):
        return '<{} name="{}"; node_types="{}">'.format(
            self.__class__.__name__, self.name, [t.type.value for t in self.nodes])

    @property
    def name(self):
        return self.stack.name

    @property
    def master_nodes(self):
        return [node for node in self.nodes if node.type == NodeType.MASTER]

    @property
    def version(self):
        raw_ver = str(self.master_nodes[0].ssh.exec_command('oc version')[1].read())
        return re.search(r'oc v([\d\.]+)', raw_ver).group(1)

    @property
    def xy_version(self):
        return '.'.join(self.version.split('.')[:2])

    @cached_property
    def metadata(self):
        return PickleShelf(os.path.join(self.mgmt_env.path, '.metadata'))

    @property
    def stack(self):
        return self._stack

    @property
    def nodes(self):
        return self._nodes

    @property
    def create_complete(self):
        return self.stack.create_complete

    @property
    def delete_complete(self):
        return self.stack.delete_complete

    @property
    def exists(self):
        return self.stack.create_complete

    @property
    def mgmt_env(self):
        return self.stack.mgmt_env

    def status(self):
        pass  # TODO: implement status checking of the cluster (stack exists, connections, ocp running, etc.)

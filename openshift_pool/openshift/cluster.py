from openshift_pool.common import Singleton
from openshift_pool.openshift.stack import Stack, StackFactory
from openshift_pool.openshift.templates import templates
from openshift_pool.ansible import run_ansible_playbook
from config import CONFIG_DIR, CONFIG_DATA


class OpenshiftClusterFactory(object):
    __metaclass__ = Singleton

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
                master_fqdn=cluster.stack.hosts_data['host_names']['ocp_master'])
        )
        return run_ansible_playbook(
            'install', cluster.management_env.file_abspath('install_inventory'),
            extra_vars=dict(
                logs_directory=cluster.management_env.path,
                openshift_master_default_subdomain='apps.{}'.format(cluster.stack.hosts_data['ocp_servers_domain']),
                ocp_version=version, master_host=cluster.stack.hosts_data['host_names']['ocp_master'],
                infra_node=cluster.stack.hosts_data['host_names']['ocp_node0'],
                primary_nodes=[
                    v for k, v in cluster.stack.hosts_data['host_names'].items() if k not in ('ocp_master', 'ocp_node0')
                ]
            )
        )

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

    def create(self, name, number_of_nodes, version):
        """Creating a new openshift cluster. Creating the stack and deploy Openshift.
        Args:
            :param `str` name: The name of the cluster.
            :param `int` number_of_nodes: Number of nodes of the cluster.
            :param `str` version: The Openshift version to deploy.
        Returns:
            :return `OpenshiftCluster` cluster: The created cluster.
        """
        stack = StackFactory().create(name, number_of_nodes)
        cluster = OpenshiftCluster(stack)
        self.deploy(cluster, version)
        return cluster

    def delete(self, cluster):
        """Deleting the cluster and the stack"""
        return StackFactory().delete(cluster.stack)


class OpenshiftCluster(object):

    def __init__(self, stack):
        assert isinstance(stack, Stack)
        self.stack = stack

    @property
    def exists(self):
        return self.stack.exists

    @property
    def management_env(self):
        return self.stack.management_env

    def status(self):
        pass  # TODO: implement status checking of the cluster (stack exists, connections, ocp running, etc.)

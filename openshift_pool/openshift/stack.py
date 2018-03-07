import os

from cached_property import cached_property
import keystoneclient.v2_0.client as ksclient
from heatclient.client import Client

from config import CONFIG_DATA
from openshift_pool.openshift.templates import templates
from openshift_pool.common import run_command, Singleton
from openshift_pool.exceptions import (StackNotFoundException,
                                       NameServerUpdateException,
                                       StackAlreadyExistsException)
from openshift_pool.openshift.management_env import ManagementEnv


class StackBuilder(object):
    __metaclass__ = Singleton

    @cached_property
    def config_data(self):
        return CONFIG_DATA['openstack']

    @cached_property
    def heat_client(self):
        keystone = ksclient.Client(
            username=self.config_data['username'],
            password=self.config_data['password'],
            auth_url=self.config_data['auth_url'],
            tenant_name=self.config_data['tenant_name']
        )
        heat_url = keystone.service_catalog.url_for(
            service_type='orchestration', endpoint_type='publicURL')
        return Client('1', endpoint=heat_url, token=keystone.auth_token)

    def _config_domains(self, stack, method, check_connection_attempts=10):
        """
        Either create or delete domains for the stack.
            :param:'str' method: either 'create' or 'delete'
        """
        assert method in ('create', 'delete')
        hosts_data = stack.hosts_data
        nsupdate_name = '{}_domains'.format(method)
        nsupdate_path = stack.management_env.file_abspath(nsupdate_name)
        stack.management_env.write_file(nsupdate_path, getattr(templates, nsupdate_name).render(**hosts_data))
        assert run_command(['nsupdate', nsupdate_path])
        check_connection_attempts = 1
        while check_connection_attempts < 10:
            connection_statuses = stack.get_connection_statuses()
            if (
                method == 'create' and all(connection_statuses.values()) or
                method == 'delete' and not any(connection_statuses.values())
                    ):
                return
        raise NameServerUpdateException(self.name)

    def _create_domains(self, stack):
        return self._config_domains(stack, 'create')

    def _delete_domains(self, stack):
        return self._config_domains(stack, 'delete')

    def create(self, name, number_of_nodes):
        params = {}

        params['stack_name'] = name
        params['number_of_nodes'] = number_of_nodes
        params.update(self.config_data)

        stack = Stack(name, number_of_nodes)
        if stack.exists:
            raise StackAlreadyExistsException(stack.name)

        stack.management_env.write_file('ocp_stack.yaml', templates.ocp_stack.render(params=params))
        stack.management_env.write_yaml('stack_params.yaml', {'parameters': self.config_data['parameters']})
        # TODO: self.heat_client.stacks.create(stack_name=self.name, template=yaml.load())
        run_command(' '.join([
            'openstack', 'stack', 'create', '--wait', '-e', 'stack_params.yaml',
            '--template ocp_stack.yaml',
            '--os-auth-url={auth_url}',
            '--os-project-name={project_name}',
            '--os-tenant-name={tenant_name}',
            '--os-username={username}',
            '--os-password={password}',
            '--os-tenant-id={tenant_id}',
            '--os-region-name={region_id}',
            '{stack_name}'
        ]).format(**params).split(' '), cwd=stack.management_env.path)
        self._create_domains(stack)
        return stack

    def delete(self, stack):
        assert isinstance(stack, Stack)
        self._delete_domains(stack)
        stack.stack.delete()
        stack.management_env.delete()


class Stack(object):
    """
    Stack class contains all the required functionality to manage the stack.
    Args:
        :param:`str` name: The name of the stack
        :param:`int` number_of_nodes: The number of nodes.
    """

    def __init__(self, name, number_of_nodes):
        self._name = name
        self._number_of_nodes = number_of_nodes

    @cached_property
    def heat_client(self):
        return StackBuilder().heat_client

    @property
    def name(self):
        return self._name

    @property
    def number_of_nodes(self):
        return self._number_of_nodes

    @cached_property
    def management_env(self):
        """Return the management env of the stack"""
        management_env = ManagementEnv(self.name)
        if not os.path.isdir(management_env.path):
            management_env.create()
        return management_env

    @cached_property
    def config_data(self):
        return CONFIG_DATA['openstack']

    @property
    def stack(self):
        if hasattr(self, '_stack'):
            return self._stack
        the_stack = next((s for s in self.heat_client.stacks.list()
                          if s.stack_name == self.name), None)
        if the_stack:
            self._stack = the_stack
        return the_stack

    @property
    def exists(self):
        if not self.stack:
            return False
        self.stack.get()
        return 'DELETE' not in self._stack.stack_status

    @cached_property
    def stack_outputs(self):
        if not self.exists:
            raise StackNotFoundException(self.name)

        self.stack.get()  # We won't get the outputs if we won't do not do this.
        return self.stack.outputs

    @cached_property
    def hosts_data(self):
        outputs = self.stack_outputs

        host_ips = {
            o["output_key"].split("_public_ip")[0]: o["output_value"]
            for o in outputs if o["output_key"].endswith("_public_ip")
        }
        host_names = {
            o["output_key"].split("_name")[0]: o["output_value"]
            for o in outputs if o["output_key"].endswith("_name")
        }
        ocp_deployment_pqdn = next(
            o["output_value"] for o in outputs
            if o["output_key"] == "ocp_deployment_pqdn")

        ocp_servers_domain = "{}.{}".format(
            ocp_deployment_pqdn, CONFIG_DATA['openstack']['dns_zone'])

        return {
            'host_ips': host_ips,
            'host_names': host_names,
            'ocp_deployment_pqdn': ocp_deployment_pqdn,
            'ocp_servers_domain': ocp_servers_domain
        }

    def get_connection_statuses(self):
        """Return a LUT that contains each node and its connectivity by the domain"""
        out = {}
        for hostname in self.hosts_data['host_names'].values():
            out[hostname] = bool(run_command(
                ['ping', '-c', '1', hostname]))
        return out

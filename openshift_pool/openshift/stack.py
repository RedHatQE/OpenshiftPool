import os
import subprocess as sp
import json
import paramiko

from cached_property import cached_property
import keystoneclient.v2_0.client as ksclient
from heatclient.client import Client
from wait_for import wait_for

from config import CONFIG_DATA, CONFIG_DIR
from openshift_pool.openshift.templates import templates
from openshift_pool.common import Singleton, NodeType
from openshift_pool.exceptions import (StackNotFoundException,
                                       NameServerUpdateException,
                                       StackAlreadyExistsException)
from openshift_pool.openshift.management_env import ManagementEnv
from openshift_pool.playbooks import run_ansible_playbook


class StackBuilder(object):
    __metaclass__ = Singleton

    @cached_property
    def config_data(self):
        return CONFIG_DATA['openstack']

    @cached_property
    def keystone_client(self):
        return ksclient.Client(
            username=self.config_data['username'],
            password=self.config_data['password'],
            auth_url=self.config_data['auth_url'],
            tenant_name=self.config_data['tenant_name']
        )

    @cached_property
    def heat_client(self):
        heat_url = self.keystone_client.service_catalog.url_for(
            service_type='orchestration', endpoint_type='publicURL')
        return Client('1', endpoint=heat_url, token=self.keystone_client.auth_token)

    def _config_domains(self, stack, method, check_connection_attempts=10):
        """
        Either create or delete domains for the stack.
            @param stack: ('Stack') The stack
            @param method: ('str') either 'create' or 'delete'
        """
        assert isinstance(stack, Stack)
        assert method in ('create', 'delete')
        hosts_data = stack.hosts_data
        infra_hosts = [hosts_data['host_ips'][name] for name in hosts_data['host_ips'].keys()
                       if hosts_data['instance_types'][name] == NodeType.INFRA.value]
        if not infra_hosts:
            infra_hosts = [hosts_data['host_ips'][name] for name in hosts_data['host_ips'].keys()
                           if hosts_data['instance_types'][name] == NodeType.MASTER.value]
        hosts_data['apps_subdomain_ip'] = infra_hosts.pop()
        nsupdate_name = '{}_domains'.format(method)
        nsupdate_path = stack.mgmt_env.file_abspath(nsupdate_name)
        stack.mgmt_env.write_file(nsupdate_path, getattr(templates, nsupdate_name).render(**hosts_data))
        nsupdate_results = sp.run(['nsupdate', nsupdate_path])
        assert not nsupdate_results.returncode, 'nsupdate failed: {}'.format(nsupdate_results.stdout)
        connection_attempts = 1
        while connection_attempts < check_connection_attempts:
            connection_statuses = stack.get_connection_statuses()
            if (
                method == 'create' and all(connection_statuses.values()) or
                method == 'delete' and not any(connection_statuses.values())
                    ):
                return
            connection_attempts += 1
        raise NameServerUpdateException(stack.name)

    def _create_domains(self, stack):
        return self._config_domains(stack, 'create')

    def _delete_domains(self, stack):
        return self._config_domains(stack, 'delete')

    def is_stack(self, name):
        """Return whether the stack with the given name exists"""
        return Stack(name).create_complete

    def exchange_keys(self, stack):
        """Exchanging the keys to the stack instances.
            @param stack: `Stack`
        """
        stack.mgmt_env.write_file(
            'exchange_keys_inventory',
            templates.pre_install_inventory.render(**stack.hosts_data)
        )
        return run_ansible_playbook(
            'exchange_keys', stack.mgmt_env.file_abspath('exchange_keys_inventory'), extra_vars=dict(
                config_dir=CONFIG_DIR
            )
        )

    def create(self, name, instance_names, instance_types):
        assert isinstance(name, str)
        assert len(instance_names) == len(instance_types)
        assert NodeType.MASTER in instance_types, 'Stack must include master instance'

        params = {}

        params['stack_name'] = name
        params['instances'] = list(zip(instance_names, [t.value for t in instance_types]))
        params.update(self.config_data['parameters'])
        params.update(self.config_data)

        stack = Stack(name)
        if stack.create_complete:
            raise StackAlreadyExistsException(stack.name)

        stack.mgmt_env.write_file('ocp_stack.yaml', templates.ocp_stack.render(params=params))
        template = stack.mgmt_env.read_yaml('ocp_stack.yaml')
        template['heat_template_version'] = template['heat_template_version'].strftime('%Y-%m-%d')
        self.heat_client.stacks.create(stack_name=stack.name, template=json.dumps(template))
        wait_for(lambda s: s.create_complete, [stack], delay=10, timeout=300)
        self._create_domains(stack)
        self.exchange_keys(stack)
        return stack

    def delete(self, stack):
        assert isinstance(stack, Stack)
        self._delete_domains(stack)
        stack.stack.delete()
        wait_for(lambda s: s.delete_complete, func_args=[stack], delay=10, timeout=120)
        stack.mgmt_env.delete()


class StackInstance(object):

    def __init__(self, fqdn):
        self.fqdn = fqdn

    @cached_property
    def ssh(self):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(self.fqdn, username='root')
        return client


class Stack(object):
    """
    Stack class contains all the required functionality to manage the stack.
        @param name: (`str`) The name of the stack
    """

    def __init__(self, name):
        self._name = name
        self._stack = None

    @cached_property
    def heat_client(self):
        return StackBuilder().heat_client

    @cached_property
    def name(self):
        return self._name

    @cached_property
    def instances(self):
        return [StackInstance(fqdn) for fqdn in self.hosts_data['host_names'].values()]

    @cached_property
    def number_of_instances(self):
        return len(self._instances)

    @cached_property
    def mgmt_env(self):
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
        if not self._stack:
            self._stack = next((s for s in self.heat_client.stacks.list()
                                if s.stack_name == self.name), None)
        return self._stack

    @property
    def status(self):
        if not self.stack:
            return
        self.stack.get()
        return self._stack.stack_status.upper()

    @property
    def create_complete(self):
        return 'CREATE_COMPLETE' == self.status or False

    @property
    def delete_complete(self):
        return 'DELETE_COMPLETE' == self.status or False

    @property
    def stack_outputs(self):
        if not self.create_complete:
            raise StackNotFoundException(self.name)

        self.stack.get()  # We won't get the outputs if we won't do not do this.
        return self.stack.outputs

    @property
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

        instance_types = {
            o["output_key"].split("_instance_type")[0]: o["output_value"]
            for o in outputs if o["output_key"].endswith("_instance_type")
        }

        return {
            'host_ips': host_ips,
            'host_names': host_names,
            'ocp_deployment_pqdn': ocp_deployment_pqdn,
            'ocp_servers_domain': ocp_servers_domain,
            'instance_types': instance_types
        }

    def get_connection_statuses(self):
        """Return a LUT that contains each node and its connectivity by the domain"""
        out = {}
        for hostname in self.hosts_data['host_names'].values():
            out[hostname] = not sp.run(
                ['ping', '-c', '1', hostname]).returncode
        return out

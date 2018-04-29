import re
import argparse

from openshift_pool.openshift.cluster import OpenshiftClusterBuilder
from openshift_pool.env import config_workspace_as_cwd
from openshift_pool.common import NodeType, pgrep, set_proc_name
from openshift_pool.openshift.stack import StackBuilder


config_workspace_as_cwd()
PROCESS_NAME = 'openshiftdeployer'


parser = argparse.ArgumentParser()


operation_subparser = parser.add_subparsers(dest='operation', help='operation')

create_parser = operation_subparser.add_parser('create', help='Creating a cluster stack without deploy')
create_parser.add_argument('cluster_name', action='store', help='The name of the cluster')
create_parser.add_argument('node_types', action='store',
                           help='The type of type nodes, all of them should be master, infra or compute')

deploy_parser = operation_subparser.add_parser('deploy', help='Deploying a cluster')
deploy_parser.add_argument('cluster_name', action='store', help='The name of the cluster')
deploy_parser.add_argument('node_types', action='store',
                           help='The type of type nodes, all of them should be master, infra or compute')
deploy_parser.add_argument('version', action='store', help='The openshift version to deploy')

delete_parser = operation_subparser.add_parser('delete', help='Deleting a cluster')
delete_parser.add_argument('cluster_name', action='store', help='The name of the cluster')
delete_parser.add_argument('-f', '--force', dest='force', required=False, action='store_true',
                           help='Force operation without prompt')


def parse_commend(namespace):
    if namespace.operation in ('create', 'deploy'):
        try:
            node_types = [next(nt for nt in NodeType if nt.value == node_type.lower())
                          for node_type in namespace.node_types.split(',')]
        except StopIteration:
            print(f'Node types are invalid! {namespace.node_types.split(",")}')
            return

        for node_type in NodeType:
            if node_type not in node_types:
                print(f'Cluster must include at least one `{node_type.value}` node!')
                return

        if StackBuilder().is_stack(namespace.cluster_name):
            print(f'Cluster with the given name "{namespace.cluster_name}" is already exists!')
            return

        if namespace.operation == 'deploy':

            version = re.match('\d\.\d', namespace.version)
            if not version or version.group() not in OpenshiftClusterBuilder().SUPPORTED_VERSIONS:
                print(f'Unsupported version: {version.group()}. '
                      f'Supported versions: {", ".join(OpenshiftClusterBuilder().SUPPORTED_VERSIONS)}')
                return

            cluster = OpenshiftClusterBuilder().create(
                namespace.cluster_name, node_types, namespace.version
            )
            print('Openshift cluster has successfully deployed.')
            print('-'*50)
            print(cluster.master_nodes[0].ssh.exec_command('oc version')[1].read())
            print('Nodes:')
            print(cluster.master_nodes[0].ssh.exec_command('oc get nodes')[1].read())
            print('-'*50)

        elif namespace.operation == 'create':
            print(f'Creating stack {namespace.cluster_name}.')
            stack = StackBuilder().create(
                namespace.cluster_name, OpenshiftClusterBuilder().gen_node_names(node_types), node_types)
            print('\nStack has successfully created.')
            print('-'*50)
            for node in stack.instances:
                print(node.fqdn)
            print('-'*50)

    if namespace.operation == 'delete':
        cluster = OpenshiftClusterBuilder().get(namespace.cluster_name)
        if namespace.force and input(
                f'Are you sure you want to delete cluster {namespace.cluster_name}? (y/n) ').lower() != 'y':
            print('Canceling operation.')
            return
        OpenshiftClusterBuilder().delete(cluster)
        print(f'\nCluster {namespace.cluster_name} has been successfully deleted.')


def main():
    if pgrep(PROCESS_NAME):
        print('Can only run 1 process at once.')
        return
    set_proc_name(PROCESS_NAME.encode())
    parse_commend(parser.parse_args())


if __name__ == '__main__':
    main()

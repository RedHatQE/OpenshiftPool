import re
import argparse

from openshift_pool.openshift.cluster import OpenshiftClusterBuilder
from openshift_pool.env import config_workspace_as_cwd
from openshift_pool.common import NodeType
from openshift_pool.openshift.stack import StackBuilder


config_workspace_as_cwd()


parser = argparse.ArgumentParser()


operation_subparser = parser.add_subparsers(dest='operation', help='operation')

deploy_parser = operation_subparser.add_parser('deploy', help='Deploying a cluster')
deploy_parser.add_argument('cluster_name', action='store', help='The name of the cluster')
deploy_parser.add_argument('version', action='store', help='The openshift version to deploy')
deploy_parser.add_argument('node_types', action='store',
                           help='The type of type nodes, all of them should be master, infra or compute')

delete_parser = operation_subparser.add_parser('delete', help='Deleting a cluster')
delete_parser.add_argument('cluster_name', action='store', help='The name of the cluster')
delete_parser.add_argument('-f', '--force', dest='force', required=False, action='store_true',
                           help='Force operation without prompt')


def parse_commend(namespace):
    if namespace.operation == 'deploy':
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
        print(cluster.ssh.exec_command('oc version')[1].read())
        print('Nodes:')
        print(cluster.ssh.exec_command('oc get nodes')[1].read())

    if namespace.operation == 'delete':
        cluster = OpenshiftClusterBuilder().get(namespace.cluster_name)
        if namespace.force and input(
                f'Are you sure you want to delete cluster {namespace.cluster_name}? (y/n) ').lower() != 'y':
            print('Canceling operation.')
            return
        OpenshiftClusterBuilder().delete(cluster)
        print(f'Cluster {namespace.cluster_name} has successfully deleted.')


def main():
    print(parse_commend(parser.parse_args()))


if __name__ == '__main__':
    main()

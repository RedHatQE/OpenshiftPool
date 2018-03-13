from openshift_pool.common import Singleton
from openshift_pool.openshift.stack import StackBuilder
from openshift_pool.openshift.cluster import OpenshiftClusterBuilder
from openshift_pool.db import DB


class PoolManager(metaclass=Singleton):
    StackBuilder = StackBuilder()
    ClusterBuilder = OpenshiftClusterBuilder()

    def __init__(self):
        self._clusters = []
        self.db = DB().pool_manager
        if self.db.find_one() is None:
            self.db.insert_one({
                'clusters': []
            })
        self.reload()

    @property
    def heat_client(self):
        return self.StackBuilder.heat_client

    @property
    def clusters(self):
        return self._clusters

    def reload(self):
        self._clusters = []
        for cluster_data in self.db.find_one()['clusters']:
            self._clusters.append(
                self.ClusterBuilder.get(cluster_data['name'])
            )

    def save(self):
        self.db.update_one({}, {'$set': {'clusters': [{'name': c.name} for c in self._clusters]}})

    def _create_cluster(self, name, version, node_types):
        cluster = self.ClusterBuilder.create(name, node_types, version)
        self._clusters.append(cluster)
        self.save()
        return cluster

    def _delete_stack(self, cluster):
        self._clusters.remove(cluster)
        self.ClusterBuilder.delete(cluster)

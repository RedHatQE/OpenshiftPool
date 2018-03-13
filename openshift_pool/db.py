from pymongo.mongo_client import MongoClient
from bson import _ENCODERS as bson_encoders

from openshift_pool.common import Singleton


class DB(metaclass=Singleton):
    bson_types = tuple(bson_encoders.keys())

    def __init__(self):
        self.client = MongoClient()

    def __getattr__(self, name):
        return getattr(self.client.db, name)

    @classmethod
    def bson_encode(cls, node):
        """Verifying that all the object in the dict node are bson encodable.
        The once that are not, converted to str"""
        if isinstance(node, dict):
            result = {}
            for key, value in node.items():
                result[key] = cls.bson_encode(value)
        elif isinstance(node, (list, tuple)):
            result = []
            for item in node:
                result.append(cls.bson_encode(item))
        elif isinstance(node, cls.bson_types):
            result = node
        else:
            result = str(node)
        return result

import os
import shutil

import yaml
import pickle

from openshift_pool.env import ENV
from openshift_pool.exceptions import ManagementEnvAlreadyExists
from openshift_pool.common import Loggable


class PickleShelf(dict):
    """
    A basic pickle shelf to store objects and metadata.
        @param path: `str` The pth of the pickle file.
    """
    def __init__(self, path):
        self._path = path
        if os.path.exists(self._path):
            self.reload()
        else:
            self.save()
        dict.__init__(self)

    @property
    def path(self):
        return self._path

    def reload(self):
        with open(self._path, 'rb') as f:
            obj = pickle.load(f)
        self.update(obj)

    def save(self):
        with open(self._path, 'wb') as f:
            pickle.dump(self, f)


class ManagementEnv(Loggable):
    """
    This class represents the directory which all the logs, data, metadata of each cluster.
    It used to keep isolated env for each one so the logs will be saved under its directory.
    It has set of utility functions that help to manage the environment directory of the cluster
    """
    def __init__(self, dirname):
        self._dirname = dirname
        Loggable.__init__(self, f'{self.file_abspath("log.log")}')

    def __repr__(self):
        return '<{} {}>'.format(self.__class__.__name__, self._dirname)

    def __eq__(self, other):
        return getattr(other, 'path', None) == self.path

    @property
    def path(self):
        """Return the absolute path of the management env directory"""
        return os.path.join(ENV['WORKSPACE'], self._dirname)

    def create(self):
        """Creating the management env directory.
            @raise ManagementEnvAlreadyExists: If the folder already exists.
        """
        if os.path.isdir(self.path):
            raise ManagementEnvAlreadyExists(self.path)
        os.mkdir(self.path)

    def delete(self):
        """Deleting the management env directory."""
        shutil.rmtree(self.path)

    def clear(self):
        """Deleting all the content of the management env directory.
        (In practice, deleting the folder and recreate it)"""
        self.delete()
        self.create()

    def file_abspath(self, filename):
        """Returns the absolute path of a filename in the management env directory"""
        return os.path.join(self.path, filename)

    def write_file(self, filename, content):
        """Writing the content to the file in the management env directory.
            @param filename: `str` The file name.
            @param content: `str` The file content.
        """
        self.log.info(f'Writing file: {filename}')
        with open(self.file_abspath(filename), 'w') as f:
            f.write(content)

    def write_yaml(self, filename, data):
        """Writing a yaml file with data in the management env directory.
            @param filename: `str` The file name.
            @param content: `dict` The yaml data.
        """
        return self.write_file(filename, yaml.dump(data, default_flow_style=False))

    def read_file(self, filename):
        """Returns the data of the yaml file
            @param filename: `str` The file name.
            @rtype: str
        """
        with open(self.file_abspath(filename), 'r') as f:
            return f.read()

    def read_yaml(self, filename):
        """Returns the data of the yaml file
            @param filename: `str` The file name.
            @rtype: dict
        """
        return yaml.load(self.read_file(filename))

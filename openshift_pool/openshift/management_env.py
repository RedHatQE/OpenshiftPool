import os
import shutil

import yaml

from openshift_pool.env import ENV
from openshift_pool.exceptions import ManagementEnvAlreadyExists


class ManagementEnv(object):
    """
    This class represents the directory which all the logs, data, metadata of each cluster.
    It used to keep isolated env for each one so the logs will be saved under its directory.
    It has set of utility functions that help to manage the environment directory of the cluster
    """
    def __init__(self, dirname):
        self._dirname = dirname

    @property
    def path(self):
        """Return the absolute path of the management env directory"""
        return os.path.join(ENV['WORKSPACE'], self._dirname)

    def create(self):
        """Creating the management env directory.
        Raises:
            :ManagementEnvAlreadyExists: If the folder already exists.
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
        Args:
            :param `str` filename: The file name.
            :param `str` content: The file content.
        """
        with open(self.file_abspath(filename), 'w') as f:
            f.write(content)

    def write_yaml(self, filename, data):
        """Writing a yaml file with data in the management env directory.
        Args:
            :param `str` filename: The file name.
            :param `dict` content: The yaml data.
        """
        return self.write_file(filename, yaml.dump(data, default_flow_style=False))

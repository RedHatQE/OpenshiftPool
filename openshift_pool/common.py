import subprocess as sp
import logging
from ctypes import cdll, byref, create_string_buffer

from enum import Enum

from openshift_pool.env import LOG_LEVEL, setup_logger, LOG_FORMATTER,\
    MAIN_LOG_FILE


class Singleton(type):

    _instances = {}

    def __call__(self, *args, **kwargs):
        if self not in self._instances:
            self._instances[self] = super(Singleton, self).__call__(*args, **kwargs)
        return self._instances[self]


class AttributeDict(dict):
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__

    @classmethod
    def attributize_dict(cls, obj):
        if isinstance(obj, dict):
            attr_dict = cls()
            for key, value in obj.items():
                attr_dict[key] = cls.attributize_dict(value)
            return attr_dict
        elif isinstance(obj, (list, tuple)):
            nested_list = list()
            for value in obj:
                nested_list.append(cls.attributize_dict(value))
            return nested_list
        return obj


def set_proc_name(newname):
    """Set the current process name"""
    libc = cdll.LoadLibrary('libc.so.6')
    buff = create_string_buffer(len(newname)+1)
    buff.value = newname
    libc.prctl(15, byref(buff), 0, 0, 0)


def get_proc_name():
    """Get the current process name"""
    libc = cdll.LoadLibrary('libc.so.6')
    buff = create_string_buffer(128)
    # 16 == PR_GET_NAME from <linux/prctl.h>
    libc.prctl(16, byref(buff), 0, 0, 0)
    return buff.value


def pgrep(grep):
    return sp.getoutput(f'pgrep {grep}')


class NodeType(Enum):
    MASTER = 'master'
    INFRA = 'infra'
    COMPUTE = 'compute'


class Loggable:
    """
    This class provides a logging ability to the inherit object.
    """
    def __init__(self, log_file=None):
        self._logger = setup_logger(f'{self.__class__.__name__}_log', log_file or MAIN_LOG_FILE, LOG_LEVEL)

    def add_logging_file(self, log_file: str):
        handler = logging.FileHandler(log_file)
        handler.setFormatter(LOG_FORMATTER)
        self._logger.addHandler(handler)

    @property
    def log(self):
        return self._logger

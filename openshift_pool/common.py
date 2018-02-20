import subprocess as sp

from openshift_pool.env import ENV


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


def run_command(*args, **kwargs):
    """Running a shell command (in the WORKSPACE as working dir by default)
    and return True if success, else return False
    """
    kwargs['cwd'] = kwargs.get('cwd', ENV['WORKSPACE'])
    try:
        return sp.check_call(*args, **kwargs) == 0
    except sp.CalledProcessError:
        return False

class StackNotFoundException(Exception):
    def __init__(self, stack_name):
        self._stack_name = stack_name

    def __str__(self, *args, **kwargs):
        return 'Could not find stack "{}"'.format(self._stack_name)


class ManagementEnvAlreadyExists(Exception):
    """Raises when trying to create new management environment and it already exists"""
    def __init__(self, path):
        self._path = path

    def __str__(self, *args, **kwargs):
        return 'Management environment "{}" is already exists'.format(self._path)


class StackAlreadyExistsException(Exception):
    """Raises when trying to create new stack and it already exists"""
    def __init__(self, stack_name):
        self._stack_name = stack_name

    def __str__(self, *args, **kwargs):
        return 'Stack "{}" is already exists'.format(self._stack_name)


class NameServerUpdateException(Exception):
    def __init__(self, stack_name):
        self._stack_name = stack_name

    def __str__(self, *args, **kwargs):
        return 'Could not update name server for stack "{}"'.format(self._stack_name)


class EnvarNotDefinedException(Exception):
    def __init__(self, envvar):
        self._envvar = envvar

    def __str__(self, *args, **kwargs):
        return 'Environment variable must be defined: {}'.format(self._envvar)

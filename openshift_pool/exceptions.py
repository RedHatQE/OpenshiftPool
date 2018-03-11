class StackNotFoundException(BaseException):
    def __init__(self, stack_name):
        self._stack_name = stack_name

    def __str__(self):
        return 'Could not find stack "{}"'.format(self._stack_name)


class CannotDetectNodeTypeException(BaseException):
    def __init__(self, node_fqdn):
        self._node_fqdn = node_fqdn

    def __str__(self):
        return 'Could not detect node type from name "{}"'.format(self._node_fqdn)


class ManagementEnvAlreadyExists(BaseException):
    """Raises when trying to create new management environment and it already exists"""
    def __init__(self, path):
        self._path = path

    def __str__(self):
        return 'Management environment "{}" is already exists'.format(self._path)


class StackAlreadyExistsException(BaseException):
    """Raises when trying to create new stack and it already exists"""
    def __init__(self, stack_name):
        self._stack_name = stack_name

    def __str__(self):
        return 'Stack "{}" is already exists'.format(self._stack_name)


class NameServerUpdateException(BaseException):
    def __init__(self, stack_name):
        self._stack_name = stack_name

    def __str__(self):
        return 'Could not update name server for stack "{}"'.format(self._stack_name)


class EnvarNotDefinedException(BaseException):
    def __init__(self, envvar):
        self._envvar = envvar

    def __str__(self):
        return 'Environment variable must be defined: {}'.format(self._envvar)

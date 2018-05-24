class StackNotFoundException(BaseException):
    def __init__(self, stack_name):
        self._stack_name = stack_name

    def __str__(self):
        return 'Could not find stack "{}"'.format(self._stack_name)


class StackCreationFailedException(BaseException):
    def __init__(self, stack_name: str, stack_status_reason: str):
        """
        @param stack_name: `str` The name of the stack.
        @param stack_status_reason: `str` The reason for the failure - could be reached via heatclient.
        """
        self._stack_name = stack_name
        self._stack_status_reason = stack_status_reason

    def __str__(self):
        return f'Failed to create stack "{self._stack_name}" - reason: {self._stack_status_reason}'


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

import os

from openshift_pool.exceptions import EnvarNotDefinedException

ENV = {}

for ev in ('WORKSPACE', ):
    try:
        ENV[ev] = os.environ[ev]
    except KeyError:
        raise EnvarNotDefinedException(ev)


def config_workspace_as_cwd():
    os.chdir(ENV['WORKSPACE'])

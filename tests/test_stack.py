import pytest

from openshift_pool.openshift.stack import Stack, StackBuilder
from openshift_pool.env import config_workspace_as_cwd
from openshift_pool.exceptions import StackAlreadyExistsException
from openshift_pool.common import NodeType


STACK_ORIGINAL_NAME = 'test-stack'
STACK_INSTANCE_NAMES = ['master', 'infra', 'compute']
STACK_INSTANCE_TYPES = [NodeType.MASTER, NodeType.INFRA, NodeType.COMPUTE]


config_workspace_as_cwd()


@pytest.fixture(scope='module')
def stack():
    stack = StackBuilder().create(STACK_ORIGINAL_NAME, STACK_INSTANCE_NAMES, STACK_INSTANCE_TYPES)
    return stack


def test_stack_create(stack):
    assert isinstance(stack, Stack)
    assert stack.exists
    assert len(stack.instances) == len(STACK_INSTANCE_NAMES)
    for instance in stack.instances:
        assert any(instance.fqdn.startswith(name) for name in STACK_INSTANCE_NAMES)


def test_stack_already_exists(stack):
    with pytest.raises(StackAlreadyExistsException):
        StackBuilder().create(STACK_ORIGINAL_NAME, STACK_INSTANCE_NAMES, STACK_INSTANCE_TYPES)


def test_stack_delete(stack):
    StackBuilder().delete(stack)
    assert not stack.exists

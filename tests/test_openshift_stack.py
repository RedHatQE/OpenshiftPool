import pytest

from openshift_pool.openshift.stack import Stack, StackBuilder
from openshift_pool.env import config_workspace_as_cwd
from openshift_pool.exceptions import StackAlreadyExistsException


STACK_ORIGINAL_NAME = 'test-stack'


config_workspace_as_cwd()


@pytest.fixture(scope='module')
def stack():
    stack = StackBuilder().create(STACK_ORIGINAL_NAME, 3)
    return stack


def test_stack_create(stack):
    assert isinstance(stack, Stack)
    assert stack.exists


def test_stack_already_exists(stack):
    with pytest.raises(StackAlreadyExistsException):
        StackBuilder().create(STACK_ORIGINAL_NAME, 3)


def test_stack_delete(stack):
    StackBuilder().delete(stack)
    assert not stack.exists

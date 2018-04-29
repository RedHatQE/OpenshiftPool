import os

from ansible.parsing.dataloader import DataLoader
from ansible.vars.manager import VariableManager
from ansible.executor.playbook_executor import PlaybookExecutor
from ansible.inventory.manager import InventoryManager
from config import CONFIG_DATA


PLAYBOOKS_DIR = os.path.join(os.path.dirname(__file__))


class Options(object):
    # Playbook executor options
    def __init__(self, listtags=False, listtasks=False, listhosts=False, syntax=False,
                 connection='ssh', module_path=None, forks=5, remote_user='cloud-user',
                 private_key_file=CONFIG_DATA['private_key_file'], ssh_common_args='-o StrictHostKeyChecking=no',
                 ssh_extra_args=None, sftp_extra_args=None, scp_extra_args=None, become=True, become_method='sudo',
                 become_user='root', verbosity=3, check=False, diff=False):
        self.listtags = listtags
        self.listtasks = listtasks
        self.listhosts = listhosts
        self.syntax = syntax
        self.connection = connection
        self.module_path = module_path
        self.forks = forks
        self.remote_user = remote_user
        self.private_key_file = private_key_file
        self.ssh_common_args = ssh_common_args
        self.ssh_extra_args = ssh_extra_args
        self.sftp_extra_args = sftp_extra_args
        self.scp_extra_args = scp_extra_args
        self.become = become
        self.become_method = become_method
        self.become_user = become_user
        self.verbosity = verbosity
        self.check = check
        self.diff = diff


def run_ansible_playbook(playbook_name, inventory_path, extra_vars={}, options={}):
    """Running an ansible playbook.
    Args:
        :param `str` playbook_name: The name of the playbook. Only the name, Without dir and extension.
        :param `str` inventory_path: The path of the inventory file. Could be relative if in workspace.
        :param `dict` (optional) extra_vars: Extra variables (i.e. --extra_vars <var>)
        :param 'dict' (optional) options: options to override. see Options class.
    Returns:
        :return: Playbook excecution results.
    """
    # Resolving playbook absolute path
    playbook_path = (playbook_name if os.path.exists(playbook_name) else
                     os.path.join(PLAYBOOKS_DIR, playbook_name + '.yaml'))
    if not os.path.exists(playbook_path):
        raise IOError('No such file: {}'.format(playbook_path))
    # Preparing the playbook
    loader = DataLoader()
    options = Options(**options)
    inventory_manager = InventoryManager(loader, inventory_path)
    variable_manager = VariableManager(loader=loader, inventory=inventory_manager)
    variable_manager.extra_vars = extra_vars
    playbook_exec = PlaybookExecutor(
        playbooks=[playbook_path], inventory=inventory_manager,
        variable_manager=variable_manager, loader=loader,
        options=options, passwords={}
    )
    # Running the playbook
    return playbook_exec.run()

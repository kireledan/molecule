from collections import namedtuple
from ansible.parsing.dataloader import DataLoader
from ansible.vars import VariableManager
from ansible.inventory import Inventory
from ansible import __version__
from ansible.playbook.play import Play
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.plugins.callback import CallbackBase
import distutils
import sys

from molecule import util


class ResultCallback(CallbackBase):
    """A sample callback plugin used for performing an action as results come in

    If you want to collect all results into a single object for processing at
    the end of the execution, look into utilizing the ``json`` callback plugin
    or writing your own custom callback plugin
    """

    def v2_runner_on_ok(self, result, **kwargs):
        """Print a json representation of the result

        This method could store the result in an instance attribute for
        retrieval later
        """
        util.print_success('Success.')

    def v2_runner_on_failed(self, result, ignore_errors=False):

        util.print_error("IM ANSIBLE")
        util.print_error(result._result['msg'])
        sys.exit(1)





Options = namedtuple('Options', [
    'connection', 'module_path', 'forks', 'become', 'become_method',
    'become_user', 'check'
])


class AnsibleLocalExec():
    def __init__(self):
        self.variable_manager = VariableManager()
        self.loader = DataLoader()
        self.options = Options(
            connection='local',
            module_path='/path/to/mymodules',
            forks=100,
            become=None,
            become_method=None,
            become_user=None,
            check=False, )
        self.passwords = dict(vault_pass='secret')

        self.results_callback = ResultCallback()

        self.inventory = Inventory(
            loader=self.loader, variable_manager=self.variable_manager)
        self.variable_manager.set_inventory(self.inventory)

    def execute_task(self, task):
        play_source = dict(
            name="Ansible Play",
            hosts="localhost",
            gather_facts='no',
            tasks=[task], )

        play = Play().load(
            play_source,
            variable_manager=self.variable_manager,
            loader=self.loader)

        tqm = None
        try:
            tqm = TaskQueueManager(
                inventory=self.inventory,
                variable_manager=self.variable_manager,
                loader=self.loader,
                options=self.options,
                passwords=self.passwords,
                stdout_callback=self.results_callback)
            tqm.run(play)
        finally:
            if tqm is not None:
                tqm.cleanup()

    def execute_module(self, module, **kwargs):
        task = dict(action=dict(module=module, args=dict(kwargs)))
        self.execute_task(task)

    def is_22(self):
        d = distutils.version
        return not (d.LooseVersion(__version__) < d.LooseVersion('2.2'))

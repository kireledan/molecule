#  Copyright (c) 2015-2016 Cisco Systems
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to deal
#  in the Software without restriction, including without limitation the rights
#  to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#  copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#  OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
#  THE SOFTWARE.


import time

import boto
from molecule.provisioners import baseprovisioner
import molecule.utilities

class AWSDriver(baseprovisioner.BaseProvisioner):
    def __init__(self, molecule):
        super(AWSDriver, self).__init__(molecule)
        self._connect_to_aws()
        self._instances = []

    def _get_platform(self):
        self.m._env['MOLECULE_PLATFORM'] = 'AWS'
        return self.m._env['MOLECULE_PLATFORM']

    def _get_provider(self):
        return 'Docker'

    def _connect_to_aws(self):

        region = self.m._config.config['aws']['region']
        if 'AWS_ACCESS_KEY_ID' not in self.m._env:
            aws_access_key_id = self.m._config.config['aws']['aws_access_key_id']
        else:
            aws_access_key_id = self.m._env['AWS_ACCESS_KEY_ID']

        if 'AWS_SECRET_ACCESS_KEY' not in self.m._env:
            aws_secret_access_key = self.m._config.config['aws']['aws_secret_access_key']
        else:
            aws_secret_access_key = self.m._env['AWS_SECRET_ACCESS_KEY']


        self._aws = boto.ec2.connect_to_region(region, aws_access_key_id=aws_access_key_id,
                                               aws_secret_access_key=aws_secret_access_key)

    @property
    def name(self):
        return 'docker'

    @property
    def instances(self):
        pass

    def _update_instances(self):

        filters = {"tag:Name": "molecule".format(self.m._config)}
        reservations = self._aws.get_all_instances(filters=filters)
        self._active_instances = [i for r in reservations for i in r.instances]


    @property
    def default_provider(self):
        pass

    @property
    def default_platform(self):
        pass

    @property
    def provider(self):
        pass

    @property
    def platform(self):
        pass

    @property
    def valid_providers(self):
        return [{'name': 'Docker'}]

    @property
    def valid_platforms(self):
        return [{'name': 'Docker'}]

    @property
    def ssh_config_file(self):
        return None

    @property
    def ansible_connection_params(self):
        pass


    def up(self, no_provision=True):

        reservation = self._aws

        # NOTE: this isn't ideal, and assumes you're reserving one instance. Use a for loop, ideally.
        instance = reservation.instances[0]

        for instance in reservation.instances:
            # Check up on its status every so often
            status = instance.update()
            while status == 'pending':
                time.sleep(10)
                status = instance.update()

            if status == 'running':
                instance.add_tag("Name", "{{INSERT NAME}}")
            else:
                print('Instance status: ' + status)
                return None

            # Now that the status is running, it's not yet launched. The only way to tell if it's fully up is to try to SSH in.
            if status == "running":
                retry = True
                while retry:
                    try:
                        # SSH into the box here. I personally use fabric
                        retry = False
                    except:
                        time.sleep(10)

    def destroy(self):
        pass

    def status(self):
        pass

    def conf(self, vm_name=None, ssh_config=False):
        pass

    def inventory_entry(self, instance):
        template = '{} connection=docker\n'

        return template.format(instance['name'])

    def login_cmd(self, instance):
        return 'docker exec -ti {} bash'

    def login_args(self, instance):
        return [instance]

    @property
    def testinfra_args(self):
        return ""
    @property
    def serverspec_args(self):
        return dict()

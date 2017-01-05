#  Copyright (c) 2015-2016 Cisco Systems, Inc.
#
#  Permission is hereby granted, free of charge, to any person obtaining a copy
#  of this software and associated documentation files (the "Software"), to
#  deal in the Software without restriction, including without limitation the
#  rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
#  sell copies of the Software, and to permit persons to whom the Software is
#  furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included in
#  all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#  IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#  AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#  FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#  DEALINGS IN THE SOFTWARE.

import collections
import io
import json
import sys
import os

try:
    import docker
except ImportError:  # pragma: no cover
    sys.exit('ERROR: Driver missing, install docker-py.')

from molecule import util
from molecule.driver import basedriver
from molecule.ansible_exec import AnsibleLocalExec


class DockerDriver(basedriver.BaseDriver):
    def __init__(self, molecule):
        super(DockerDriver, self).__init__(molecule)
        self._docker = docker.Client(
            version='auto', **docker.utils.kwargs_from_env())
        self._containers = self.molecule.config.config['docker']['containers']
        self._provider = self._get_provider()
        self._platform = self._get_platform()
        self._ansib = AnsibleLocalExec()
        self._docker_module = 'docker_container' if self._ansib.is_22() else 'docker'

        self.image_tag = 'molecule_local/{}:{}'

        if 'build_image' not in self.molecule.config.config['docker']:
            self.molecule.config.config['docker']['build_image'] = True

    @property
    def name(self):
        return 'docker'

    @property
    def instances(self):
        created_containers = self._docker.containers(all=True)
        created_container_names = [
            container.get('Names')[0][1:].encode('utf-8')
            for container in created_containers
        ]
        for container in self._containers:
            if container.get('name') in created_container_names:
                container['created'] = True
            else:
                container['created'] = False

        return self._containers

    @property
    def default_provider(self):
        return self._provider

    @property
    def default_platform(self):
        return self._platform

    @property
    def provider(self):
        return self._provider

    @property
    def platform(self):
        return self._platform

    @platform.setter
    def platform(self, val):
        self._platform = val

    @property
    def valid_providers(self):
        return [{'name': self.provider}]

    @property
    def valid_platforms(self):
        return [{'name': self.platform}]

    @property
    def ssh_config_file(self):
        return

    @property
    def ansible_connection_params(self):
        return {'user': 'root', 'connection': 'docker'}

    @property
    def testinfra_args(self):
        return {'connection': 'docker'}

    @property
    def serverspec_args(self):
        return {}

    def up(self, no_provision=True):
        self.molecule.state.change_state('driver', self.name)

        if self.molecule.config.config['docker']['build_image']:
            self._build_ansible_compatible_image()
        else:
            self.image_tag = '{}:{}'

        for container in self.instances:
            container['image'] = self.image_tag.format(
                container['image'], container['image_version'])

            stored_groups = ""

            del container['image_version']
            del container['registry']

            if 'created' in container:
                del container['created']

            if 'ansible_groups' in container:
                stored_groups = container['ansible_groups']
                del container['ansible_groups']

            if 'dockerfile' in container:
                del container['dockerfile']

            if 'options' in container:
                del container['options']

            msg = 'Starting container {}...'.format(container['name'])
            util.print_info(msg)

            self._ansib.execute_module(
                self._docker_module,
                state='started',
                tty=True,
                detach=True,
                **container)


            container['ansible_groups'] = stored_groups

    def destroy(self):
        for container in self.instances:

            util.print_info('Removing container {}'.format(container['name']))

            tag_string = self.image_tag.format(
                container['image'], container['image_version'])

            self._ansib.execute_module(
                self._docker_module, state='absent', name=container['name'], image=tag_string)


    def status(self):
        Status = collections.namedtuple(
            'Status', ['name', 'state', 'provider', 'ports'])
        status_list = []
        for container in self.instances:
            name = container.get('name')
            try:
                d = self._docker.containers(filters={'name': name})[0]
                state = d.get('Status')
                ports = d.get('Ports')
            except IndexError:
                state = 'not_created'
                ports = []
            status_list.append(
                Status(
                    name=name,
                    state=state,
                    provider=self.provider,
                    ports=ports))

        return status_list

    def conf(self, vm_name=None, ssh_config=False):
        pass

    def inventory_entry(self, instance):
        template = '{} ansible_connection=docker\n'

        return template.format(instance['name'])

    def login_cmd(self, instance):
        return 'docker exec -ti {} bash'

    def login_args(self, instance):
        return [instance]

    def _get_platform(self):
        return 'docker'

    def _get_provider(self):
        return 'docker'

    def _build_ansible_compatible_image(self):
        available_images = [
            tag.encode('utf-8')
            for image in self._docker.images()
            for tag in image.get('RepoTags', [])
        ]

        for container in self.instances:
            if container.get('build_image'):
                msg = ('Creating Ansible compatible '
                       'image of {}:{} ...').format(container['image'],
                                                    container['image_version'])
                util.print_info(msg)

            if 'registry' in container:
                container['registry'] += '/'
            else:
                container['registry'] = ''

            dockerfile = '''
            FROM {container_image}:{container_version}
            {container_environment}
            RUN bash -c 'if [ -x "$(command -v apt-get)" ]; then apt-get update && apt-get install -y python sudo; fi'
            RUN bash -c 'if [ -x "$(command -v yum)" ]; then yum makecache fast && yum update -y && yum install -y python sudo yum-plugin-ovl && sed -i 's/plugins=0/plugins=1/g' /etc/yum.conf; fi'
            RUN bash -c 'if [ -x "$(command -v zypper)" ]; then zypper refresh && zypper update -y && zypper install -y python sudo; fi'

            '''  # noqa

            if 'dockerfile' in container:
                dockerfile = container['dockerfile']


            else:
                environment = container.get('environment')
                if environment:
                    environment = '\n'.join(
                        'ENV {} {}'.format(k, v)
                        for k, v in environment.iteritems())
                else:
                    environment = ''

                dockerfile = dockerfile.format(
                    container_image=container['registry'] + container['image'],
                    container_version=container['image_version'],
                    container_environment=environment)


                try:
                    with open(os.path.join(os.getcwd(),'dockerfile'),'w') as dockerf:
                        dockerf.write(dockerfile.encode('utf-8'))
                except IOError as e:
                    util.print_error(e.message)


                container['image'] = container['registry'].replace(
                    '/', '_').replace(':', '_') + container['image']

            tag_string = self.image_tag.format(container['image'],
                                               container['image_version'])

            if tag_string not in available_images or 'dockerfile' in container:
                util.print_info('Building ansible compatible image...')

                self._ansib.execute_module(
                    "docker_image",
                    path=str(os.getcwd()),
                    dockerfile=os.path.join(os.getcwd(),'dockerfile'),
                    name=tag_string)

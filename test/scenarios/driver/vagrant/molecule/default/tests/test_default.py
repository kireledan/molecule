import os

import testinfra.utils.ansible_runner

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']).get_hosts('all')


def test_hostname(host):
    assert 'instance' == host.system_info.hostname


def test_etc_molecule_directory(host):
    f = host.file('/etc/molecule')

    assert f.is_directory
    assert f.user == 'root'
    assert f.group == 'root'
    assert f.mode == 0o755


def test_etc_molecule_ansible_hostname_file(host):
    f = host.file('/etc/molecule/instance')

    assert f.is_file
    assert f.user == 'root'
    assert f.group == 'root'
    assert f.mode == 0o644


def test_interface(host):
    i = host.interface('eth1').addresses

    # NOTE(retr0h): Contains ipv4 and ipv6 addresses.
    assert len(i) == 2

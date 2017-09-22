*******
Install
*******

Requirements
============

* Ansible
* >=Ubuntu 14.04 

Install
=======

.. code-block:: bash

  $ sudo ansible-galaxy install kireledan.libvirt
  $ echo -ne "- hosts: localhost\n  remote_user: root\n  roles:\n    - kireledan.libvirt\n  vars:\n    state: install" > inst.yml
  $ ansible-playbook inst.yml


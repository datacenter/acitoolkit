"""
Ansible templates used by intraepg.py
"""
HOSTS_TEMPLATE = """
[acihosts]
{{ all_host_ip }}

[newhost]
{{ new_host_ip }}
                """

MY_PLAYBOOK = """
---
- name: Configure new hosts
  hosts: newhost
  user: {{ user_name }}
  sudo: yes
  tasks:

    # Install and configure ferm.
    #

    # We need to install libselinux-python on the target
    # machine to be able to use Ansible to copy the ferm.conf
    # file to the /etc/ferm/ directory.
    - name: install python-selinux
      apt: name=python-selinux
           state=present

    - name: install ferm
      apt: name=ferm
           state=present

    - name: install arptables
      apt: name=arptables
           state=present

    - name: install ebtables
      apt: name=ebtables
           state=present

    - name: install conntrack
      apt: name=conntrack
           state=present

    - name: add /etc/ferm directory
      file: path=/etc/ferm
            mode=0700
            state=directory

- name: Configure ferm
  hosts: acihosts
  user: {{ user_name }}
  sudo: yes
  tasks:

    - name: add the ferm.conf file to /etc/ferm
      copy: src={{ ferm_conf }}
            dest=/etc/ferm/ferm.conf
      notify: run ferm

  handlers:
    - name: run ferm
      command: ferm /etc/ferm/ferm.conf
      notify: save iptables

    - name: save iptables
      command: iptables-save
            """
#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_system
short_description: Manage system settings on VyOS via the REST API.
description:
  - Manages system-level settings — hostname, domain name, name servers,
    domain search list — using the VyOS HTTPS REST API.
  - Mirrors C(vyos.vyos.vyos_system) but uses the HTTP API.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  host_name:
    description: System hostname.
    type: str
  domain_name:
    description: System domain name.
    type: str
  name_server:
    description: List of DNS name servers. Mutually exclusive with domain_search.
    type: list
    elements: str
    aliases: [name_servers]
  domain_search:
    description: List of domain search suffixes. Mutually exclusive with name_server.
    type: list
    elements: str
  state:
    description: C(present) to apply, C(absent) to remove.
    type: str
    choices: [present, absent]
    default: present
  hostname:
    type: str
    required: true
  port:
    type: int
    default: 443
  api_key:
    type: str
    required: true
    no_log: true
  timeout:
    type: int
    default: 30
  verify_ssl:
    type: bool
    default: false
"""

RETURN = r"""
commands:
  description: set/delete commands issued.
  returned: always
  type: list
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vyos.rest.plugins.module_utils.vyos_rest import (
    VYOS_REST_CONNECTION_ARGSPEC,
    VyOSRestClient,
    VyOSRestError,
)


def main():
    argument_spec = dict(
        host_name=dict(type="str"),
        domain_name=dict(type="str"),
        name_server=dict(type="list", elements="str", aliases=["name_servers"]),
        domain_search=dict(type="list", elements="str"),
        state=dict(type="str", default="present", choices=["present", "absent"]),
    )
    argument_spec.update(VYOS_REST_CONNECTION_ARGSPEC)
    module = AnsibleModule(
        argument_spec=argument_spec,
        mutually_exclusive=[["name_server", "domain_search"]],
        supports_check_mode=True,
    )

    if module.check_mode:
        module.exit_json(changed=True, commands=["(check mode)"])

    client = VyOSRestClient(module)
    state = module.params["state"]
    commands = []
    changed = False

    try:
        if state == "present":
            if module.params.get("host_name"):
                client.configure_set(["system", "host-name"], module.params["host_name"])
                commands.append("set system host-name '{h}'".format(h=module.params["host_name"]))
                changed = True
            if module.params.get("domain_name"):
                client.configure_set(["system", "domain-name"], module.params["domain_name"])
                commands.append(
                    "set system domain-name '{d}'".format(d=module.params["domain_name"]),
                )
                changed = True
            for ns in module.params.get("name_server") or []:
                client.configure_set(["system", "name-server"], ns)
                commands.append("set system name-server {ns}".format(ns=ns))
                changed = True
            for ds in module.params.get("domain_search") or []:
                client.configure_set(["system", "domain-search", "domain"], ds)
                commands.append("set system domain-search domain {ds}".format(ds=ds))
                changed = True
        else:
            if module.params.get("host_name"):
                try:
                    client.configure_delete(["system", "host-name"])
                    commands.append("delete system host-name")
                    changed = True
                except VyOSRestError:
                    pass
            if module.params.get("domain_name"):
                try:
                    client.configure_delete(["system", "domain-name"])
                    commands.append("delete system domain-name")
                    changed = True
                except VyOSRestError:
                    pass
            if module.params.get("name_server"):
                try:
                    client.configure_delete(["system", "name-server"])
                    commands.append("delete system name-server")
                    changed = True
                except VyOSRestError:
                    pass
    except VyOSRestError as exc:
        module.fail_json(msg=str(exc))

    module.exit_json(changed=changed, commands=commands)


if __name__ == "__main__":
    main()

#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+
from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_system
short_description: Manage system settings on VyOS devices using REST API
description:
  - Manages basic system settings on VyOS devices via the REST API.
  - Uses REST API (C(connection=httpapi)) instead of CLI.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  host_name:
    description: Device hostname.
    type: str
  domain_name:
    description: Device domain name.
    type: str
  name_server:
    description: List of DNS name servers.
    type: list
    elements: str
    aliases: [name_servers]
  domain_search:
    description: List of domain search suffixes.
    type: list
    elements: str
  state:
    description:
      - C(present) applies the configuration.
      - C(absent) removes the configuration.
    type: str
    choices: [present, absent]
    default: present
notes:
  - Requires C(ansible_connection=httpapi) with the VyOS httpapi plugin.
  - C(ansible_network_os) must be set to C(vyos.rest.vyos).
"""

EXAMPLES = r"""
- name: Configure hostname and domain
  vyos.rest.vyos_system:
    host_name: router1
    domain_name: example.com
    name_server:
      - 8.8.8.8
      - 8.8.4.4
    state: present

- name: Remove domain name and name servers
  vyos.rest.vyos_system:
    domain_name: example.com
    name_server:
      - 8.8.8.8
    state: absent
"""

RETURN = r"""
before:
  description: Module-owned system configuration before this module ran.
  returned: always
  type: dict
after:
  description: Module-owned system configuration after this module ran.
  returned: when changed
  type: dict
commands:
  description: List of API command tuples sent to the device.
  returned: always
  type: list
saved:
  description: Whether the config was saved after changes.
  returned: when changed
  type: bool
response:
  description: Raw API response.
  returned: always
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vyos.rest.plugins.module_utils.vyos import (
    VyOSModule,
    dict_op,
    owned_config,
)


_BASE = ["system"]

ARGUMENT_SPEC = dict(
    host_name=dict(type="str"),
    domain_name=dict(type="str"),
    name_server=dict(type="list", elements="str", aliases=["name_servers"]),
    domain_search=dict(type="list", elements="str"),
    state=dict(type="str", default="present", choices=["present", "absent"]),
)


def main():
    module = AnsibleModule(ARGUMENT_SPEC, supports_check_mode=True)
    vyos = VyOSModule(module)

    state = module.params["state"]

    # want: snake_case keys from YAML, nulls removed
    _CANONICAL_KEYS = set(ARGUMENT_SPEC.keys()) - {"state"}
    want = {k: v for k, v in module.params.items() if k in _CANONICAL_KEYS and v is not None}

    # have: raw kebab-case keys from device, scoped by _BASE
    have = vyos.get_config(_BASE)

    # before/after: only keys owned by this module (declared in argspec)
    before = owned_config(have, ARGUMENT_SPEC)

    op = "set" if state == "present" else "delete"
    commands = dict_op(want, have, _BASE, op=op)

    if module.check_mode:
        module.exit_json(changed=bool(commands), commands=commands, before=before)

    if commands:
        response = vyos.apply_commands(commands)
        saved = vyos.save_config()
        after = owned_config(vyos.get_config(_BASE), ARGUMENT_SPEC)
        module.exit_json(
            changed=True,
            before=before,
            after=after,
            commands=commands,
            saved=saved,
            response=response,
        )

    module.exit_json(changed=False, before=before, after=before, commands=[])


if __name__ == "__main__":
    main()

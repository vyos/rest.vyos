#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function


__metaclass__ = type
DOCUMENTATION = r"""
---
module: vyos_lldp_global
short_description: Manage LLDP global configuration on VyOS via REST API.
description:
  - Manage LLDP global configuration on VyOS via REST API.
version_added: "1.0.0"
author: VyOS Community (@vyos)
options:
  config:
    type: dict
    suboptions:
      enable:
        type: bool
      addresses:
        type: list
        elements: str
      snmp:
        description:
        - C(enable) or C(disable).
        type: str
      legacy_protocols:
        type: list
        elements: str
        choices: [cdp, edp, fdp, sonmp]
  state:
    type: str
    default: merged
    choices: [merged, replaced, deleted, gathered]
"""
EXAMPLES = r"""
- vyos.rest.vyos_lldp_global:
    config:
      enable: true
      addresses: [192.0.2.17]
      snmp: enable
      legacy_protocols: [cdp, fdp]
    state: merged
"""
RETURN = r"""
before:
  returned: always
  type: dict
after:
  returned: when changed
  type: dict
commands:
  returned: always
  type: list
gathered:
  returned: when state is gathered
  type: dict
"""
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vyos.rest.plugins.module_utils.vyos import VyOSModule


_BASE = ["service", "lldp"]


def _get(vyos):
    raw = vyos.get_config(_BASE)
    if not raw:
        return {}
    result = {}
    if isinstance(raw, dict):
        result["enable"] = True
        if "management-address" in raw:
            v = raw["management-address"]
            result["addresses"] = (
                list(v.keys()) if isinstance(v, dict) else ([v] if isinstance(v, str) else list(v))
            )
        if "snmp" in raw:
            result["snmp"] = "enable"
        if "legacy-protocols" in raw:
            v = raw["legacy-protocols"]
            result["legacy_protocols"] = (
                list(v.keys()) if isinstance(v, dict) else ([v] if isinstance(v, str) else list(v))
            )
    return result


def _build(want, have, state):
    cmds = []
    if state in ("replaced", "deleted") and have:
        cmds.append(("delete", _BASE))
        if state == "deleted":
            return cmds
    if want.get("enable") is not False:
        cmds.append(("set", _BASE))
    for addr in want.get("addresses") or []:
        cmds.append(("set", _BASE + ["management-address", addr]))
    if want.get("snmp"):
        if want["snmp"] == "disable":
            cmds.append(("delete", _BASE + ["snmp"]))
        else:
            cmds.append(("set", _BASE + ["snmp"]))
    for p in want.get("legacy_protocols") or []:
        cmds.append(("set", _BASE + ["legacy-protocols", p]))
    return cmds


def main():
    module = AnsibleModule(
        dict(
            config=dict(
                type="dict",
                options=dict(
                    enable=dict(type="bool"),
                    addresses=dict(type="list", elements="str"),
                    snmp=dict(type="str"),
                    legacy_protocols=dict(
                        type="list",
                        elements="str",
                        choices=["cdp", "edp", "fdp", "sonmp"],
                    ),
                ),
            ),
            state=dict(default="merged", choices=["merged", "replaced", "deleted", "gathered"]),
        ),
        supports_check_mode=True,
    )
    vyos = VyOSModule(module)
    state = module.params["state"]
    config = module.params.get("config") or {}
    have = _get(vyos)
    if state == "gathered":
        module.exit_json(changed=False, gathered=have)
    commands = _build(config, have, state)
    if module.check_mode:
        module.exit_json(changed=bool(commands), commands=commands, before=have)
    if commands:
        response = vyos.apply_commands(commands)
        saved = vyos.save_config()
        module.exit_json(
            changed=True,
            before=have,
            after=_get(vyos),
            commands=commands,
            saved=saved,
            response=response,
        )
    module.exit_json(changed=False, before=have, after=have, commands=[])


if __name__ == "__main__":
    main()

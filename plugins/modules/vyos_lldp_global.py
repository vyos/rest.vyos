#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+
from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_lldp_global
short_description: Manage LLDP global configuration on VyOS via REST API.
description:
  - Manage LLDP global configuration on VyOS via REST API.
  - Uses C(ansible_connection=ansible.netcommon.httpapi).
version_added: "1.0.0"
author: VyOS Community (@vyos)
options:
  config:
    description: LLDP global configuration.
    type: dict
    suboptions:
      enable:
        description: Enable LLDP service.
        type: bool
      addresses:
        description: List of management addresses to advertise.
        type: list
        elements: str
      snmp:
        description:
          - C(enable) to enable LLDP SNMP subagent.
          - C(disable) to disable it.
          - Requires SNMP service to be configured on the device.
        type: str
      legacy_protocols:
        description: Legacy protocols to support.
        type: list
        elements: str
        choices: [cdp, edp, fdp, sonmp]
  state:
    description:
      - C(merged) - merge config with existing.
      - C(replaced) - replace existing config with provided.
      - C(deleted) - delete LLDP configuration.
      - C(gathered) - return current config without changes.
    type: str
    default: merged
    choices: [merged, replaced, deleted, gathered]
"""

EXAMPLES = r"""
- name: Enable LLDP with management address and legacy protocols
  vyos.rest.vyos_lldp_global:
    config:
      enable: true
      addresses:
        - 192.0.2.17
      legacy_protocols:
        - cdp
        - fdp
    state: merged

- name: Replace LLDP configuration
  vyos.rest.vyos_lldp_global:
    config:
      enable: true
      addresses:
        - 192.0.2.99
    state: replaced

- name: Delete all LLDP configuration
  vyos.rest.vyos_lldp_global:
    state: deleted

- name: Gather current LLDP configuration
  vyos.rest.vyos_lldp_global:
    state: gathered
  register: result
"""

RETURN = r"""
before:
  description: LLDP configuration before the module ran.
  returned: always
  type: dict
after:
  description: LLDP configuration after the module ran.
  returned: when changed
  type: dict
commands:
  description: List of commands sent to the device.
  returned: always
  type: list
gathered:
  description: Current LLDP configuration from the device.
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
                sorted(list(v.keys()))
                if isinstance(v, dict)
                else ([v] if isinstance(v, str) else sorted(list(v)))
            )
        if "snmp" in raw:
            result["snmp"] = "enable"
        if "legacy-protocols" in raw:
            v = raw["legacy-protocols"]
            result["legacy_protocols"] = (
                sorted(list(v.keys()))
                if isinstance(v, dict)
                else ([v] if isinstance(v, str) else sorted(list(v)))
            )
    return result


def _build(want, have, state):
    cmds = []

    if state == "deleted":
        if have:
            cmds.append(("delete", _BASE))
        return cmds

    if state == "replaced":
        # only wipe and rebuild if have differs from want
        want_addrs = sorted(want.get("addresses") or [])
        have_addrs = sorted(have.get("addresses") or [])
        want_protos = sorted(want.get("legacy_protocols") or [])
        have_protos = sorted(have.get("legacy_protocols") or [])
        want_snmp = want.get("snmp")
        have_snmp = have.get("snmp")
        want_enable = bool(want.get("enable"))
        have_enable = bool(have.get("enable"))

        if (
            want_addrs != have_addrs
            or want_protos != have_protos
            or want_snmp != have_snmp
            or want_enable != have_enable
        ):
            if have:
                cmds.append(("delete", _BASE))
            # fall through to set everything from want
        else:
            return cmds  # already matches — idempotent

    # enable
    if want.get("enable") and not have.get("enable"):
        cmds.append(("set", _BASE))

    # addresses
    have_addrs_set = set(have.get("addresses") or []) if state != "replaced" else set()
    for addr in want.get("addresses") or []:
        if addr not in have_addrs_set:
            cmds.append(("set", _BASE + ["management-address", addr]))

    # snmp
    if want.get("snmp"):
        if want["snmp"] == "disable" and have.get("snmp"):
            cmds.append(("delete", _BASE + ["snmp"]))
        elif want["snmp"] != "disable" and not have.get("snmp"):
            cmds.append(("set", _BASE + ["snmp"]))

    # legacy_protocols
    have_protos_set = set(have.get("legacy_protocols") or []) if state != "replaced" else set()
    for p in want.get("legacy_protocols") or []:
        if p not in have_protos_set:
            cmds.append(("set", _BASE + ["legacy-protocols", p]))

    return cmds


def main():
    module = AnsibleModule(
        argument_spec=dict(
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
            state=dict(
                default="merged",
                choices=["merged", "replaced", "deleted", "gathered"],
            ),
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

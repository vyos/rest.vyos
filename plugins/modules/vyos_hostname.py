#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_hostname
short_description: Manage the system hostname on a VyOS device via the REST API.
description:
  - Manages the C(system host-name) configuration on a VyOS device using the HTTPS REST API.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  config:
    description: Hostname configuration.
    type: dict
    suboptions:
      hostname:
        description: System hostname (max 63 characters, no underscores).
        type: str
        required: true
  state:
    description:
      - C(merged) - Ensure the hostname is set to the value in I(config).
      - >-
        C(replaced) and C(overridden) behave identically to C(merged) for
        this single-value resource -- there is nothing else to distinctly
        replace or override when there is only one field.
      - C(deleted) - Remove the configured hostname.
      - C(gathered) - Read the current hostname from the device without making changes.
    type: str
    choices: [merged, replaced, overridden, deleted, gathered]
    default: merged
seealso:
  - module: vyos.vyos.vyos_hostname
"""

EXAMPLES = r"""
- name: Set hostname
  vyos.rest.vyos_hostname:
    config:
      hostname: vyos-core-01
    state: merged

- name: Gather current hostname
  vyos.rest.vyos_hostname:
    state: gathered

- name: Delete hostname configuration
  vyos.rest.vyos_hostname:
    state: deleted
"""

RETURN = r"""
before:
  description: Configuration on the device before the module ran.
  returned: always
  type: dict
after:
  description: Configuration on the device after the module ran.
  returned: when changed
  type: dict
gathered:
  description: Hostname read from the device (state=gathered only).
  returned: when state is gathered
  type: dict
commands:
  description: List of API command tuples sent to the device.
  returned: always
  type: list
saved:
  description: Whether the config was saved after changes.
  returned: when changes are applied
  type: bool
response:
  description: Raw API response.
  returned: when changes are applied
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vyos.rest.plugins.module_utils.vyos import (
    VyOSModule,
    VyOSRestError,
)


_BASE = ["system", "host-name"]


def get_running_config(vyos):
    """ "system host-name" is a plain leafNode, not a container -- a
    single scalar value, not a config subtree. get_value (VyOS's
    "returnValue" retrieve operation) is the correct fetch for this,
    distinct from get_config's "showConfig" operation used everywhere
    else in this collection for genuine nested config sections.
    """
    return vyos.get_value(_BASE)


def build_commands(config, current, state):
    if state == "deleted":
        return [("delete", _BASE)] if current else []

    desired = (config or {}).get("hostname")
    if not desired or desired == current:
        return []
    return [("set", _BASE + [desired])]


ARGUMENT_SPEC = dict(
    config=dict(
        type="dict",
        options=dict(
            hostname=dict(type="str", required=True),
        ),
    ),
    state=dict(
        type="str",
        default="merged",
        choices=["merged", "replaced", "overridden", "deleted", "gathered"],
    ),
)


def main():
    module = AnsibleModule(
        ARGUMENT_SPEC,
        required_if=[
            ("state", "merged", ["config"]),
            ("state", "replaced", ["config"]),
            ("state", "overridden", ["config"]),
        ],
        supports_check_mode=True,
    )
    vyos = VyOSModule(module)

    # Collapsed states: replaced/overridden are identical to merged for
    # this single-value resource -- there is nothing else to distinctly
    # replace or override when there's only one field.
    state = module.params["state"]
    if state in ("replaced", "overridden"):
        state = "merged"

    config = module.params.get("config") or {}

    try:
        current = get_running_config(vyos)
    except VyOSRestError as exc:
        module.fail_json(msg="failed to read current hostname: {e}".format(e=str(exc)))

    have = {"hostname": current}

    if state == "gathered":
        module.exit_json(changed=False, gathered=have, commands=[])

    commands = build_commands(config, current, state)

    if module.check_mode:
        module.exit_json(changed=bool(commands), commands=commands, before=have, after=have)

    if commands:
        response = vyos.apply_commands(commands)
        saved = vyos.save_config()
        try:
            after_current = get_running_config(vyos)
        except VyOSRestError as exc:
            module.fail_json(
                msg="hostname change applied but failed to read back result: {e}".format(
                    e=str(exc),
                ),
            )
        after = {"hostname": after_current}
        module.exit_json(
            changed=True,
            before=have,
            after=after,
            commands=commands,
            saved=saved,
            response=response,
        )

    module.exit_json(changed=False, before=have, after=have, commands=[])


if __name__ == "__main__":
    main()

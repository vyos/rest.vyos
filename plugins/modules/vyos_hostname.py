#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vyos.rest.plugins.module_utils.vyos import VyOSModule


DOCUMENTATION = r"""
---
module: vyos_hostname
short_description: Manage the hostname of a VyOS device using REST API
description:
  - Configures the system hostname on VyOS network devices via the REST API.
  - Supports idempotent configuration — no change is made if the desired
    hostname already matches the running configuration.
  - Uses REST API (C(connection=httpapi)) instead of CLI.
version_added: "1.0.0"
author:
  - Your Name (@yourhandle)

options:
  config:
    description:
      - Hostname configuration dictionary.
    type: dict
    suboptions:
      hostname:
        description:
          - The hostname to set on the VyOS device.
          - Must be a valid RFC 1123 hostname.
        type: str

  state:
    description:
      - The desired state of the hostname configuration.
      - C(merged), C(replaced), and C(overridden) are identical for this
        single-value resource — all three ensure the hostname is set to
        the value specified in C(config).
      - C(deleted) removes the configured hostname, reverting to the
        device default.
      - C(gathered) retrieves the current hostname from the device and
        returns it as structured data in the C(gathered) key. No changes
        are made to the device.
    type: str
    default: merged
    choices:
      - merged
      - replaced
      - overridden
      - deleted
      - gathered

notes:
  - Tested against VyOS 1.3 (equuleus) and 1.4 (sagitta).
  - Requires C(ansible_connection=httpapi) with the VyOS httpapi plugin.
  - The C(ansible_network_os) inventory variable must be set to C(vyos.rest.vyos).
"""

EXAMPLES = r"""
# Before state:
# -------------
# vyos@router:~$ show configuration commands | grep host-name
# set system host-name 'vyostest'

- name: Set hostname using merged state
  vyos.rest.vyos_hostname:
    config:
      hostname: vyos
    state: merged

# After state:
# ------------
# set system host-name 'vyos'

# ------------------------------------------------------------------------

# Before state:
# -------------
# set system host-name 'vyos'

- name: Override hostname (identical behaviour to merged for this resource)
  vyos.rest.vyos_hostname:
    config:
      hostname: vyosTest
    state: overridden

# After state:
# ------------
# set system host-name 'vyosTest'

# ------------------------------------------------------------------------

# Before state:
# -------------
# set system host-name 'vyos'

- name: Replace hostname
  vyos.rest.vyos_hostname:
    config:
      hostname: vyosRouter
    state: replaced

# After state:
# ------------
# set system host-name 'vyosRouter'

# ------------------------------------------------------------------------

# Before state:
# -------------
# set system host-name 'vyos'

- name: Delete configured hostname
  vyos.rest.vyos_hostname:
    state: deleted

# After state:
# ------------
# (no host-name entry — device reverts to default)

# ------------------------------------------------------------------------

- name: Gather current hostname from device
  vyos.rest.vyos_hostname:
    state: gathered

# Module result:
# --------------
# "gathered": {
#     "hostname": "vyos"
# }

# ------------------------------------------------------------------------

- name: Idempotency — no change when hostname already matches
  vyos.rest.vyos_hostname:
    config:
      hostname: vyos
    state: merged

# Module result (hostname already 'vyos'):
# ----------------------------------------
# "changed": false
"""

RETURN = r"""
before:
  description: Hostname configuration on the device before this module ran.
  returned: when I(state) is C(merged), C(replaced), C(overridden) or C(deleted)
  type: dict
  sample:
    hostname: vyostest

after:
  description: Hostname configuration on the device after this module ran.
  returned: when changed
  type: dict
  sample:
    hostname: vyos

commands:
  description: List of API command dicts sent to the device.
  returned: when I(state) is C(merged), C(replaced), C(overridden) or C(deleted)
  type: list
  sample:
    - op: set
      path: ["system", "host-name", "vyos"]

gathered:
  description: >
    Current hostname configuration retrieved from the device as structured
    data. Returned only when I(state) is C(gathered).
  returned: when I(state) is C(gathered)
  type: dict
  sample:
    hostname: vyos

response:
  description: Raw response returned by the VyOS REST API.
  returned: when changes are applied
  type: dict
  sample:
    success: true
    data: null
    error: null

saved:
  description: Result of the save_config call issued after applying changes.
  returned: when changes are applied
  type: dict
"""


def get_running_config(vyos):

    raw = vyos.get_config(["system", "host-name"])

    hostname = None

    if isinstance(raw, dict):
        hostname = raw.get("host-name")

    elif isinstance(raw, str):
        hostname = raw.strip()
    else:
        hostname = None

    return {"hostname": hostname}


def build_commands(want, have, state):

    commands = []

    want_host = want.get("hostname")
    have_host = have.get("hostname")

    if state in ["merged", "replaced", "overridden"]:

        if want_host and want_host != have_host:
            commands.append(
                {
                    "op": "set",
                    "path": ["system", "host-name", want_host],
                },
            )

    elif state == "deleted":

        if have_host:
            commands.append(
                {
                    "op": "delete",
                    "path": ["system", "host-name"],
                },
            )

    return commands


def main():

    argument_spec = dict(
        config=dict(
            type="dict",
            options=dict(
                hostname=dict(type="str"),
            ),
        ),
        state=dict(
            default="merged",
            choices=[
                "merged",
                "replaced",
                "overridden",
                "deleted",
                "gathered",
            ],
        ),
    )

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    vyos = VyOSModule(module)

    state = module.params["state"]
    want = module.params.get("config") or {}

    have = get_running_config(vyos)

    if state == "gathered":
        module.exit_json(
            changed=False,
            gathered=have,
        )

    commands = build_commands(want, have, state)

    if module.check_mode:
        module.exit_json(
            changed=bool(commands),
            commands=commands,
        )

    if commands:

        response = vyos.apply_commands(commands)

        # save config if change applied
        saved = vyos.save_config()

        module.exit_json(
            changed=True,
            before=have,
            after=want,
            commands=commands,
            saved=saved,
            response=response,
        )

    module.exit_json(
        changed=False,
        before=have,
        after=have,
    )


if __name__ == "__main__":
    main()

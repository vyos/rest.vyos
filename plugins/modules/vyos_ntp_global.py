#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_ntp_global
short_description: Manage NTP configuration on VyOS devices using REST API
description:
  - Manages NTP server, allow-client, and listen-address configuration on
    VyOS devices via the REST API.
  - Supports idempotent operation using structured data.
  - Uses REST API (C(connection=httpapi)) instead of CLI.
  - Targets VyOS 1.4+ where NTP is managed by chronyd under C(service ntp).
version_added: "1.0.0"
author:
  - Varshitha Yataluru (@YVarshitha)

options:
  config:
    description: NTP configuration.
    type: dict
    suboptions:
      allow_clients:
        description:
          - List of client networks or addresses allowed to query this NTP server.
          - Maps to C(service ntp allow-client address) on the device.
        type: list
        elements: str
      listen_addresses:
        description:
          - Local IP addresses the NTP service should listen on.
          - Maps to C(service ntp listen-address) on the device.
        type: list
        elements: str
      servers:
        description:
          - List of upstream NTP servers to synchronise from.
        type: list
        elements: dict
        suboptions:
          server:
            description: Server hostname or IP address.
            type: str
            required: true
          options:
            description:
              - Per-server options.
            type: list
            elements: str
            choices:
              - dynamic
              - noselect
              - pool
              - preempt
              - prefer
              - nts
              - ptp
              - interleave

  state:
    description:
      - The desired state of the NTP configuration.
    type: str
    default: merged
    choices:
      - merged
      - replaced
      - overridden
      - deleted
      - gathered
"""

EXAMPLES = r"""
- name: Gather current NTP configuration
  vyos.rest.vyos_ntp_global:
    state: gathered

- name: Merge NTP configuration
  vyos.rest.vyos_ntp_global:
    config:
      allow_clients:
        - 10.6.6.0/24
      listen_addresses:
        - 10.1.3.1
      servers:
        - server: 203.0.113.0
          options:
            - prefer
    state: merged

- name: Replace NTP configuration
  vyos.rest.vyos_ntp_global:
    config:
      allow_clients:
        - 10.6.6.0/24
      listen_addresses:
        - 10.1.3.1
      servers:
        - server: 203.0.113.0
          options:
            - prefer
    state: replaced

- name: Delete all managed NTP configuration
  vyos.rest.vyos_ntp_global:
    state: deleted
"""

RETURN = r"""
before:
  description: NTP configuration before this module ran.
  returned: when state is merged, replaced, overridden or deleted
  type: dict
after:
  description: NTP configuration after this module ran.
  returned: when changed
  type: dict
commands:
  description: List of API commands sent to the device.
  returned: always
  type: list
gathered:
  description: Current NTP configuration as structured data.
  returned: when state is gathered
  type: dict
saved:
  description: Whether the config was saved after changes.
  returned: when changed
  type: bool
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vyos.rest.plugins.module_utils.vyos import (
    VyOSModule,
    dict_op,
    normalize_have,
    to_tag_dict,
)


_BASE = ["service", "ntp"]

# "server" is a genuine tag node (keyed by server address) that VyOS's
# REST API can collapse to a bare value for a single server with no
# options set.
_TAG_KEYS = {"server"}


def _servers_to_device(servers):
    """server[].options is the one genuine structural exception here:
    the argspec wraps per-server options in a named "options" list
    field, but confirmed against vyos-1x (service_ntp.xml.in) each
    option (noselect/nts/pool/prefer/ptp/interleave) is a direct
    valueless leafNode sibling under the server tagNode itself -- there
    is no "options" wrapper node on the device side at all.
    """
    return {s["server"]: {opt: {} for opt in (s.get("options") or [])} for s in servers or []}


def _servers_from_device(raw):
    result = []
    for name, data in sorted((raw or {}).items()):
        entry = {"server": name}
        if data:
            entry["options"] = sorted(to_tag_dict(data).keys())
        result.append(entry)
    return result


def _want_to_device(config):
    want = {}
    if config.get("allow_clients"):
        # allow_clients is a flat argspec list, but confirmed against
        # vyos-1x (allow-client.xml.i) the device nests the multi-value
        # leaf one level deeper, under a literal "address" child --
        # allow-client itself is a plain grouping node, not the leaf.
        want["allow-client"] = {"address": list(config["allow_clients"])}
    if config.get("listen_addresses"):
        want["listen-address"] = list(config["listen_addresses"])
    if config.get("servers"):
        want["server"] = _servers_to_device(config["servers"])
    return want


def get_running_config(vyos):
    return vyos.get_config(_BASE) or {}


def _device_to_argspec(raw):
    raw = raw or {}
    result = {"allow_clients": [], "listen_addresses": [], "servers": []}

    # allow-client: handle both VyOS schema variants (this module
    # targets VyOS 1.4+) --
    #   1.4:  {"allow-client": {"address": {...}}}
    #   1.5+: {"allow-client": {...}}  (no "address" subnode observed
    #         on some REST responses)
    # Confirmed current vyos-1x schema always declares the "address"
    # child, but this stays defensive for older devices/REST variants.
    allow_outer = raw.get("allow-client") or {}
    if isinstance(allow_outer, dict) and "address" in allow_outer:
        allow_raw = allow_outer["address"]
    else:
        allow_raw = allow_outer
    if allow_raw:
        result["allow_clients"] = sorted(to_tag_dict(allow_raw).keys())

    listen_raw = raw.get("listen-address")
    if listen_raw:
        result["listen_addresses"] = sorted(to_tag_dict(listen_raw).keys())

    result["servers"] = _servers_from_device(raw.get("server"))
    return result


def _normalize_allow_client(raw_have):
    """Ensure allow-client always presents the shape _want_to_device
    emits and dict_op compares against -- a dict with a plain LIST
    under "address" -- regardless of which VyOS schema/REST variant the
    device actually returned (a missing "address" wrapper, or the
    address values themselves collapsed to a dict-of-presence or a bare
    string instead of a plain array). This keeps dict_op only ever
    comparing list-vs-list for this field, the same well-exercised path
    used throughout the rest of this collection, rather than needing
    any change to the shared engine for a dict-vs-list case.
    """
    allow_outer = raw_have.get("allow-client")
    if not allow_outer:
        return raw_have

    if isinstance(allow_outer, dict) and "address" in allow_outer:
        address_raw = allow_outer["address"]
    else:
        address_raw = allow_outer

    raw_have = dict(raw_have)
    raw_have["allow-client"] = {"address": sorted(to_tag_dict(address_raw).keys())}
    return raw_have


def build_commands(config, raw_have, state):
    raw_have = _normalize_allow_client(raw_have or {})
    config = config or {}

    if state == "overridden":
        state = "replaced"

    if state == "deleted":
        return [("delete", _BASE)] if raw_have else []

    want = _want_to_device(config)
    norm_have = normalize_have(raw_have, _TAG_KEYS)

    commands = []
    if state == "replaced":
        commands += dict_op(want, norm_have, _BASE, op="purge")
    commands += dict_op(want, norm_have, _BASE, op="set")
    return commands


def main():
    argument_spec = dict(
        config=dict(
            type="dict",
            options=dict(
                allow_clients=dict(type="list", elements="str"),
                listen_addresses=dict(type="list", elements="str"),
                servers=dict(
                    type="list",
                    elements="dict",
                    options=dict(
                        server=dict(type="str", required=True),
                        options=dict(
                            type="list",
                            elements="str",
                            choices=[
                                "dynamic",
                                "noselect",
                                "pool",
                                "preempt",
                                "prefer",
                                "nts",
                                "ptp",
                                "interleave",
                            ],
                        ),
                    ),
                ),
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

    module = AnsibleModule(argument_spec, supports_check_mode=True)
    vyos = VyOSModule(module)

    state = module.params["state"]
    config = module.params.get("config") or {}

    raw_have = get_running_config(vyos)
    have = _device_to_argspec(raw_have)

    if state == "gathered":
        module.exit_json(gathered=have)

    commands = build_commands(config, raw_have, state)

    if module.check_mode:
        module.exit_json(changed=bool(commands), commands=commands, before=have)

    if commands:
        response = vyos.apply_commands(commands)
        saved = vyos.save_config()
        module.exit_json(
            changed=True,
            before=have,
            after=_device_to_argspec(get_running_config(vyos)),
            commands=commands,
            saved=saved,
            response=response,
        )

    module.exit_json(changed=False, before=have, after=have, commands=[])


if __name__ == "__main__":
    main()

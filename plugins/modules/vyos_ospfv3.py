#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+
from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_ospfv3
short_description: Manage OSPFv3 configuration on VyOS devices using REST API
description:
  - Manages OSPFv3 configuration on VyOS devices via the REST API.
  - Uses REST API (C(connection=httpapi)) instead of CLI.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  config:
    description: OSPFv3 configuration.
    type: dict
    suboptions:
      areas:
        description: OSPFv3 areas.
        type: list
        elements: dict
        suboptions:
          area_id:
            description: Area identity.
            type: str
            required: true
          export_list:
            description: Name of export-list.
            type: str
          import_list:
            description: Name of import-list.
            type: str
          range:
            description: Summarize routes matching prefix.
            type: list
            elements: dict
            suboptions:
              address:
                description: IPv6 prefix.
                type: str
                required: true
              advertise:
                description: Advertise this range.
                type: bool
              not_advertise:
                description: Do not advertise this range.
                type: bool
      parameters:
        description: OSPFv3 global parameters.
        type: dict
        suboptions:
          router_id:
            description: Router ID (IPv4 address format).
            type: str
      redistribute:
        description: Redistribute routes from another protocol.
        type: list
        elements: dict
        suboptions:
          route_type:
            description: Protocol to redistribute.
            type: str
            choices: [bgp, connected, kernel, ripng, static]
          route_map:
            description: Route map to apply.
            type: str
  state:
    description:
      - Desired state of the OSPFv3 configuration.
      - C(merged) adds or updates without removing existing config.
      - C(replaced) replaces the entire OSPFv3 configuration.
      - C(deleted) removes OSPFv3 configuration.
      - C(gathered) returns current configuration as structured data.
    type: str
    choices: [merged, replaced, deleted, gathered]
    default: merged
notes:
  - Requires C(ansible_connection=httpapi) with the VyOS httpapi plugin.
  - C(ansible_network_os) must be set to C(vyos.rest.vyos).
"""

EXAMPLES = r"""
- name: Merge OSPFv3 configuration
  vyos.rest.vyos_ospfv3:
    config:
      parameters:
        router_id: 192.0.2.10
      redistribute:
        - route_type: bgp
      areas:
        - area_id: "2"
          export_list: export1
          import_list: import1
          range:
            - address: "2001:db10::/32"
            - address: "2001:db20::/32"
    state: merged

- name: Delete all OSPFv3 configuration
  vyos.rest.vyos_ospfv3:
    state: deleted

- name: Gather current OSPFv3 configuration
  vyos.rest.vyos_ospfv3:
    state: gathered
"""

RETURN = r"""
before:
  description: OSPFv3 configuration before this module ran.
  returned: always
  type: dict
after:
  description: OSPFv3 configuration after this module ran.
  returned: when changed
  type: dict
commands:
  description: List of API command tuples sent to the device.
  returned: always
  type: list
gathered:
  description: Current OSPFv3 configuration as structured data.
  returned: when state is gathered
  type: dict
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
from ansible_collections.vyos.rest.plugins.module_utils.vyos import VyOSModule


_BASE = ["protocols", "ospfv3"]


def get_running_config(vyos):
    raw = vyos.get_config(_BASE)
    if not raw or not isinstance(raw, dict):
        return {}
    return _parse_ospfv3(raw)


def _parse_ospfv3(raw):
    result = {}

    # parameters
    params = raw.get("parameters", {})
    if params:
        result["parameters"] = {}
        if "router-id" in params:
            result["parameters"]["router_id"] = params["router-id"]

    # redistribute
    redist_raw = raw.get("redistribute", {})
    if redist_raw and isinstance(redist_raw, dict):
        redist = []
        for route_type, data in sorted(redist_raw.items()):
            entry = {"route_type": route_type}
            if isinstance(data, dict) and data.get("route-map"):
                entry["route_map"] = data["route-map"]
            redist.append(entry)
        if redist:
            result["redistribute"] = redist

    # areas
    area_raw = raw.get("area", {})
    if area_raw and isinstance(area_raw, dict):
        areas = []
        for area_id, area_data in sorted(area_raw.items()):
            area = {"area_id": area_id}
            area_data = area_data or {}
            if area_data.get("export-list"):
                area["export_list"] = area_data["export-list"]
            if area_data.get("import-list"):
                area["import_list"] = area_data["import-list"]
            range_raw = area_data.get("range", {})
            if range_raw and isinstance(range_raw, dict):
                ranges = []
                for prefix, rdata in sorted(range_raw.items()):
                    r = {"address": prefix}
                    rdata = rdata or {}
                    if "advertise" in rdata:
                        r["advertise"] = True
                    if "not-advertise" in rdata:
                        r["not_advertise"] = True
                    ranges.append(r)
                if ranges:
                    area["range"] = ranges
            areas.append(area)
        if areas:
            result["areas"] = areas

    return result


def build_commands(config, have, state):
    cmds = []

    if state == "deleted":
        if have:
            cmds.append(("delete", _BASE))
        return cmds

    if state == "replaced":
        # Build what we would set from scratch and compare to have
        would_set = build_commands(config, {}, "merged")
        have_set = build_commands(have, {}, "merged")
        if would_set == have_set:
            return []
        if have:
            cmds.append(("delete", _BASE))
        have = {}

    # parameters
    want_params = (config or {}).get("parameters") or {}
    have_params = have.get("parameters") or {}
    if want_params.get("router_id") and want_params["router_id"] != have_params.get("router_id"):
        cmds.append(("set", _BASE + ["parameters", "router-id", want_params["router_id"]]))

    # redistribute
    want_redist = {r["route_type"]: r for r in ((config or {}).get("redistribute") or [])}
    have_redist = {r["route_type"]: r for r in (have.get("redistribute") or [])}

    for rt in set(have_redist) - set(want_redist):
        if state == "merged":
            pass  # merged doesn't remove
    for rt, entry in want_redist.items():
        if rt not in have_redist:
            cmds.append(("set", _BASE + ["redistribute", rt]))
        if entry.get("route_map"):
            have_rm = have_redist.get(rt, {}).get("route_map")
            if entry["route_map"] != have_rm:
                cmds.append(("set", _BASE + ["redistribute", rt, "route-map", entry["route_map"]]))

    # areas
    want_areas = {a["area_id"]: a for a in ((config or {}).get("areas") or [])}
    have_areas = {a["area_id"]: a for a in (have.get("areas") or [])}

    for area_id, want_area in want_areas.items():
        have_area = have_areas.get(area_id, {})
        abase = _BASE + ["area", area_id]

        if want_area.get("export_list") and want_area["export_list"] != have_area.get(
            "export_list",
        ):
            cmds.append(("set", abase + ["export-list", want_area["export_list"]]))
        if want_area.get("import_list") and want_area["import_list"] != have_area.get(
            "import_list",
        ):
            cmds.append(("set", abase + ["import-list", want_area["import_list"]]))

        want_ranges = {r["address"]: r for r in (want_area.get("range") or [])}
        have_ranges = {r["address"]: r for r in (have_area.get("range") or [])}

        for addr in want_ranges:
            if addr not in have_ranges:
                cmds.append(("set", abase + ["range", addr]))
                r = want_ranges[addr]
                if r.get("not_advertise"):
                    cmds.append(("set", abase + ["range", addr, "not-advertise"]))
                elif r.get("advertise"):
                    cmds.append(("set", abase + ["range", addr, "advertise"]))

    return cmds


ARGUMENT_SPEC = dict(
    config=dict(
        type="dict",
        options=dict(
            areas=dict(
                type="list",
                elements="dict",
                options=dict(
                    area_id=dict(type="str", required=True),
                    export_list=dict(type="str"),
                    import_list=dict(type="str"),
                    range=dict(
                        type="list",
                        elements="dict",
                        options=dict(
                            address=dict(type="str", required=True),
                            advertise=dict(type="bool"),
                            not_advertise=dict(type="bool"),
                        ),
                    ),
                ),
            ),
            parameters=dict(
                type="dict",
                options=dict(
                    router_id=dict(type="str"),
                ),
            ),
            redistribute=dict(
                type="list",
                elements="dict",
                options=dict(
                    route_type=dict(
                        type="str",
                        choices=["bgp", "connected", "kernel", "ripng", "static"],
                    ),
                    route_map=dict(type="str"),
                ),
            ),
        ),
    ),
    state=dict(
        default="merged",
        choices=["merged", "replaced", "deleted", "gathered"],
    ),
)


def main():
    module = AnsibleModule(ARGUMENT_SPEC, supports_check_mode=True)
    vyos = VyOSModule(module)

    state = module.params["state"]
    config = module.params.get("config") or {}

    have = get_running_config(vyos)

    if state == "gathered":
        module.exit_json(changed=False, gathered=have)

    commands = build_commands(config, have, state)

    if module.check_mode:
        module.exit_json(changed=bool(commands), commands=commands, before=have)

    if commands:
        response = vyos.apply_commands(commands)
        saved = vyos.save_config()
        module.exit_json(
            changed=True,
            before=have,
            after=get_running_config(vyos),
            commands=commands,
            saved=saved,
            response=response,
        )

    module.exit_json(changed=False, before=have, after=have, commands=[])


if __name__ == "__main__":
    main()

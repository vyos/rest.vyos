#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_facts
short_description: Get facts about VyOS devices via REST API.
description:
  - Collects facts from VyOS devices using the HTTPS REST API.
  - Returns system info and optionally per-resource configuration facts.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  gather_subset:
    description:
      - Restrict facts to a subset. Use C(all), C(default), C(config), or C(min).
    type: list
    elements: str
    default: ["min"]
  gather_network_resources:
    description:
      - Which network resource facts to gather.
    type: list
    elements: str
  available_network_resources:
    description:
    - When true, return a list of available resource names.
    type: bool
    default: false
  hostname:
    description:
    - Device IP or FQDN.
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
ansible_facts:
  description: Dictionary of facts keyed by resource name.
  returned: always
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vyos.rest.plugins.module_utils.vyos_rest import (
    VYOS_REST_CONNECTION_ARGSPEC,
    VyOSRestClient,
    VyOSRestError,
)


_NETWORK_RESOURCES = [
    "interfaces",
    "l3_interfaces",
    "lag_interfaces",
    "lldp_global",
    "lldp_interfaces",
    "static_routes",
    "firewall_rules",
    "firewall_global",
    "firewall_interfaces",
    "ospfv2",
    "ospfv3",
]

_RESOURCE_PATHS = {
    "interfaces": ["interfaces"],
    "l3_interfaces": ["interfaces"],
    "lag_interfaces": ["interfaces", "bonding"],
    "lldp_global": ["service", "lldp"],
    "lldp_interfaces": ["service", "lldp"],
    "static_routes": ["protocols", "static"],
    "firewall_rules": ["firewall"],
    "firewall_global": ["firewall"],
    "firewall_interfaces": ["firewall"],
    "ospfv2": ["protocols", "ospf"],
    "ospfv3": ["protocols", "ospfv3"],
}


def _get_subset(client, resource):
    path = _RESOURCE_PATHS.get(resource, [])
    try:
        result = client.retrieve_show_config(path)
        return result.get("data") or {}
    except VyOSRestError:
        return {}


def main():
    argument_spec = dict(
        gather_subset=dict(type="list", elements="str", default=["min"]),
        gather_network_resources=dict(type="list", elements="str"),
        available_network_resources=dict(type="bool", default=False),
    )
    argument_spec.update(VYOS_REST_CONNECTION_ARGSPEC)
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)

    client = VyOSRestClient(module)
    facts = {}

    if module.params["available_network_resources"]:
        facts["available_network_resources"] = _NETWORK_RESOURCES

    gather_subset = module.params["gather_subset"]
    get_all = "all" in gather_subset

    # Always gather system info for "min" or "all"
    if get_all or "min" in gather_subset or "default" in gather_subset:
        try:
            info = client.info()
            facts["version"] = info.get("data", {}).get("version", "")
            facts["hostname"] = info.get("data", {}).get("hostname", "")
        except VyOSRestError:
            pass

    # Config subset
    if get_all or "config" in gather_subset:
        try:
            result = client.retrieve_show_config([])
            facts["config"] = result.get("data") or {}
        except VyOSRestError:
            facts["config"] = {}

    # Network resources
    requested = module.params.get("gather_network_resources") or []
    if "all" in requested:
        requested = _NETWORK_RESOURCES

    for resource in requested:
        if resource.startswith("!"):
            continue
        if resource in _NETWORK_RESOURCES:
            facts["network_resources"] = facts.get("network_resources", {})
            facts["network_resources"][resource] = _get_subset(client, resource)

    module.exit_json(changed=False, ansible_facts=facts)


if __name__ == "__main__":
    main()

#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+
from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_facts
short_description: Get facts about VyOS devices using REST API
description:
  - Collects facts from VyOS devices via the REST API.
  - Returns structured facts under the C(ansible_facts) key.
  - Uses REST API (C(connection=httpapi)) instead of CLI.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  gather_subset:
    description:
      - When supplied, this argument will restrict the facts collected to
        a given subset. Possible values for this argument include C(all),
        C(default), C(config), C(interfaces), C(hostname), C(users),
        C(bgp), C(ospf), C(ntp), C(snmp) and C(logging).
      - Specify a list of values to include a larger subset. Use the
        exclamation mark (C(!)) before a value to exclude it. Values
        C(all) and C(default) cannot be combined with each other or with
        negation.
    type: list
    elements: str
    default: ['default']
  gather_network_resources:
    description:
      - When supplied, this argument will restrict the facts collected to
        a given subset. Possible values include the resource module names.
      - This argument is not currently used.
    type: list
    elements: str
notes:
  - Requires C(ansible_connection=httpapi) with the VyOS httpapi plugin.
  - C(ansible_network_os) must be set to C(vyos.rest.vyos).
  - Only configuration facts are available via the REST API.
    Operational state (interface counters, BGP neighbors) is not supported.
"""

EXAMPLES = r"""
- name: Gather all facts
  vyos.rest.vyos_facts:
    gather_subset: all

- name: Gather default facts
  vyos.rest.vyos_facts:

- name: Gather interface and hostname facts only
  vyos.rest.vyos_facts:
    gather_subset:
      - interfaces
      - hostname

- name: Gather all except config
  vyos.rest.vyos_facts:
    gather_subset:
      - all
      - '!config'
"""

RETURN = r"""
ansible_facts:
  description: Facts collected from the device.
  returned: always
  type: dict
  contains:
    vyos_hostname:
      description: Device hostname.
      type: str
    vyos_config:
      description: Full device configuration as structured data.
      type: dict
    vyos_interfaces:
      description: Interface configuration.
      type: dict
    vyos_users:
      description: User accounts (without passwords).
      type: list
    vyos_bgp:
      description: BGP configuration.
      type: dict
    vyos_ospf:
      description: OSPFv2 configuration.
      type: dict
    vyos_ospfv3:
      description: OSPFv3 configuration.
      type: dict
    vyos_ntp:
      description: NTP configuration.
      type: dict
    vyos_snmp:
      description: SNMP configuration.
      type: dict
    vyos_logging:
      description: Logging configuration.
      type: dict
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vyos.rest.plugins.module_utils.vyos import VyOSModule


VALID_SUBSETS = frozenset(
    [
        "all",
        "default",
        "config",
        "interfaces",
        "hostname",
        "users",
        "bgp",
        "ospf",
        "ospfv3",
        "ntp",
        "snmp",
        "logging",
    ],
)

DEFAULT_SUBSETS = frozenset(["hostname", "interfaces"])


def _get_config(vyos, path):
    try:
        result = vyos.get_config(path)
        return result or {}
    except Exception:
        return {}


def gather_hostname(vyos):
    raw = _get_config(vyos, ["system"])
    return raw.get("host-name", "")


def gather_config(vyos):
    return _get_config(vyos, [])


def gather_interfaces(vyos):
    return _get_config(vyos, ["interfaces"])


def gather_users(vyos):
    raw = _get_config(vyos, ["system", "login", "user"])
    if not raw or not isinstance(raw, dict):
        return []
    raw = raw.get("user", raw)
    users = []
    for username, data in sorted(raw.items()):
        user = {"name": username}
        data = data or {}
        if data.get("full-name"):
            user["full_name"] = data["full-name"]
        auth = data.get("authentication", {}) or {}
        pub_keys = auth.get("public-keys", {}) or {}
        if pub_keys:
            user["public_keys"] = list(pub_keys.keys())
        users.append(user)
    return users


def gather_bgp(vyos):
    return _get_config(vyos, ["protocols", "bgp"])


def gather_ospf(vyos):
    return _get_config(vyos, ["protocols", "ospf"])


def gather_ospfv3(vyos):
    return _get_config(vyos, ["protocols", "ospfv3"])


def gather_ntp(vyos):
    return _get_config(vyos, ["service", "ntp"])


def gather_snmp(vyos):
    return _get_config(vyos, ["service", "snmp"])


def gather_logging(vyos):
    return _get_config(vyos, ["system", "syslog"])


def main():
    module = AnsibleModule(
        argument_spec=dict(
            gather_subset=dict(
                type="list",
                elements="str",
                default=["default"],
            ),
            gather_network_resources=dict(
                type="list",
                elements="str",
            ),
        ),
        supports_check_mode=True,
    )

    vyos = VyOSModule(module)
    gather_subset = module.params["gather_subset"]

    # Normalize subset
    runable_subsets = set()
    exclude_subsets = set()

    for subset in gather_subset:
        if subset.startswith("!"):
            exclude = subset[1:]
            if exclude not in VALID_SUBSETS:
                module.fail_json(msg="Invalid subset: %s" % exclude)
            exclude_subsets.add(exclude)
        elif subset == "all":
            runable_subsets.update(VALID_SUBSETS - {"all", "default"})
        elif subset == "default":
            runable_subsets.update(DEFAULT_SUBSETS)
        elif subset in VALID_SUBSETS:
            runable_subsets.add(subset)
        else:
            module.fail_json(msg="Invalid subset: %s" % subset)

    if not runable_subsets:
        runable_subsets.update(DEFAULT_SUBSETS)

    runable_subsets -= exclude_subsets
    runable_subsets -= {"all", "default"}

    facts = {}

    if "hostname" in runable_subsets:
        facts["vyos_hostname"] = gather_hostname(vyos)

    if "config" in runable_subsets:
        facts["vyos_config"] = gather_config(vyos)

    if "interfaces" in runable_subsets:
        facts["vyos_interfaces"] = gather_interfaces(vyos)

    if "users" in runable_subsets:
        facts["vyos_users"] = gather_users(vyos)

    if "bgp" in runable_subsets:
        bgp = gather_bgp(vyos)
        if bgp:
            facts["vyos_bgp"] = bgp

    if "ospf" in runable_subsets:
        ospf = gather_ospf(vyos)
        if ospf:
            facts["vyos_ospf"] = ospf

    if "ospfv3" in runable_subsets:
        ospfv3 = gather_ospfv3(vyos)
        if ospfv3:
            facts["vyos_ospfv3"] = ospfv3

    if "ntp" in runable_subsets:
        ntp = gather_ntp(vyos)
        if ntp:
            facts["vyos_ntp"] = ntp

    if "snmp" in runable_subsets:
        snmp = gather_snmp(vyos)
        if snmp:
            facts["vyos_snmp"] = snmp

    if "logging" in runable_subsets:
        logging = gather_logging(vyos)
        if logging:
            facts["vyos_logging"] = logging

    module.exit_json(ansible_facts=facts)


if __name__ == "__main__":
    main()

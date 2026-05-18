#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_ospf_interfaces
short_description: OSPF Interfaces Resource Module via REST API.
description:
  - Manages per-interface OSPF parameters (cost, hello/dead timers, authentication,
    passive mode, etc.) for both OSPFv2 and OSPFv3 via the VyOS HTTPS REST API.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  config:
    description: List of OSPF interface configurations.
    type: list
    elements: dict
    suboptions:
      name:
        description: Interface name.
        type: str
      address_family:
        description: OSPF settings per address family.
        type: list
        elements: dict
        suboptions:
          afi:
            description: Address family (ipv4=OSPFv2, ipv6=OSPFv3).
            type: str
            choices: [ipv4, ipv6]
            required: true
          authentication:
            type: dict
            suboptions:
              plaintext_password:
                type: str
              md5_key:
                type: dict
                suboptions:
                  key_id:
                    type: int
                  key:
                    type: str
          bandwidth:
            type: int
          cost:
            type: int
          dead_interval:
            type: int
          hello_interval:
            type: int
          mtu_ignore:
            type: bool
          network:
            type: str
          priority:
            type: int
          retransmit_interval:
            type: int
          transmit_delay:
            type: int
          ifmtu:
            type: int
          instance:
            type: str
          passive:
            type: bool
  state:
    type: str
    choices: [merged, replaced, overridden, deleted, gathered]
    default: merged
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
before:
  returned: always
  type: list
after:
  returned: when changed
  type: list
commands:
  returned: always
  type: list
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vyos.rest.plugins.module_utils.vyos_rest import (
    VYOS_REST_CONNECTION_ARGSPEC,
    VyOSRestClient,
    VyOSRestError,
)


_IFACE_TYPES = {
    "eth": "ethernet",
    "bond": "bonding",
    "lo": "loopback",
    "dummy": "dummy",
    "br": "bridge",
    "wg": "wireguard",
    "tun": "tunnel",
    "vxlan": "vxlan",
}


def _itype(name):
    for p, t in _IFACE_TYPES.items():
        if name.startswith(p):
            return t
    return "ethernet"


def _ospf_iface_base(name, afi):
    itype = _itype(name)
    if afi == "ipv4":
        return ["interfaces", itype, name, "ip", "ospf"]
    return ["interfaces", itype, name, "ipv6", "ospfv3"]


def _apply(client, cfg, commands):
    name = cfg["name"]
    for af in cfg.get("address_family") or []:
        afi = af["afi"]
        base = _ospf_iface_base(name, afi)

        int_map = {
            "cost": "cost",
            "bandwidth": "bandwidth",
            "dead_interval": "dead-interval",
            "hello_interval": "hello-interval",
            "priority": "priority",
            "retransmit_interval": "retransmit-interval",
            "transmit_delay": "transmit-delay",
            "ifmtu": "ifmtu",
        }
        for param, key in int_map.items():
            if af.get(param) is not None:
                client.configure_set(base + [key], str(af[param]))
                commands.append("set {b} {k} {v}".format(b=" ".join(base), k=key, v=af[param]))

        if af.get("mtu_ignore"):
            client.configure_set(base + ["mtu-ignore"])
            commands.append("set {b} mtu-ignore".format(b=" ".join(base)))
        if af.get("passive"):
            client.configure_set(base + ["passive"])
            commands.append("set {b} passive".format(b=" ".join(base)))
        if af.get("network"):
            client.configure_set(base + ["network"], af["network"])
        if af.get("instance"):
            client.configure_set(base + ["instance-id"], af["instance"])

        auth = af.get("authentication") or {}
        if auth.get("plaintext_password"):
            client.configure_set(
                base + ["authentication", "plaintext-password"],
                auth["plaintext_password"],
            )
            commands.append(
                "set {b} authentication plaintext-password ...".format(b=" ".join(base)),
            )
        md5 = auth.get("md5_key") or {}
        if md5.get("key_id") and md5.get("key"):
            client.configure_set(
                base + ["authentication", "md5", "key-id", str(md5["key_id"]), "md5-key"],
                md5["key"],
            )


def _get(client):
    try:
        r = client.retrieve_show_config(["interfaces"])
        raw = r.get("data") or {}
        out = []
        for itype, itype_data in raw.items():
            if not isinstance(itype_data, dict):
                continue
            for iname, idata in itype_data.items():
                if not isinstance(idata, dict):
                    continue
                afs = []
                ip_ospf = (idata.get("ip") or {}).get("ospf")
                if ip_ospf:
                    afs.append({"afi": "ipv4", "ospf_data": ip_ospf})
                ip6_ospfv3 = (idata.get("ipv6") or {}).get("ospfv3")
                if ip6_ospfv3:
                    afs.append({"afi": "ipv6", "ospfv3_data": ip6_ospfv3})
                if afs:
                    out.append({"name": iname, "address_family": afs})
        return out
    except VyOSRestError:
        return []


def main():
    argument_spec = dict(
        config=dict(
            type="list",
            elements="dict",
            options=dict(
                name=dict(type="str"),
                address_family=dict(
                    type="list",
                    elements="dict",
                    options=dict(
                        afi=dict(type="str", required=True, choices=["ipv4", "ipv6"]),
                        authentication=dict(
                            type="dict",
                            options=dict(
                                plaintext_password=dict(type="str", no_log=True),
                                md5_key=dict(
                                    type="dict",
                                    options=dict(
                                        key_id=dict(type="int"),
                                        key=dict(type="str", no_log=True),
                                    ),
                                ),
                            ),
                        ),
                        bandwidth=dict(type="int"),
                        cost=dict(type="int"),
                        dead_interval=dict(type="int"),
                        hello_interval=dict(type="int"),
                        mtu_ignore=dict(type="bool"),
                        network=dict(type="str"),
                        priority=dict(type="int"),
                        retransmit_interval=dict(type="int"),
                        transmit_delay=dict(type="int"),
                        ifmtu=dict(type="int"),
                        instance=dict(type="str"),
                        passive=dict(type="bool"),
                    ),
                ),
            ),
        ),
        state=dict(
            type="str",
            default="merged",
            choices=["merged", "replaced", "overridden", "deleted", "gathered"],
        ),
    )
    argument_spec.update(VYOS_REST_CONNECTION_ARGSPEC)
    module = AnsibleModule(argument_spec=argument_spec, supports_check_mode=True)
    client = VyOSRestClient(module)
    state = module.params["state"]
    config = module.params.get("config") or []
    commands = []
    changed = False
    before = _get(client)

    if state == "gathered":
        module.exit_json(changed=False, gathered=before, before=before, commands=[])
    if module.check_mode:
        module.exit_json(changed=True, before=before, commands=["(check mode)"])

    try:
        for cfg in config:
            _apply(client, cfg, commands)
            changed = True
    except VyOSRestError as exc:
        module.fail_json(msg=str(exc))

    after = _get(client) if changed else before
    module.exit_json(changed=changed, before=before, after=after, commands=commands)


if __name__ == "__main__":
    main()

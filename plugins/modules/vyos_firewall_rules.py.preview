#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_firewall_rules
short_description: Manage firewall rules on VyOS via the REST API.
description:
  - Manages VyOS firewall rule sets and individual rules using the HTTPS REST API.
  - Mirrors C(vyos.vyos.vyos_firewall_rules) but uses the HTTP API.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  config:
    description: List of firewall rule set configurations.
    type: list
    elements: dict
    suboptions:
      afi:
        description: Address family.
        type: str
        choices: [ipv4, ipv6]
        required: true
      rule_sets:
        description: List of named rule sets.
        type: list
        elements: dict
        suboptions:
          name:
            description: Rule set name.
            type: str
            required: true
          default_action:
            description: Default action for unmatched traffic.
            type: str
            choices: [drop, reject, accept]
            default: drop
          description:
            description: Rule set description.
            type: str
          rules:
            description: List of firewall rules.
            type: list
            elements: dict
            suboptions:
              number:
                description: Rule number (1-999999).
                type: int
                required: true
              action:
                description: Rule action.
                type: str
                choices: [drop, reject, accept, inspect]
              description:
                description: Rule description.
                type: str
              protocol:
                description: Protocol (e.g. C(tcp), C(udp), C(icmp), C(all)).
                type: str
              source:
                description: Source match criteria.
                type: dict
                suboptions:
                  address:
                    description: Source IP address or network.
                    type: str
                  port:
                    description: Source port or port range.
                    type: str
                  group:
                    description: Address or network group.
                    type: dict
                    suboptions:
                      address_group:
                        type: str
                      network_group:
                        type: str
              destination:
                description: Destination match criteria.
                type: dict
                suboptions:
                  address:
                    description: Destination IP address or network.
                    type: str
                  port:
                    description: Destination port or port range.
                    type: str
                  group:
                    description: Address or network group.
                    type: dict
                    suboptions:
                      address_group:
                        type: str
                      network_group:
                        type: str
              state:
                description: Connection state matching.
                type: dict
                suboptions:
                  established:
                    type: bool
                  new:
                    type: bool
                  related:
                    type: bool
                  invalid:
                    type: bool
              enabled:
                description: Whether the rule is active.
                type: bool
                default: true
  state:
    description:
      - C(merged): Add/update listed rule sets and rules.
      - C(replaced): Replace listed rule sets entirely.
      - C(overridden): Replace the entire firewall rule config.
      - C(deleted): Remove listed (or all) rule sets.
      - C(gathered): Read firewall rule config from device.
    type: str
    choices: [merged, replaced, overridden, deleted, gathered]
    default: merged
  hostname:
    description: IP address or FQDN of the VyOS device.
    type: str
    required: true
  port:
    description: HTTPS port for the REST API.
    type: int
    default: 443
  api_key:
    description: API key configured on the device.
    type: str
    required: true
    no_log: true
  timeout:
    description: Request timeout in seconds.
    type: int
    default: 30
  verify_ssl:
    description: Validate the device's TLS certificate.
    type: bool
    default: false
requirements:
  - VyOS 1.3+
seealso:
  - module: vyos.vyos.vyos_firewall_rules
examples: |
  - name: Create an IPv4 firewall rule set
    vyos.rest.vyos_firewall_rules:
      hostname: 192.168.1.1
      api_key: MY-KEY
      config:
        - afi: ipv4
          rule_sets:
            - name: OUTSIDE-IN
              default_action: drop
              rules:
                - number: 10
                  action: accept
                  protocol: tcp
                  destination:
                    port: "80,443"
                  state:
                    established: true
                    related: true
      state: merged

  - name: Delete all firewall rules
    vyos.rest.vyos_firewall_rules:
      hostname: 192.168.1.1
      api_key: MY-KEY
      state: deleted
"""

RETURN = r"""
before:
  description: Firewall rule config before the module ran.
  returned: always
  type: list
after:
  description: Firewall rule config after the module ran.
  returned: when changed
  type: list
gathered:
  description: Firewall config read from device (state=gathered).
  returned: when state is gathered
  type: list
commands:
  description: set/delete commands issued.
  returned: always
  type: list
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vyos.rest.plugins.module_utils.vyos_rest import (
    VYOS_REST_CONNECTION_ARGSPEC,
    VyOSRestClient,
    VyOSRestError,
)


_FW_PATH = {
    "ipv4": ["firewall", "name"],
    "ipv6": ["firewall", "ipv6-name"],
}


def _get_fw_rules(client):
    try:
        result = client.retrieve_show_config(["firewall"])
        data = result.get("data") or {}
        out = []
        for afi, key in [("ipv4", "name"), ("ipv6", "ipv6-name")]:
            sets_data = data.get(key, {})
            if not isinstance(sets_data, dict):
                continue
            rule_sets = []
            for rs_name, rs_data in sets_data.items():
                if not isinstance(rs_data, dict):
                    continue
                rs = {
                    "name": rs_name,
                    "default_action": rs_data.get("default-action", "drop"),
                }
                if "description" in rs_data:
                    rs["description"] = rs_data["description"]
                rules = []
                for rnum, rdata in (rs_data.get("rule") or {}).items():
                    if not isinstance(rdata, dict):
                        continue
                    rule = {"number": int(rnum)}
                    if "action" in rdata:
                        rule["action"] = rdata["action"]
                    if "description" in rdata:
                        rule["description"] = rdata["description"]
                    if "protocol" in rdata:
                        rule["protocol"] = rdata["protocol"]
                    rule["enabled"] = "disable" not in rdata
                    rules.append(rule)
                if rules:
                    rs["rules"] = sorted(rules, key=lambda r: r["number"])
                rule_sets.append(rs)
            if rule_sets:
                out.append({"afi": afi, "rule_sets": rule_sets})
        return out
    except VyOSRestError:
        return []


def _apply_rule_set(client, afi, rs, commands):
    base = _FW_PATH[afi] + [rs["name"]]
    client.configure_set(base)
    commands.append("set {p}".format(p=" ".join(base)))

    if rs.get("default_action"):
        client.configure_set(base + ["default-action"], rs["default_action"])
        commands.append(
            "set {p} default-action {a}".format(
                p=" ".join(base),
                a=rs["default_action"],
            ),
        )
    if rs.get("description"):
        client.configure_set(base + ["description"], rs["description"])
        commands.append(
            "set {p} description '{d}'".format(
                p=" ".join(base),
                d=rs["description"],
            ),
        )

    for rule in rs.get("rules") or []:
        rbase = base + ["rule", str(rule["number"])]
        client.configure_set(rbase)
        commands.append("set {p}".format(p=" ".join(rbase)))

        if rule.get("action"):
            client.configure_set(rbase + ["action"], rule["action"])
            commands.append(
                "set {p} action {a}".format(p=" ".join(rbase), a=rule["action"]),
            )
        if rule.get("description"):
            client.configure_set(rbase + ["description"], rule["description"])
        if rule.get("protocol"):
            client.configure_set(rbase + ["protocol"], rule["protocol"])
            commands.append(
                "set {p} protocol {pr}".format(
                    p=" ".join(rbase),
                    pr=rule["protocol"],
                ),
            )
        for direction in ("source", "destination"):
            match = rule.get(direction)
            if not match:
                continue
            mbase = rbase + [direction]
            if match.get("address"):
                client.configure_set(mbase + ["address"], match["address"])
                commands.append(
                    "set {p} address '{a}'".format(
                        p=" ".join(mbase),
                        a=match["address"],
                    ),
                )
            if match.get("port"):
                client.configure_set(mbase + ["port"], match["port"])
                commands.append(
                    "set {p} port {pt}".format(
                        p=" ".join(mbase),
                        pt=match["port"],
                    ),
                )

        state_match = rule.get("state")
        if state_match:
            sbase = rbase + ["state"]
            for st_name in ("established", "new", "related", "invalid"):
                if state_match.get(st_name):
                    client.configure_set(sbase + [st_name], "enable")
                    commands.append(
                        "set {p} {s} enable".format(
                            p=" ".join(sbase),
                            s=st_name,
                        ),
                    )

        if "enabled" in rule and not rule["enabled"]:
            client.configure_set(rbase + ["disable"])
            commands.append("set {p} disable".format(p=" ".join(rbase)))


def main():
    rule_spec = dict(
        number=dict(type="int", required=True),
        action=dict(type="str", choices=["drop", "reject", "accept", "inspect"]),
        description=dict(type="str"),
        protocol=dict(type="str"),
        source=dict(
            type="dict",
            options=dict(
                address=dict(type="str"),
                port=dict(type="str"),
                group=dict(
                    type="dict",
                    options=dict(
                        address_group=dict(type="str"),
                        network_group=dict(type="str"),
                    ),
                ),
            ),
        ),
        destination=dict(
            type="dict",
            options=dict(
                address=dict(type="str"),
                port=dict(type="str"),
                group=dict(
                    type="dict",
                    options=dict(
                        address_group=dict(type="str"),
                        network_group=dict(type="str"),
                    ),
                ),
            ),
        ),
        state=dict(
            type="dict",
            options=dict(
                established=dict(type="bool"),
                new=dict(type="bool"),
                related=dict(type="bool"),
                invalid=dict(type="bool"),
            ),
        ),
        enabled=dict(type="bool", default=True),
    )

    argument_spec = dict(
        config=dict(
            type="list",
            elements="dict",
            options=dict(
                afi=dict(type="str", required=True, choices=["ipv4", "ipv6"]),
                rule_sets=dict(
                    type="list",
                    elements="dict",
                    options=dict(
                        name=dict(type="str", required=True),
                        default_action=dict(
                            type="str",
                            choices=["drop", "reject", "accept"],
                            default="drop",
                        ),
                        description=dict(type="str"),
                        rules=dict(type="list", elements="dict", options=rule_spec),
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

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    client = VyOSRestClient(module)
    state = module.params["state"]
    config = module.params.get("config") or []
    commands = []
    changed = False

    before = _get_fw_rules(client)

    if state == "gathered":
        module.exit_json(changed=False, gathered=before, before=before, commands=[])

    if module.check_mode:
        module.exit_json(changed=True, before=before, commands=["(check mode)"])

    try:
        if state in ("deleted", "overridden") and not config:
            for afi_key in ("name", "ipv6-name"):
                try:
                    client.configure_delete(["firewall", afi_key])
                    commands.append(
                        "delete firewall {k}".format(k=afi_key),
                    )
                except VyOSRestError:
                    pass
            changed = True

        elif state == "deleted" and config:
            for entry in config:
                afi = entry["afi"]
                base_path = _FW_PATH[afi]
                for rs in entry.get("rule_sets") or []:
                    try:
                        client.configure_delete(base_path + [rs["name"]])
                        commands.append(
                            "delete {p} {n}".format(
                                p=" ".join(base_path),
                                n=rs["name"],
                            ),
                        )
                        changed = True
                    except VyOSRestError:
                        pass

        elif state in ("merged", "replaced", "overridden"):
            if state == "replaced":
                for entry in config:
                    afi = entry["afi"]
                    base_path = _FW_PATH[afi]
                    for rs in entry.get("rule_sets") or []:
                        try:
                            client.configure_delete(base_path + [rs["name"]])
                            commands.append(
                                "delete {p} {n}".format(
                                    p=" ".join(base_path),
                                    n=rs["name"],
                                ),
                            )
                        except VyOSRestError:
                            pass
            for entry in config:
                afi = entry["afi"]
                for rs in entry.get("rule_sets") or []:
                    _apply_rule_set(client, afi, rs, commands)
                    changed = True
    except VyOSRestError as exc:
        module.fail_json(msg=str(exc))

    after = _get_fw_rules(client) if changed else before
    module.exit_json(changed=changed, before=before, after=after, commands=commands)


if __name__ == "__main__":
    main()

#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+
from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_nat
short_description: Manage NAT configuration on VyOS devices using REST API
description:
  - Manages NAT configuration on VyOS devices via the REST API.
  - Supports source, destination, static, CGNAT, NAT64, and NAT66.
  - Uses REST API (C(connection=httpapi)) instead of CLI.
  - Targets VyOS 1.5+.
version_added: "1.0.0"
author:
  - Evgeny Molotkov (@omnom62)
options:
  config:
    description: NAT configuration.
    type: dict
  state:
    description:
      - The desired state of the NAT configuration.
    type: str
    default: merged
    choices: [merged, replaced, overridden, deleted, gathered]
"""

EXAMPLES = r"""
- name: Merge source NAT rule
  vyos.rest.vyos_nat:
    config:
      nat:
        source:
          rule:
            - id: 100
              outbound_interface:
                name: eth0
              translation:
                address: masquerade
    state: merged

- name: Delete all NAT
  vyos.rest.vyos_nat:
    state: deleted

- name: Gather NAT configuration
  vyos.rest.vyos_nat:
    state: gathered
"""

RETURN = r"""
before:
  description: NAT configuration before this module ran.
  returned: always
  type: dict
after:
  description: NAT configuration after this module ran.
  returned: when changed
  type: dict
commands:
  description: List of API commands sent to the device.
  returned: always
  type: list
gathered:
  description: Current NAT configuration as structured data.
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
    autoclean,
    dict_op,
    from_device,
    normalize_have,
    to_tag_dict,
)


_NAT_TYPES = ("nat", "nat64", "nat66")

# "rule" (any NAT rule set) and "backend" (load-balance) are genuine tag
# nodes everywhere they appear -- unambiguous. "range" is NOT included
# here: confirmed against vyos-1x that it means two different things
# depending on parent -- cgnat.pool.external.<name>.range is a tagNode
# (has a nested "seq" leaf), but cgnat.pool.internal.<name>.range is a
# plain multi-value leafNode (<multi/>). Handling that context-sensitive
# case generically by key name alone would silently corrupt one or the
# other, so it's handled explicitly in _normalize_cgnat_have() instead.
_TAG_KEYS = {"rule", "backend"}


# ---------------------------------------------------------------------------
# load_balance.backend / nat64 translation.pool — the only two genuine
# structural exceptions in this module (confirmed tagNodes with nested
# substructure). Every other field (destination/source/translation/
# match, inbound/outbound-interface, exclude, disable, description,
# protocol, packet_type, load_balance.hash) is a direct structural match
# and flows through autoclean/from_device untouched. hash in particular
# stays a plain list -- it's a multi-value leafNode, not a tag node, so
# dict_op's own native list handling applies to it directly.
# ---------------------------------------------------------------------------


def _backend_to_device(backends):
    return {b["ip"]: autoclean({k: v for k, v in b.items() if k != "ip"}) for b in backends or []}


def _backend_from_device(raw):
    result = []
    for ip, data in sorted((raw or {}).items()):
        entry = {"ip": ip, **from_device(data or {})}
        if "weight" in entry:
            entry["weight"] = int(entry["weight"])
        result.append(entry)
    return result


def _pool_to_device(pools):
    return {str(p["id"]): autoclean({k: v for k, v in p.items() if k != "id"}) for p in pools or []}


def _pool_from_device(raw):
    return [
        {"id": int(pid), **from_device(data or {})}
        for pid, data in sorted((raw or {}).items(), key=lambda kv: int(kv[0]))
    ]


def _rule_to_device(rule):
    entry = autoclean(
        {k: v for k, v in rule.items() if k not in ("id", "load_balance", "translation")},
    )

    lb = rule.get("load_balance")
    if lb:
        lb_entry = autoclean({k: v for k, v in lb.items() if k != "backend"})
        if lb.get("backend"):
            lb_entry["backend"] = _backend_to_device(lb["backend"])
        entry["load_balance"] = lb_entry

    translation = rule.get("translation")
    if translation:
        t_entry = autoclean({k: v for k, v in translation.items() if k != "pool"})
        if translation.get("pool"):
            t_entry["pool"] = _pool_to_device(translation["pool"])
        entry["translation"] = t_entry

    return entry


def _rule_from_device(raw):
    raw = raw or {}
    entry = from_device({k: v for k, v in raw.items() if k not in ("load-balance", "translation")})

    lb_raw = raw.get("load-balance")
    if lb_raw:
        lb_entry = from_device({k: v for k, v in lb_raw.items() if k != "backend"})
        # "hash" is a multi-value leafNode; the device can collapse a
        # single value to a bare string. from_device() only does
        # kebab->snake translation, not type coercion, so fix that up
        # explicitly here (there's no ARGUMENT_SPEC for cast_by_spec to
        # derive this from -- config is a bare type=dict in this module).
        if isinstance(lb_entry.get("hash"), str):
            lb_entry["hash"] = [lb_entry["hash"]]
        if lb_raw.get("backend"):
            lb_entry["backend"] = _backend_from_device(lb_raw["backend"])
        entry["load_balance"] = lb_entry

    t_raw = raw.get("translation")
    if t_raw:
        t_entry = from_device({k: v for k, v in t_raw.items() if k != "pool"})
        if t_raw.get("pool"):
            t_entry["pool"] = _pool_from_device(t_raw["pool"])
        entry["translation"] = t_entry

    return entry


def _rules_to_device(rules):
    return {str(r["id"]): _rule_to_device(r) for r in rules or []}


def _rules_from_device(raw):
    return [
        {"id": int(rid), **_rule_from_device(data or {})}
        for rid, data in sorted((raw or {}).items(), key=lambda kv: int(kv[0]))
    ]


# ---------------------------------------------------------------------------
# CGNAT — cgnat.pool.external.<name>.range is a genuine tag node
# (confirmed: nested "seq" leaf); cgnat.pool.internal.<name>.range is a
# plain multi-value leafNode (confirmed <multi/>). Fixing the real bug
# here: the previous implementation only checked isinstance(str)/
# isinstance(dict) for internal range and silently dropped it whenever
# the device returned the actual real shape -- a plain list.
# ---------------------------------------------------------------------------


def _cgnat_pool_external_to_device(pools):
    result = {}
    for p in pools or []:
        entry = autoclean({k: v for k, v in p.items() if k not in ("name", "range")})
        if p.get("range"):
            entry["range"] = {
                r["value"]: ({"seq": r["seq"]} if r.get("seq") is not None else {})
                for r in p["range"]
            }
        result[p["name"]] = entry
    return result


def _cgnat_pool_external_from_device(raw):
    result = []
    for name, data in sorted((raw or {}).items()):
        data = data or {}
        p = {"name": name, **from_device({k: v for k, v in data.items() if k != "range"})}
        rng = data.get("range")
        if rng:
            rng_dict = to_tag_dict(rng)
            p["range"] = [
                (
                    {"value": v, "seq": int(d["seq"])}
                    if isinstance(d, dict) and d.get("seq")
                    else {"value": v}
                )
                for v, d in sorted(rng_dict.items())
            ]
        result.append(p)
    return result


def _cgnat_pool_internal_to_device(pools):
    return {p["name"]: {"range": list(p["range"])} for p in pools or [] if p.get("range")}


def _cgnat_pool_internal_from_device(raw):
    result = []
    for name, data in sorted((raw or {}).items()):
        rng = (data or {}).get("range")
        p = {"name": name}
        if rng:
            # Confirmed real bug in the previous implementation: it only
            # checked isinstance(str)/isinstance(dict) here, silently
            # dropping "range" entirely whenever the device returned the
            # actual real shape for >1 value -- a plain list.
            p["range"] = [rng] if isinstance(rng, str) else list(rng)
        result.append(p)
    return result


# The two known CGNAT pool kinds and their handlers, declared once. Both
# are unavoidable exceptions -- "external" pool range is a tag node
# (confirmed: nested "seq" leaf), "internal" pool range is a plain
# multi-value leaf (confirmed <multi/>), same key name, genuinely
# different device shape, not discoverable by walking the JSON alone.
# What's NOT necessary is repeating "if pool.get(kind)" per kind inline
# -- one table declares the exception, both directions read it.
_CGNAT_POOL_KINDS = {
    "external": (_cgnat_pool_external_to_device, _cgnat_pool_external_from_device),
    "internal": (_cgnat_pool_internal_to_device, _cgnat_pool_internal_from_device),
}


def _cgnat_pool_to_device(pool):
    return {
        kind: to_fn(pool[kind])
        for kind, (to_fn, _from_fn) in _CGNAT_POOL_KINDS.items()
        if pool.get(kind)
    }


def _cgnat_pool_from_device(pool_raw):
    return {
        kind: from_fn(pool_raw[kind])
        for kind, (_to_fn, from_fn) in _CGNAT_POOL_KINDS.items()
        if pool_raw.get(kind)
    }


def _normalize_cgnat_have(cgnat_raw):
    """Like normalize_have(), but external/internal pool "range" needs
    different treatment despite sharing a key name -- see _TAG_KEYS.
    """
    if not cgnat_raw or not isinstance(cgnat_raw, dict):
        return {}
    result = normalize_have(cgnat_raw, _TAG_KEYS)
    ext_raw = (cgnat_raw.get("pool") or {}).get("external")
    if ext_raw:
        ext_norm = {}
        for name, data in ext_raw.items():
            data = dict(data or {})
            if "range" in data:
                data["range"] = to_tag_dict(data["range"])
            ext_norm[name] = data
        result.setdefault("pool", {})["external"] = ext_norm
    return result


def _cgnat_to_device(cgnat):
    if not cgnat:
        return {}
    entry = autoclean({k: v for k, v in cgnat.items() if k not in ("pool", "rule")})
    pool = cgnat.get("pool") or {}
    pool_entry = _cgnat_pool_to_device(pool)
    if pool_entry:
        entry["pool"] = pool_entry
    if cgnat.get("rule"):
        entry["rule"] = _rules_to_device(cgnat["rule"])
    return entry


def _cgnat_from_device(raw):
    raw = raw or {}
    entry = from_device({k: v for k, v in raw.items() if k not in ("pool", "rule")})
    pool_entry = _cgnat_pool_from_device(raw.get("pool") or {})
    if pool_entry:
        entry["pool"] = pool_entry
    if raw.get("rule"):
        entry["rule"] = _rules_from_device(raw["rule"])
    return entry


# ---------------------------------------------------------------------------
# want -> device / device -> argspec (top level)
# ---------------------------------------------------------------------------


# Which sections are valid under each NAT type, and whether it has a
# cgnat subtree (only "nat" does) -- declared once so _want_to_device and
# _device_to_argspec each need a single loop instead of three near-
# identical hand-written blocks per NAT type.
_NAT_TYPE_SECTIONS = {
    "nat": ("destination", "source", "static"),
    "nat64": ("source",),
    "nat66": ("destination", "source"),
}


def _want_to_device(config):
    if not config:
        return {}
    result = {}
    for nat_type, sections in _NAT_TYPE_SECTIONS.items():
        nat = config.get(nat_type) or {}
        if not nat:
            continue
        nat_dev = {}
        if nat_type == "nat" and nat.get("cgnat"):
            nat_dev["cgnat"] = _cgnat_to_device(nat["cgnat"])
        for section in sections:
            rules = (nat.get(section) or {}).get("rule")
            if rules:
                nat_dev[section] = {"rule": _rules_to_device(rules)}
        if nat_dev:
            result[nat_type] = nat_dev
    return result


def _device_to_argspec(raw_all):
    if not raw_all:
        return {}
    result = {}
    for nat_type, sections in _NAT_TYPE_SECTIONS.items():
        nat = raw_all.get(nat_type) or {}
        if not nat:
            continue
        nat_arg = {}
        if nat_type == "nat" and nat.get("cgnat"):
            nat_arg["cgnat"] = _cgnat_from_device(nat["cgnat"])
        for section in sections:
            rules = (nat.get(section) or {}).get("rule")
            if rules:
                nat_arg[section] = {"rule": _rules_from_device(rules)}
        if nat_arg:
            result[nat_type] = nat_arg
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def _get_raw(vyos):
    """Retrieve all NAT config from device."""
    result = {}
    for nat_type in _NAT_TYPES:
        raw = vyos.get_config([nat_type])
        if raw:
            result[nat_type] = raw
    return result


def _normalize_nat_have(raw_have, nat_type):
    """normalize_have() for a given NAT type's have data, with "nat"'s
    cgnat section handled by the range-context-aware
    _normalize_cgnat_have() instead of the generic pass (which would
    mishandle internal-pool range -- see _TAG_KEYS).
    """
    nat_raw = raw_have.get(nat_type, {})
    result = normalize_have(nat_raw, _TAG_KEYS)
    if nat_type == "nat" and nat_raw.get("cgnat"):
        result["cgnat"] = _normalize_cgnat_have(nat_raw["cgnat"])
    return result


def main():
    argument_spec = dict(
        config=dict(type="dict"),
        state=dict(
            default="merged",
            choices=["merged", "replaced", "overridden", "deleted", "gathered"],
        ),
    )

    module = AnsibleModule(argument_spec, supports_check_mode=True)
    vyos = VyOSModule(module)

    state = module.params["state"]
    config = module.params.get("config") or {}

    raw_have = _get_raw(vyos)
    have = _device_to_argspec(raw_have)

    if state == "gathered":
        module.exit_json(changed=False, gathered=have)

    want_device = _want_to_device(config)

    if state == "deleted":
        commands = []
        if not config:
            for nat_type in _NAT_TYPES:
                if raw_have.get(nat_type):
                    commands.append(("delete", [nat_type]))
        else:
            for nat_type in _NAT_TYPES:
                if config.get(nat_type) and raw_have.get(nat_type):
                    commands.append(("delete", [nat_type]))
    elif state == "overridden":
        commands = []
        for nat_type in _NAT_TYPES:
            nat_want = want_device.get(nat_type, {})
            nat_have_norm = _normalize_nat_have(raw_have, nat_type)
            base = [nat_type]
            commands += dict_op(nat_want, nat_have_norm, base, op="purge")
            commands += dict_op(nat_want, nat_have_norm, base, op="set")
    else:
        commands = []
        for nat_type in _NAT_TYPES:
            nat_want = want_device.get(nat_type, {})
            nat_have_norm = _normalize_nat_have(raw_have, nat_type)
            base = [nat_type]
            if state == "replaced":
                for section, section_want in nat_want.items():
                    section_have = nat_have_norm.get(section, {})
                    commands += dict_op(section_want, section_have, base + [section], op="purge")
            commands += dict_op(nat_want, nat_have_norm, base, op="set")

    if module.check_mode:
        module.exit_json(changed=bool(commands), commands=commands, before=have)

    if commands:
        response = vyos.apply_commands(commands)
        saved = vyos.save_config()
        after = _device_to_argspec(_get_raw(vyos))
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

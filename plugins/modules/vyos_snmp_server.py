#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_snmp_server
short_description: Manage SNMP server configuration on VyOS devices using REST API
description:
  - Manages SNMP server configuration on VyOS devices via the REST API.
  - Supports communities, listen addresses, contact/location/description,
    trap target, and SNMPv3 (engine ID, groups, users, views).
  - Uses REST API (C(connection=httpapi)) instead of CLI.
version_added: "1.0.0"
author: your_name (@yourhandle)
options:
  config:
    description: SNMP server configuration.
    type: dict
    suboptions:
      communities:
        description: SNMP community configuration.
        type: list
        elements: dict
        suboptions:
          name:
            description: Community name.
            type: str
            required: true
          clients:
            description: IP addresses of SNMP clients allowed to contact the system.
            type: list
            elements: str
          networks:
            description: Subnets of SNMP clients allowed to contact the system.
            type: list
            elements: str
          authorization_type:
            description: Authorization type (ro=read-only, rw=read-write).
            type: str
            choices: ['ro', 'rw']
      contact:
        description: Contact person for the system.
        type: str
      description:
        description: System description.
        type: str
      location:
        description: System location.
        type: str
      smux_peer:
        description: >-
          Register a subtree for SMUX-based processing. The device supports
          multiple values here; this module manages a single value only.
        type: str
      trap_source:
        description: SNMP trap source address.
        type: str
      listen_addresses:
        description: IP addresses to listen for incoming SNMP requests.
        type: list
        elements: dict
        suboptions:
          address:
            description: IP address to listen on.
            type: str
            required: true
          port:
            description: UDP port (default 161).
            type: int
      trap_target:
        description: >-
          SNMP (v2) trap target. The device supports multiple trap targets;
          this module manages a single one only.
        type: dict
        suboptions:
          address:
            description: IP address of the trap target host.
            type: str
            required: true
          community:
            description: Community name to use for traps.
            type: str
          port:
            description: UDP port on the trap target host.
            type: int
      snmp_v3:
        description: SNMPv3 configuration.
        type: dict
        suboptions:
          engine_id:
            description: EngineID as a hex string.
            type: str
          groups:
            description: SNMPv3 group configuration.
            type: list
            elements: dict
            suboptions:
              group:
                description: Group name.
                type: str
                required: true
              mode:
                description: Access mode (ro=read-only, rw=read-write).
                type: str
                choices: ['ro', 'rw']
              seclevel:
                description: Minimum security level required for group members.
                type: str
                choices: ['auth', 'priv']
              view:
                description: View name the group has access to.
                type: str
          users:
            description: SNMPv3 user configuration.
            type: list
            elements: dict
            suboptions:
              user:
                description: Username.
                type: str
                required: true
              authentication:
                description: Authentication parameters for this user.
                type: dict
                suboptions:
                  type:
                    description: Authentication algorithm.
                    type: str
                  encrypted_key:
                    description: >-
                      Encrypted authentication key (stored as encrypted-password
                      on device).
                    type: str
                  plaintext_key:
                    description: Plaintext authentication key (device encrypts it).
                    type: str
              privacy:
                description: Privacy (encryption) parameters for this user.
                type: dict
                suboptions:
                  type:
                    description: Privacy algorithm.
                    type: str
                  encrypted_key:
                    description: Encrypted privacy key.
                    type: str
                  plaintext_key:
                    description: Plaintext privacy key (device encrypts it).
                    type: str
              group:
                description: Group this user belongs to.
                type: str
              mode:
                description: Access mode for this user.
                type: str
                choices: ['ro', 'rw']
              tsm_key:
                description: TSM fingerprint of the certificate mapped to this user.
                type: str
          trap_targets:
            description: SNMPv3 trap target configuration.
            type: list
            elements: dict
            suboptions:
              address:
                description: IP address of the SNMPv3 trap target.
                type: str
                required: true
              port:
                description: UDP port on the trap target host.
                type: int
              protocol:
                description: Transport protocol for traps.
                type: str
                choices: ['tcp', 'udp']
              type:
                description: Trap type.
                type: str
                choices: ['inform', 'trap']
              authentication:
                description: Authentication parameters for trap target.
                type: dict
                suboptions:
                  type:
                    description: Authentication algorithm.
                    type: str
                  encrypted_key:
                    description: Encrypted authentication key.
                    type: str
                  plaintext_key:
                    description: Plaintext authentication key.
                    type: str
              privacy:
                description: Privacy parameters for trap target.
                type: dict
                suboptions:
                  type:
                    description: Privacy algorithm.
                    type: str
                  encrypted_key:
                    description: Encrypted privacy key.
                    type: str
                  plaintext_key:
                    description: Plaintext privacy key.
                    type: str
          views:
            description: >-
              SNMPv3 view configuration. The device supports multiple OIDs
              (each with its own exclude/mask) per view; this module manages
              a single OID entry per view only.
            type: list
            elements: dict
            suboptions:
              view:
                description: View name.
                type: str
                required: true
              oid:
                description: OID subtree included in this view.
                type: str
              exclude:
                description: OID subtree excluded from this view.
                type: str
              mask:
                description: OID mask for the view.
                type: str
  state:
    description:
      - Desired state of SNMP configuration.
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
- name: Merge SNMP configuration
  vyos.rest.vyos_snmp_server:
    config:
      communities:
        - name: switches
          authorization_type: rw
        - name: bridges
          clients:
            - 1.1.1.1
            - 12.1.1.10
      contact: admin2@ex.com
      listen_addresses:
        - address: 20.1.1.1
        - address: 100.1.2.1
          port: 33
      snmp_v3:
        users:
          - user: admin_user
            authentication:
              plaintext_key: abc1234567
              type: sha
            privacy:
              plaintext_key: abc1234567
              type: aes
    state: merged

- name: Delete all SNMP configuration
  vyos.rest.vyos_snmp_server:
    state: deleted

- name: Gather current SNMP configuration
  vyos.rest.vyos_snmp_server:
    state: gathered
"""

RETURN = r"""
before:
  description: SNMP configuration before this module ran.
  returned: when state is merged, replaced, overridden or deleted
  type: dict
after:
  description: SNMP configuration after this module ran.
  returned: when changed
  type: dict
commands:
  description: List of API command tuples sent to the device.
  returned: always
  type: list
gathered:
  description: Current SNMP configuration as structured data.
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
    cast_by_spec,
    dict_op,
    from_device,
    to_tag_dict,
)


_BASE = ["service", "snmp"]

# ---------------------------------------------------------------------------
# The one thing a purely structural walk of ARGUMENT_SPEC can never
# infer: a handful of field names that mean something different on the
# device than in the argspec, and aren't a mechanical kebab<->snake
# conversion dict_op could handle itself. Declared once, here, as a
# flat value map -- not embedded in ARGUMENT_SPEC (keeping that 100%
# standard Ansible), and not scattered across per-section transform
# functions. Confirmed against vyos-1x for every entry:
#   - authorization_type/clients/networks: communities' fields don't
#     match their device leaf names at all ("authorization"/"client"/
#     "network").
#   - authentication/encrypted_key/plaintext_key: shared by v3 users
#     and v3 trap-targets (both nest under a device "auth" node with
#     "encrypted-password"/"plaintext-password" leaves). This is also
#     a real bug fix -- the previous implementation used "plaintext-
#     key", which does not exist on the device at all.
#   - engine_id: "engineid" on the device is one word, so there's no
#     hyphen for the mechanical conversion to split on.
# None of these names are reused elsewhere in this argspec with a
# different intended device mapping (confirmed by inspection), so one
# flat map is safe here -- a module with a genuine name collision
# across nesting levels (this one doesn't have one) would need the map
# scoped by path instead.
_DEVICE_RENAMES = {
    "communities": "community",
    "listen_addresses": "listen-address",
    "snmp_v3": "v3",
    "authorization_type": "authorization",
    "clients": "client",
    "networks": "network",
    "authentication": "auth",
    "encrypted_key": "encrypted-password",
    "plaintext_key": "plaintext-password",
    "engine_id": "engineid",
    "groups": "group",
    "users": "user",
    "views": "view",
    "trap_targets": "trap-target",
}


def _derive_key_field(options_spec):
    """The field identifying each entry in a named-list section is
    never inferable from a generic walk alone -- but it doesn't need
    to be hand-declared either: every such section in this argspec
    already marks exactly one suboption required=True (you can't
    create a community without a name, a user without a username).
    Deriving it here means the key field is asserted to exist by the
    argspec itself, not duplicated in a place that could drift out of
    sync with it.
    """
    required = [k for k, spec in options_spec.items() if spec.get("required")]
    if len(required) != 1:
        raise ValueError(
            "expected exactly one required suboption to serve as the key field, "
            "found: {0}".format(required),
        )
    return required[0]


def _keyed_list_to_device(items, key_field, entry_transform=None):
    """A list of dicts, each identified by key_field's value, becomes a
    device dict keyed by that value -- the one structural mechanic
    every named-list section in this module needs. entry_transform
    supplies whatever else is genuinely irreducible for a given section
    (a nested reshape) -- defaulting to the generic recursive walker.
    """
    entry_transform = entry_transform or autoclean
    result = {}
    for item in items or []:
        if not item.get(key_field):
            continue
        rest = {k: v for k, v in item.items() if k != key_field}
        result[item[key_field]] = entry_transform(rest)
    return result


def _keyed_list_from_device(raw, key_field, entry_transform=None):
    entry_transform = entry_transform or from_device
    return [
        {key_field: key, **entry_transform(data or {})}
        for key, data in sorted(to_tag_dict(raw).items())
    ]


def _single_to_device(obj, key_field):
    """trap_target (v2): confirmed a genuine tagNode keyed by address,
    but the argspec models only a single object (documented
    limitation, preserved as-is: the device supports multiple trap
    targets, this module manages one). Reuses the same keyed-list
    mechanic above as "a list capped to one entry" rather than a
    bespoke pair of functions.
    """
    if not obj or not obj.get(key_field):
        return {}
    return _keyed_list_to_device([obj], key_field)


def _single_from_device(raw, key_field):
    entries = _keyed_list_from_device(raw, key_field)
    return entries[0] if entries else None


# ---------------------------------------------------------------------------
# v3 views — the confirmed structural bug fix. "oid" is a genuine tag
# node (keyed by the OID value itself) with its own "exclude"/"mask"
# children -- the previous implementation treated "oid" as a flat leaf
# and read exclude/mask from the wrong nesting level entirely (directly
# under the view, when they actually live under view.oid.<value>). This
# is a genuine arity change (three sibling scalar fields collapse into
# one nested tag node), not a rename -- it can't be expressed through
# _DEVICE_RENAMES, so it's the one section needing a real override
# instead of the generic recursive walker. The device also supports
# multiple OIDs per view and multiple excludes per OID (both <multi/> /
# tagNode); the argspec only models one of each -- a documented
# limitation, preserved as-is, not expanded here.
# ---------------------------------------------------------------------------


def _view_entry_to_device(rest):
    entry = autoclean({k: v for k, v in rest.items() if k not in ("oid", "exclude", "mask")})
    if rest.get("oid"):
        oid_entry = {}
        if rest.get("exclude"):
            oid_entry["exclude"] = [rest["exclude"]]
        if rest.get("mask"):
            oid_entry["mask"] = rest["mask"]
        entry["oid"] = {rest["oid"]: oid_entry}
    return entry


def _view_entry_from_device(data):
    entry = {}
    oid_raw = (data or {}).get("oid")
    if oid_raw:
        oid_dict = to_tag_dict(oid_raw)
        oid_value, oid_data = sorted(oid_dict.items())[0]
        entry["oid"] = oid_value
        oid_data = oid_data or {}
        excl_raw = oid_data.get("exclude")
        if excl_raw:
            excl_list = (
                [excl_raw] if isinstance(excl_raw, str) else sorted(to_tag_dict(excl_raw).keys())
            )
            entry["exclude"] = excl_list[0]
        if oid_data.get("mask"):
            entry["mask"] = oid_data["mask"]
    return entry


# Sections needing something other than the generic recursive walker,
# keyed by the argspec field name -- a second small value map, kept
# separate from _DEVICE_RENAMES because it answers a different
# question (how to build/parse each entry, not what to call a field).
# Every other named-list section in this module (communities,
# listen_addresses, v3 groups/users/trap_targets) needs neither: their
# member fields either match the device 1:1 or are covered by
# _DEVICE_RENAMES, so the generic walker handles them with no entry
# here at all.
_ENTRY_OVERRIDES = {
    "views": (_view_entry_to_device, _view_entry_from_device),
}


# ---------------------------------------------------------------------------
# The generic recursive walker. Driven entirely by ARGUMENT_SPEC's own
# structure (type=dict -> recurse; type=list with options -> a named
# list, keyed by _derive_key_field; type=list with no options -> a
# plain multi-value leaf, left to dict_op's own list handling) plus the
# two small value maps above for the handful of cases structure alone
# can't resolve. This is what replaced a hand-written to-device/from-
# device function pair for every single section in this module.
# ---------------------------------------------------------------------------


def _spec_to_device(value, options_spec):
    if not isinstance(value, dict):
        return value
    result = {}
    for arg_key, sub_spec in options_spec.items():
        val = value.get(arg_key)
        if val is None or val is False:
            continue
        device_key = _DEVICE_RENAMES.get(arg_key, arg_key)
        sub_type = sub_spec.get("type")
        sub_options = sub_spec.get("options")
        if sub_type == "dict" and sub_options:
            converted = _spec_to_device(val, sub_options)
            if converted:
                result[device_key] = converted
        elif sub_type == "list" and sub_options:
            key_field = _derive_key_field(sub_options)
            entry_to, _entry_from = _ENTRY_OVERRIDES.get(arg_key, (None, None))
            entry_transform = entry_to or (
                lambda rest, spec=sub_options: _spec_to_device(rest, spec)
            )
            result[device_key] = _keyed_list_to_device(val, key_field, entry_transform)
        elif val is True:
            result[device_key] = {}
        elif sub_type == "list":
            result[device_key] = list(val)
        else:
            result[device_key] = val
    return result


def _device_to_spec(raw, options_spec):
    if not raw or not isinstance(raw, dict):
        return {}
    have_idx = {k.replace("-", "_"): k for k in raw}
    result = {}
    for arg_key, sub_spec in options_spec.items():
        device_key = _DEVICE_RENAMES.get(arg_key, arg_key)
        orig_key = device_key if device_key in raw else have_idx.get(arg_key)
        if orig_key is None:
            continue
        raw_val = raw[orig_key]
        sub_type = sub_spec.get("type")
        sub_options = sub_spec.get("options")
        if sub_type == "dict" and sub_options:
            converted = _device_to_spec(raw_val, sub_options)
            if converted:
                result[arg_key] = converted
        elif sub_type == "list" and sub_options:
            key_field = _derive_key_field(sub_options)
            _entry_to, entry_from = _ENTRY_OVERRIDES.get(arg_key, (None, None))
            entry_transform = entry_from or (lambda d, spec=sub_options: _device_to_spec(d, spec))
            entries = _keyed_list_from_device(raw_val, key_field, entry_transform)
            if entries:
                result[arg_key] = entries
        elif sub_type == "list":
            if raw_val:
                result[arg_key] = sorted(to_tag_dict(raw_val).keys())
        elif isinstance(raw_val, dict) and not raw_val:
            result[arg_key] = True
        else:
            result[arg_key] = raw_val
    return result


def _want_to_device(config):
    config = config or {}
    want = _spec_to_device(
        {k: v for k, v in config.items() if k != "trap_target"},
        _TOP_OPTIONS,
    )
    if config.get("trap_target"):
        tt = _single_to_device(config["trap_target"], _derive_key_field(_TRAP_TARGET_OPTIONS))
        if tt:
            want["trap-target"] = tt
    return want


def get_running_config(vyos):
    try:
        return vyos.get_config(_BASE) or {}
    except Exception as e:
        if "Configuration under specified path is empty" in str(e):
            return {}
        raise


def _device_to_argspec(raw):
    if not raw:
        return {}
    result = _device_to_spec(
        {k: v for k, v in raw.items() if k != "trap-target"},
        _TOP_OPTIONS,
    )
    if raw.get("trap-target"):
        tt = _single_from_device(raw["trap-target"], _derive_key_field(_TRAP_TARGET_OPTIONS))
        if tt:
            result["trap_target"] = tt
    cast_by_spec(result, _TOP_OPTIONS)
    return result


# Device key names (as they appear in want/have, underscore-normalized)
# whose child dict is a tag node keyed by an opaque value -- a username,
# a community name, any user-supplied identifier -- rather than a schema
# field name.
_VERBATIM_KEYS = {"community", "listen_address", "group", "user", "view", "trap_target"}


def _seed_tag_node_placeholders(want, have, verbatim_keys):
    """dict_op's own key lookup falls back to guessing a translated
    device key whenever a want key is missing from have entirely (a
    brand-new entry). That guess is correct for a schema field name
    (e.g. "trap_source" -> "trap-source" on first set) but wrong for a
    tag-node key, which is an opaque value, not a schema name --
    confirmed as a real bug: a username like "admin_user" was silently
    becoming "admin-user" in the generated command the first time that
    user was created (any tag-node key with an underscore would trigger
    the same, since dict_op can't otherwise tell a schema name from a
    value that merely happens to contain one).

    Rather than teach the shared engine that distinction, this seeds an
    empty placeholder into have (mutated in place) for every tag-node
    entry present in want but not yet in have, keyed by the exact,
    verbatim value from want. dict_op's own unmodified exact-match
    lookup then finds it directly and never reaches its guessing
    fallback at all -- the fix lives entirely in this module, not in
    the shared engine, and every field the entry declares still
    correctly shows up as "missing from have" and gets set, since the
    placeholder is empty.
    """
    if not isinstance(want, dict):
        return
    have_idx = {k.replace("-", "_"): k for k in have}
    for key, want_val in want.items():
        if not isinstance(want_val, dict):
            continue
        norm_key = key.replace("-", "_")
        orig_key = have_idx.get(norm_key, key)
        have_val = have.setdefault(orig_key, {})
        if not isinstance(have_val, dict):
            continue
        if norm_key in verbatim_keys:
            for entry_key in want_val:
                if entry_key not in have_val:
                    have_val[entry_key] = None
        else:
            _seed_tag_node_placeholders(want_val, have_val, verbatim_keys)


_CREDENTIAL_LEAVES = {"encrypted-password", "plaintext-password"}


def _protect_credentials_from_purge(want, have):
    """ "replaced"/"overridden" purge deletes anything in have that
    isn't re-specified in want -- correct for ordinary config, but
    wrong for a write-only credential leaf: the user can never read
    back the current encrypted-password to re-supply it, so its
    absence from a new config must not be read as "remove it".
    Confirmed as a real device-rejected commit: VyOS requires an
    auth/privacy node to carry an encrypted-password or plaintext-
    password whenever the node exists at all, so purging the existing
    hash out from under an unrelated field-level change (e.g. updating
    "type") broke the commit entirely, not just the password.

    Copies have's password leaf into want (mutating want in place)
    wherever want doesn't already supply its own -- purge then sees it
    as unchanged and never deletes it, while a genuinely new
    plaintext_key/encrypted_key the user did provide still overrides
    normally, since this only fills in what's missing.
    """
    if not isinstance(want, dict) or not isinstance(have, dict):
        return
    have_idx = {k.replace("-", "_"): k for k in have}
    for key, want_val in want.items():
        if not isinstance(want_val, dict):
            continue
        norm_key = key.replace("-", "_")
        have_val = have.get(have_idx.get(norm_key, key))
        if not isinstance(have_val, dict):
            continue
        if norm_key in ("auth", "privacy") and not (_CREDENTIAL_LEAVES & set(want_val)):
            for cred in _CREDENTIAL_LEAVES:
                if cred in have_val:
                    want_val[cred] = have_val[cred]
        _protect_credentials_from_purge(want_val, have_val)


def build_commands(config, raw_have, state):
    raw_have = raw_have or {}
    config = config or {}

    if state == "deleted":
        return [("delete", _BASE)] if raw_have else []

    want = _want_to_device(config)
    # Rather than a generic key-name-based normalize_have, round-trip
    # raw_have through the same structural converters used for want.
    # This module has several keys that mean genuinely different things
    # at different nesting depths (community/view/group are each both a
    # tag node at one level and an unrelated scalar leaf at another) --
    # a blanket tag_keys set would wrongly coerce the scalar occurrences
    # into presence-dicts. Going through _device_to_argspec/
    # _want_to_device instead resolves each occurrence with full
    # knowledge of its actual position in the tree, not just its name.
    norm_have = _want_to_device(_device_to_argspec(raw_have))
    _seed_tag_node_placeholders(want, norm_have, _VERBATIM_KEYS)
    _protect_credentials_from_purge(want, norm_have)

    commands = []
    if state == "overridden":
        commands += dict_op(want, norm_have, _BASE, op="purge")
    elif state == "replaced":
        for section, section_want in want.items():
            if not isinstance(section_want, dict):
                continue
            section_have = norm_have.get(section, {})
            commands += dict_op(section_want, section_have, _BASE + [section], op="purge")
    commands += dict_op(want, norm_have, _BASE, op="set")
    return commands


def _auth_privacy_spec():
    return dict(
        type=dict(type="str"),
        encrypted_key=dict(type="str", no_log=False),
        plaintext_key=dict(type="str", no_log=True),
    )


ARGUMENT_SPEC = dict(
    config=dict(
        type="dict",
        options=dict(
            communities=dict(
                type="list",
                elements="dict",
                options=dict(
                    name=dict(type="str", required=True),
                    clients=dict(type="list", elements="str"),
                    networks=dict(type="list", elements="str"),
                    authorization_type=dict(type="str", choices=["ro", "rw"]),
                ),
            ),
            contact=dict(type="str"),
            description=dict(type="str"),
            location=dict(type="str"),
            smux_peer=dict(type="str"),
            trap_source=dict(type="str"),
            listen_addresses=dict(
                type="list",
                elements="dict",
                options=dict(
                    address=dict(type="str", required=True),
                    port=dict(type="int"),
                ),
            ),
            trap_target=dict(
                type="dict",
                options=dict(
                    address=dict(type="str", required=True),
                    community=dict(type="str"),
                    port=dict(type="int"),
                ),
            ),
            snmp_v3=dict(
                type="dict",
                options=dict(
                    engine_id=dict(type="str"),
                    groups=dict(
                        type="list",
                        elements="dict",
                        options=dict(
                            group=dict(type="str", required=True),
                            mode=dict(type="str", choices=["ro", "rw"]),
                            seclevel=dict(type="str", choices=["auth", "priv"]),
                            view=dict(type="str"),
                        ),
                    ),
                    users=dict(
                        type="list",
                        elements="dict",
                        options=dict(
                            user=dict(type="str", required=True),
                            authentication=dict(type="dict", options=_auth_privacy_spec()),
                            privacy=dict(type="dict", options=_auth_privacy_spec()),
                            group=dict(type="str"),
                            mode=dict(type="str", choices=["ro", "rw"]),
                            tsm_key=dict(type="str", no_log=True),
                        ),
                    ),
                    trap_targets=dict(
                        type="list",
                        elements="dict",
                        options=dict(
                            address=dict(type="str", required=True),
                            port=dict(type="int"),
                            protocol=dict(type="str", choices=["tcp", "udp"]),
                            type=dict(type="str", choices=["inform", "trap"]),
                            authentication=dict(type="dict", options=_auth_privacy_spec()),
                            privacy=dict(type="dict", options=_auth_privacy_spec()),
                        ),
                    ),
                    views=dict(
                        type="list",
                        elements="dict",
                        options=dict(
                            view=dict(type="str", required=True),
                            oid=dict(type="str"),
                            exclude=dict(type="str"),
                            mask=dict(type="str"),
                        ),
                    ),
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

_TOP_OPTIONS = ARGUMENT_SPEC["config"]["options"]
_TRAP_TARGET_OPTIONS = _TOP_OPTIONS["trap_target"]["options"]


def main():
    module = AnsibleModule(argument_spec=ARGUMENT_SPEC, supports_check_mode=True)
    vyos = VyOSModule(module)
    state = module.params["state"]
    config = module.params.get("config") or {}

    raw_have = get_running_config(vyos)
    have = _device_to_argspec(raw_have)

    if state == "gathered":
        module.exit_json(changed=False, gathered=have)

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

#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+
from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_user
short_description: Manage user accounts on VyOS devices using REST API
description:
  - Manages local user accounts on VyOS devices via the REST API.
  - Uses REST API (C(connection=httpapi)) instead of CLI.
  - Passwords are write-only. Once set, they cannot be read back in plaintext.
  - Use C(update_password=on_create) to avoid resetting passwords on every run.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  users:
    description: List of user definitions.
    type: list
    elements: dict
    suboptions:
      name:
        description: Username.
        type: str
        required: true
      full_name:
        description: Full name of the user.
        type: str
      password:
        description: Plaintext password. Write-only — hashed on device immediately.
        type: str
      update_password:
        description:
          - Control when password is updated.
          - C(always) updates the password on every run (default).
          - C(on_create) only sets the password when the user is first created.
        type: str
        choices: [always, on_create]
        default: always
      public_keys:
        description: SSH public keys for the user.
        type: list
        elements: dict
        suboptions:
          name:
            description: Key identifier/name.
            type: str
            required: true
          key:
            description: Base64-encoded public key.
            type: str
            required: true
          type:
            description: Key type.
            type: str
            choices: [ssh-dss, ssh-rsa, ecdsa-sha2-nistp256, ecdsa-sha2-nistp384,
                      ecdsa-sha2-nistp521, ssh-ed25519]
            required: true
  state:
    description:
      - C(present) ensures users exist with the specified configuration.
      - C(absent) removes specified users.
      - C(gathered) returns current user configuration as structured data.
    type: str
    choices: [present, absent, gathered]
    default: present
notes:
  - Requires C(ansible_connection=httpapi) with the VyOS httpapi plugin.
  - C(ansible_network_os) must be set to C(vyos.rest.vyos).
  - The C(vyos) user cannot be deleted as it is required for API access.
  - Passwords are hashed immediately by VyOS and cannot be read back.
"""

EXAMPLES = r"""
- name: Create user
  vyos.rest.vyos_user:
    users:
      - name: alice
        full_name: Alice Smith
        password: securepassword
        update_password: on_create
    state: present

- name: Add SSH public key
  vyos.rest.vyos_user:
    users:
      - name: alice
        public_keys:
          - name: alice-laptop
            type: ssh-rsa
            key: AAAAB3NzaC1yc2EAAAADAQABAAAB...
    state: present

- name: Delete user
  vyos.rest.vyos_user:
    users:
      - name: alice
    state: absent

- name: Gather all users
  vyos.rest.vyos_user:
    state: gathered
"""

RETURN = r"""
before:
  description: User configuration before this module ran.
  returned: always
  type: list
after:
  description: User configuration after this module ran.
  returned: when changed
  type: list
commands:
  description: List of API command tuples sent to the device.
  returned: always
  type: list
gathered:
  description: Current user configuration as structured data.
  returned: when state is gathered
  type: list
saved:
  description: Whether the config was saved after changes.
  returned: when changed
  type: bool
response:
  description: Raw API response.
  returned: always
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vyos.rest.plugins.module_utils.vyos import (
    VyOSModule,
    autoclean,
    dict_op,
    from_device,
    normalize_have,
)


_BASE = ["system", "login", "user"]

# "public-keys" is a tag node (keyed by key identifier) that could in
# principle collapse to a bare value for a single entry; defensive only
# -- "key" is required by the argspec so a real collapse is unlikely,
# but the guard costs nothing and matches the pattern used everywhere
# else a tag node is involved.
_TAG_KEYS = {"public-keys"}

# Users this module will never delete under state=absent, no matter what
# the playbook asks for -- "vyos" is required for REST API access itself,
# so deleting it would lock out every subsequent module call.
_PROTECTED_USERS = {"vyos"}


def _public_keys_to_device(keys):
    return {
        k["name"]: autoclean({kk: vv for kk, vv in k.items() if kk != "name"}) for k in keys or []
    }


def _public_keys_from_device(raw):
    return [{"name": name, **from_device(data or {})} for name, data in sorted((raw or {}).items())]


def _user_to_device(user):
    """password/update_password are deliberately excluded here and
    handled entirely outside dict_op in build_commands() -- "password"
    (plaintext, write-only) and have's "encrypted-password" are
    structurally different data with no valid equality comparison
    between them, so whether to set it is a policy decision
    (update_password), never a diff. public_keys nests under a literal
    "authentication" wrapper the argspec doesn't have.
    """
    entry = autoclean(
        {
            k: v
            for k, v in user.items()
            if k not in ("name", "password", "update_password", "public_keys")
        },
    )
    if user.get("public_keys"):
        entry["authentication"] = {"public_keys": _public_keys_to_device(user["public_keys"])}
    return entry


def _user_from_device(name, data):
    data = dict(data or {})
    auth = data.pop("authentication", None) or {}
    entry = {"name": name, **from_device(data)}
    if auth.get("encrypted-password"):
        entry["encrypted_password"] = auth["encrypted-password"]
    pub_keys_raw = auth.get("public-keys")
    if pub_keys_raw:
        entry["public_keys"] = _public_keys_from_device(pub_keys_raw)
    return entry


def get_running_config(vyos):
    raw = vyos.get_config(_BASE) or {}
    if isinstance(raw, dict):
        raw = raw.get("user", raw)
    return raw if isinstance(raw, dict) else {}


def _device_to_argspec(raw):
    if not raw or not isinstance(raw, dict):
        return []
    return [_user_from_device(name, data) for name, data in sorted(raw.items())]


def build_commands(users, raw_have, state):
    raw_have = raw_have or {}
    users = users or []

    if state == "absent":
        commands = []
        for user in users:
            name = user["name"]
            if name in _PROTECTED_USERS:
                continue
            if name in raw_have:
                commands.append(("delete", _BASE + [name]))
        return commands

    # state == "present": additive-only, matches the original module's
    # scope exactly -- existing fields/keys not mentioned in a user's
    # config are left alone, never removed (there's no "replaced" state
    # here to make a full-model rewrite meaningful).
    commands = []
    norm_have = normalize_have(raw_have, _TAG_KEYS)
    for user in users:
        name = user["name"]
        is_new = name not in raw_have
        ubase = _BASE + [name]
        have_user = norm_have.get(name) or {}

        commands += dict_op(_user_to_device(user), have_user, ubase, op="set")

        if user.get("password"):
            update_policy = user.get("update_password", "always")
            if update_policy == "always" or is_new:
                commands.append(
                    ("set", ubase + ["authentication", "plaintext-password", user["password"]]),
                )

    return commands


ARGUMENT_SPEC = dict(
    users=dict(
        type="list",
        elements="dict",
        options=dict(
            name=dict(type="str", required=True),
            full_name=dict(type="str"),
            password=dict(type="str", no_log=True),
            update_password=dict(
                type="str",
                choices=["always", "on_create"],
                default="always",
            ),
            public_keys=dict(
                type="list",
                elements="dict",
                options=dict(
                    name=dict(type="str", required=True),
                    key=dict(type="str", required=True, no_log=True),
                    type=dict(
                        type="str",
                        required=True,
                        choices=[
                            "ssh-dss",
                            "ssh-rsa",
                            "ecdsa-sha2-nistp256",
                            "ecdsa-sha2-nistp384",
                            "ecdsa-sha2-nistp521",
                            "ssh-ed25519",
                        ],
                    ),
                ),
            ),
        ),
    ),
    state=dict(
        default="present",
        choices=["present", "absent", "gathered"],
    ),
)


def main():
    module = AnsibleModule(ARGUMENT_SPEC, supports_check_mode=True)
    vyos = VyOSModule(module)

    state = module.params["state"]
    users = module.params.get("users") or []

    raw_have = get_running_config(vyos)
    have = _device_to_argspec(raw_have)

    if state == "gathered":
        module.exit_json(changed=False, gathered=have)

    commands = build_commands(users, raw_have, state)

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

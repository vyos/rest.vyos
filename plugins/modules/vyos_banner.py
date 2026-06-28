#!/usr/bin/python
# -*- coding: utf-8 -*-
# GNU General Public License v3.0+

from __future__ import absolute_import, division, print_function


__metaclass__ = type

DOCUMENTATION = r"""
---
module: vyos_banner
short_description: Manage multiline banners on VyOS devices via REST API.
description:
  - Manages pre-login and post-login banners on VyOS devices using the HTTPS
    REST API.
  - Works with C(ansible_connection=ansible.netcommon.httpapi) (recommended)
    or with direct C(hostname)/C(api_key) task parameters.
  - VyOS stores banner newlines as literal C(\n) in its config; this module
    handles that conversion automatically.
version_added: "1.0.0"
author:
  - VyOS Community (@vyos)
options:
  config:
    description:
      - Banner configuration.
    type: dict
    suboptions:
      banner:
        description:
          - Which banner to configure.
        type: str
        choices:
          - pre-login
          - post-login
      text:
        description:
          - The banner text. Required when I(state=merged) or I(state=replaced).
          - Use a YAML block scalar (C(|)) for multi-line banners.
          - Real newline characters are converted to the C(\n) escape sequence
            that VyOS stores internally; this is transparent to the user.
        type: str
  state:
    description:
      - Desired state of the banner configuration.
      - C(merged) - set the banner if it differs from the current value.
      - C(replaced) - replace the banner text unconditionally.
      - C(deleted) - remove the banner. If C(config.banner) is omitted,
          both pre-login and post-login banners are removed.
      - C(gathered) - return the current banner in I(gathered) without
        making any changes. If C(config.banner) is omitted, all banners
        are returned.
    type: str
    default: merged
    choices:
      - merged
      - replaced
      - deleted
      - gathered
  hostname:
    description: Device IP or FQDN (not needed with httpapi inventory).
    type: str
  port:
    description: HTTPS port (local mode only).
    type: int
    default: 443
  api_key:
    description: REST API key (not needed when ansible_httpapi_api_key is set).
    type: str
  timeout:
    description: Request timeout in seconds.
    type: int
    default: 30
  verify_ssl:
    description: Validate the device TLS certificate.
    type: bool
    default: false
seealso:
  - module: vyos.vyos.vyos_banner
"""

EXAMPLES = r"""
- name: Set pre-login banner (merged — only changes if different)
  vyos.rest.vyos_banner:
    config:
      banner: pre-login
      text: |
        Junk pre-login banner
        over multiple lines
    state: merged

- name: Replace post-login banner unconditionally
  vyos.rest.vyos_banner:
    config:
      banner: post-login
      text: "Welcome. Authorised access only."
    state: replaced

- name: Remove pre-login banner only
  vyos.rest.vyos_banner:
    config:
      banner: pre-login
    state: deleted

- name: Remove all banners
  vyos.rest.vyos_banner:
    state: deleted

- name: Read current pre-login banner without changing it
  vyos.rest.vyos_banner:
    config:
      banner: pre-login
    state: gathered
  register: result

- name: Read all banners
  vyos.rest.vyos_banner:
    state: gathered
  register: result

- name: Print gathered banner
  ansible.builtin.debug:
    msg: "Current banner: {{ result.gathered.text }}"
"""

RETURN = r"""
before:
  description: Banner configuration before the module ran.
  returned: always
  type: dict
  sample:
    banner: pre-login
    text: "Old banner text\nline two\n"
after:
  description: Banner configuration after the module ran.
  returned: when changed
  type: dict
gathered:
  description: Current banner configuration read from the device (state=gathered).
  returned: when state is gathered
  type: dict
  sample:
    banner: pre-login
    text: "Current banner\nline two\n"
commands:
  description: Configuration commands issued.
  returned: always
  type: list
"""

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vyos.rest.plugins.module_utils.vyos_rest import (
    VYOS_REST_CONNECTION_ARGSPEC,
    VyOSRestClient,
    VyOSRestError,
)


_BANNER_PATH = {
    "pre-login": ["system", "login", "banner", "pre-login"],
    "post-login": ["system", "login", "banner", "post-login"],
}


def _encode_banner(text):
    """Convert real newlines to literal \\n for the VyOS REST API value field."""
    return text.replace("\n", "\\n")


def _decode_banner(text):
    """Convert literal \\n back to real newlines for display and comparison."""
    return text.replace("\\n", "\n")


def _get_current(client, banner_type):
    """Return current banner as a config dict, or empty dict if not set."""
    path = _BANNER_PATH[banner_type]
    try:
        result = client.retrieve_return_value(path)
        raw = result.get("data") or ""
        if raw:
            return {"banner": banner_type, "text": _decode_banner(raw)}
    except VyOSRestError:
        pass
    return {"banner": banner_type, "text": ""}


def main():
    argument_spec = dict(
        config=dict(
            type="dict",
            options=dict(
                banner=dict(
                    type="str",
                    required=False,
                    choices=["pre-login", "post-login"],
                ),
                text=dict(type="str"),
            ),
        ),
        state=dict(
            type="str",
            default="merged",
            choices=["merged", "replaced", "deleted", "gathered"],
        ),
    )
    argument_spec.update(VYOS_REST_CONNECTION_ARGSPEC)

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[
            ("state", "merged", ["config"]),
            ("state", "replaced", ["config"]),
        ],
        supports_check_mode=True,
    )

    client = VyOSRestClient(module)
    state = module.params["state"]
    config = module.params["config"] or {}
    banner_type = config.get("banner")
    desired_text = config.get("text") or ""

    # deleted without banner_type — delete all banners
    if state == "deleted" and not banner_type:
        commands = []
        changed = False
        for bt in ["pre-login", "post-login"]:
            current = _get_current(client, bt)
            if current.get("text"):
                if not module.check_mode:
                    try:
                        client.configure_delete(_BANNER_PATH[bt])
                    except VyOSRestError as exc:
                        module.fail_json(msg=str(exc))
                commands.append("delete {p}".format(p=" ".join(_BANNER_PATH[bt])))
                changed = True
        module.exit_json(changed=changed, commands=commands)

    # gathered without banner_type — return all banners
    if state == "gathered" and not banner_type:
        gathered = {}
        for bt in ["pre-login", "post-login"]:
            current = _get_current(client, bt)
            if current.get("text"):
                gathered[bt] = current
        module.exit_json(changed=False, gathered=gathered, commands=[])

    # all other states require banner_type
    if not banner_type:
        module.fail_json(
            msg="config.banner is required for state={0}".format(state),
        )

    path = _BANNER_PATH[banner_type]
    commands = []
    changed = False

    before = _get_current(client, banner_type)

    if state == "gathered":
        module.exit_json(changed=False, gathered=before, before=before, commands=[])

    if module.check_mode:
        module.exit_json(changed=True, before=before, commands=["(check mode)"])

    try:
        if state in ("merged", "replaced"):
            if before.get("text") == desired_text:
                module.exit_json(changed=False, before=before, commands=[])
            client.configure_set(path, _encode_banner(desired_text))
            commands.append("set {p} '...'".format(p=" ".join(path)))
            changed = True

        elif state == "deleted":
            if not before.get("text"):
                module.exit_json(changed=False, before=before, commands=[])
            client.configure_delete(path)
            commands.append("delete {p}".format(p=" ".join(path)))
            changed = True

    except VyOSRestError as exc:
        module.fail_json(msg=str(exc), before=before)

    after = _get_current(client, banner_type) if changed else before
    module.exit_json(changed=changed, before=before, after=after, commands=commands)


if __name__ == "__main__":
    main()

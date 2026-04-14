#!/usr/bin/python

from ansible.module_utils.basic import AnsibleModule
from ansible_collections.vyos.rest.plugins.module_utils.vyos import VyOSModule


DOCUMENTATION = r"""
---
module: vyos_banner
short_description: Manage login banners on VyOS devices using REST API
description:
  - Configure pre-login and post-login banners on VyOS devices via REST API.
  - Supports idempotent configuration using structured data.
  - Multiline banner text is supported via YAML block scalars.
  - Uses REST API (C(connection=httpapi)) instead of CLI.
  - VyOS stores multiline banners as a single string with literal C(\\n) separators.
version_added: "1.0.0"
author:
  - Your Name (@yourhandle)

options:
  config:
    description:
      - Banner configuration.
    type: dict
    required: true
    suboptions:
      banner:
        description:
          - Banner type to configure.
        type: str
        required: true
        choices:
          - pre-login
          - post-login
      text:
        description:
          - Banner text. Supports multiline strings via YAML block scalar (|).
          - Internally, real newlines are converted to literal C(\\n) as VyOS expects.
        type: str

  state:
    description:
      - Desired state of the configuration.
    type: str
    default: merged
    choices:
      - merged
      - replaced
      - overridden
      - deleted
      - gathered

notes:
  - This module requires C(ansible_connection=httpapi).
  - Banner text comparison is whitespace-normalized for idempotency.
  - VyOS stores banner text as a leaf string value with literal C(\\n) for newlines.
  - For C(merged), C(replaced), and C(overridden) states, the behaviour is identical
    for this single-leaf resource — the banner value is set to the desired text.
"""

EXAMPLES = r"""
- name: Configure single-line pre-login banner
  vyos.rest.vyos_banner:
    config:
      banner: pre-login
      text: "Unauthorized access is prohibited"
    state: merged

- name: Configure multiline post-login banner
  vyos.rest.vyos_banner:
    config:
      banner: post-login
      text: |
        Welcome to VyOS
        Authorized users only
        Disconnect if you are not authorized
    state: merged

- name: Replace post-login banner
  vyos.rest.vyos_banner:
    config:
      banner: post-login
      text: "Welcome to VyOS"
    state: replaced

- name: Remove pre-login banner
  vyos.rest.vyos_banner:
    config:
      banner: pre-login
    state: deleted

- name: Gather banner configuration
  vyos.rest.vyos_banner:
    config:
      banner: pre-login
    state: gathered
"""

RETURN = r"""
before:
  description: Configuration before changes (text uses real newlines).
  returned: always
  type: dict
  sample:
    banner: pre-login
    text: "Old banner text"

after:
  description: Configuration after changes (text uses real newlines).
  returned: when changed
  type: dict
  sample:
    banner: pre-login
    text: "New banner text"

commands:
  description: List of API command dicts sent to the device.
  returned: when changes are required
  type: list
  sample:
    - op: set
      path: ["system", "login", "banner", "pre-login"]
      value: "New banner text"

gathered:
  description: Current device configuration (text uses real newlines).
  returned: when state is gathered
  type: dict
  sample:
    banner: pre-login
    text: "Current banner text"

response:
  description: Raw response from VyOS REST API.
  returned: when changes are applied
  type: dict

saved:
  description: Result of save_config call after applying changes.
  returned: when changes are applied
  type: dict
"""


# ------------------------------------------------------------
# Text conversion helpers
#
# Internal canonical form: real Python newlines (\n), stripped.
#
# VyOS wire format: literal backslash-n (\\n) sequences within
# a single quoted string, e.g. 'line one\nline two\nline three'.
#
# Rule: convert FROM wire format on read, TO wire format on write,
#       always compare in canonical (internal) form.
# ------------------------------------------------------------


def normalize_text(text):
    """
    Normalize text to canonical internal form.

    - Converts to str if needed
    - Strips each line
    - Removes leading/trailing blank lines
    - Joins with real newlines
    - Returns None if result is empty
    """
    if text is None:
        return None
    lines = [line.strip() for line in text.strip().splitlines()]
    # Trim leading blank lines
    while lines and not lines[0]:
        lines.pop(0)
    # Trim trailing blank lines
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines) if lines else None


def text_from_api_value(raw):
    """
    Convert VyOS API/device value to canonical internal form.

    VyOS returns multiline banners with literal \\n sequences:
      'line one\\nline two\\nline three'

    Convert those to real newlines first, then normalize.
    """
    if raw is None:
        return None
    return normalize_text(raw.replace("\\n", "\n"))


def text_to_api_value(text):
    """
    Convert canonical internal form to VyOS wire format.

    Real newlines become literal \\n sequences as VyOS expects.
    Returns None if input normalizes to None.
    """
    normalized = normalize_text(text)
    if normalized is None:
        return None
    return normalized.replace("\n", "\\n")


# ------------------------------------------------------------
# Device interaction
# ------------------------------------------------------------


def get_running_config(vyos, banner):
    """
    Fetch current banner configuration from the device.

    The VyOS showConfig API returns banner text as a plain string value:
      {"pre-login": "test1"}
      {"post-login": "line one\\nline two\\nline three"}

    Returns:
      {"banner": <str>, "text": <normalized str or None>}
    """
    try:
        raw = vyos.get_config(["system", "login", "banner"])
    except Exception as e:
        if "Configuration under specified path is empty" in str(e):
            return {"banner": banner, "text": None}
        raise

    if not raw or not isinstance(raw, dict):
        return {"banner": banner, "text": None}

    val = raw.get(banner)

    if val is None:
        return {"banner": banner, "text": None}

    if isinstance(val, str):
        # Convert from wire format (literal \n) to internal form (real newlines)
        return {"banner": banner, "text": text_from_api_value(val)}

    # Unexpected type — surface clearly rather than silently swallowing
    raise ValueError(
        "Unexpected banner value type '{t}' returned by API (value={v!r}). "
        "Expected a plain string. Please file a bug.".format(
            t=type(val).__name__,
            v=val,
        ),
    )


def build_commands(want, have, state):
    """
    Build list of VyOS REST API command dicts.

    VyOS banner API payload structure:
      SET:    {"op": "set",    "path": ["system","login","banner","<type>"], "value": "<text>"}
      DELETE: {"op": "delete", "path": ["system","login","banner","<type>"]}

    The banner text is always a leaf VALUE on the path, never a path segment.

    All text comparison is done in canonical internal form (real newlines).
    Conversion to wire format (literal \\n) happens only when building the
    final API command value.
    """
    banner = want["banner"]

    # Canonical internal form for comparison
    want_text = normalize_text(want.get("text"))
    have_text = have.get("text")  # already in canonical form from get_running_config

    base_path = ["system", "login", "banner", banner]
    banner_exists = have_text is not None

    # --------------------------------------------------------
    # deleted: remove the banner node if it exists
    # --------------------------------------------------------
    if state == "deleted":
        if banner_exists:
            return [{"op": "delete", "path": base_path}]
        return []

    # --------------------------------------------------------
    # merged / replaced / overridden
    #
    # For this single leaf-value resource all three states are
    # semantically equivalent: ensure the desired value is set.
    # Idempotency: skip if the normalized value already matches.
    # --------------------------------------------------------
    if state in ("merged", "replaced", "overridden"):
        if want_text is None:
            # No text provided with a non-delete state — nothing to do
            return []

        if want_text == have_text:
            # Already correct — idempotent, no change needed
            return []

        # Convert to wire format only at the point of building the payload
        return [
            {
                "op": "set",
                "path": base_path,
                "value": text_to_api_value(want_text),
            },
        ]

    return []


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------


def main():

    argument_spec = dict(
        config=dict(
            type="dict",
            required=True,
            options=dict(
                banner=dict(
                    type="str",
                    required=True,
                    choices=["pre-login", "post-login"],
                ),
                text=dict(type="str"),
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

    module = AnsibleModule(
        argument_spec=argument_spec,
        supports_check_mode=True,
    )

    vyos = VyOSModule(module)

    state = module.params["state"]
    config = module.params.get("config") or {}
    banner = config.get("banner")

    if not banner:
        module.fail_json(msg="banner is required in config")

    # Fetch current device state (text in canonical internal form)
    have = get_running_config(vyos, banner)

    # --------------------------------------------------------
    # gathered: return current state, no changes
    # --------------------------------------------------------
    if state == "gathered":
        module.exit_json(changed=False, gathered=have)

    want = {
        "banner": banner,
        "text": config.get("text"),
    }

    commands = build_commands(want, have, state)

    # --------------------------------------------------------
    # check mode: report what would change, make no API calls
    # --------------------------------------------------------
    if module.check_mode:
        module.exit_json(
            changed=bool(commands),
            commands=commands,
            before=have,
        )

    # --------------------------------------------------------
    # apply changes
    # --------------------------------------------------------
    if commands:
        response = vyos.apply_commands(commands)
        saved = vyos.save_config()

        module.exit_json(
            changed=True,
            before=have,
            # Report after-state in canonical form (real newlines, human-readable)
            after=want,
            # after={
            #     "banner": banner,
            #     "text": normalize_text(want["text"]),
            # },
            commands=commands,
            saved=saved,
            response=response,
        )

    # --------------------------------------------------------
    # no changes needed
    # --------------------------------------------------------
    module.exit_json(
        changed=False,
        before=have,
        after=have,
    )


if __name__ == "__main__":
    main()

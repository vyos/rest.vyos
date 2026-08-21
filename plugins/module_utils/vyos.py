"""
VyOSModule — high-level wrapper used by vyos.rest resource modules.

Provides ``get_config()``, ``apply_commands()``, and ``save_config()``
on top of ``VyOSRestClient``, so resource modules can work with simple
``("set", path)`` / ``("delete", path)`` command tuples rather than
calling the REST client directly.
"""

from __future__ import absolute_import, division, print_function


__metaclass__ = type

from ansible_collections.vyos.rest.plugins.module_utils.vyos_rest import (
    VyOSRestClient,
    VyOSRestError,
)


# ---------------------------------------------------------------------------
# Legacy dynamic config utilities (used by Wave 1-3 modules)
# ---------------------------------------------------------------------------


def _kebab_to_snake(s):
    """Convert kebab-case string to snake_case."""
    return s.replace("-", "_")


def _snake_to_kebab(s):
    """Convert snake_case string to kebab-case."""
    return s.replace("_", "-")


def normalize(raw):
    """Recursively normalize an API response dict to snake_case keys."""
    if isinstance(raw, dict):
        return {_kebab_to_snake(k): normalize(v) for k, v in raw.items()}
    if isinstance(raw, list):
        return [normalize(v) for v in raw]
    return raw


def denormalize_path(path):
    """Convert a snake_case path list to kebab-case for the API."""
    return [_snake_to_kebab(p) for p in path]


def _diff_value(want_val, have_val, path, cmds, delete_missing):
    if isinstance(want_val, dict):
        if not want_val:
            if have_val is None:
                cmds.append(("set", denormalize_path(path)))
        else:
            have_dict = have_val if isinstance(have_val, dict) else {}
            _diff_dict(want_val, have_dict, path, cmds, delete_missing)
    elif isinstance(want_val, list):
        have_set = set(have_val) if isinstance(have_val, list) else set()
        for item in want_val:
            if item not in have_set:
                cmds.append(("set", denormalize_path(path + [str(item)])))
        if delete_missing:
            want_set = set(str(i) for i in want_val)
            for item in have_val or []:
                if str(item) not in want_set:
                    cmds.append(("delete", denormalize_path(path + [str(item)])))
    else:
        if want_val != have_val:
            cmds.append(("set", denormalize_path(path + [str(want_val)])))


def _diff_dict(want, have, path, cmds, delete_missing):
    for key, want_val in want.items():
        _diff_value(want_val, have.get(key), path + [key], cmds, delete_missing)
    if delete_missing:
        for key in have:
            if key not in want:
                cmds.append(("delete", denormalize_path(path + [key])))


def diff_configs(want, have, base_path, delete_missing=False):
    """Diff two normalized config dicts and return API command tuples.

    Args:
        want (dict): Desired configuration (snake_case keys).
        have (dict): Current configuration (snake_case keys).
        base_path (list): Base API path for commands.
        delete_missing (bool): Generate delete commands for keys in
            ``have`` absent from ``want``.

    Returns:
        list: Tuples of ``("set", path)`` or ``("delete", path)``.
    """
    cmds = []
    _diff_dict(want, have, base_path, cmds, delete_missing)
    return cmds


# ---------------------------------------------------------------------------
# Generic dict diff engine (used by Wave 4+ modules)
#
# Design principles:
#   - want uses snake_case (from YAML/argspec)
#   - have uses kebab-case (from device API)
#   - Conversion between - and _ happens here, once, in the core
#   - Modules only need _BASE path — no key mapping anywhere
#   - want is the reference dataset — drives all operations
# ---------------------------------------------------------------------------


def owned_config(have, argspec):
    """Filter raw device config to only keys owned by this module.

    Ownership is declared by the module's argspec — the single source
    of truth for what this module manages. Keys in have not present in
    argspec (after normalization) are excluded from before/after output.

    Args:
        have (dict): Raw device config (kebab-case keys).
        argspec (dict): Module argument_spec dict.

    Returns:
        dict: Filtered have with only module-owned keys.
    """
    owned = set(argspec.keys()) - {"state"}
    return {k: v for k, v in have.items() if k.replace("-", "_") in owned}


# ---------------------------------------------------------------------------
# Generic, field-name-agnostic helpers shared by every dict_op-based module.
#
# Key-case translation (snake_case <-> kebab-case) is dict_op's own job on
# the want/have side fed to it directly; these helpers only handle what
# dict_op *can't* infer on its own: Python bool <-> device presence-node,
# tag-node string/list collapse, argspec-driven type casting for the
# public have/gathered output, and keeping one module's dict_op calls from
# reaching into a subtree owned by another module sharing the same root.
# ---------------------------------------------------------------------------


def autoclean(d):
    """want-side cleanup: drop None/False, True -> presence node ({}),
    recurse into dicts. Keys are left exactly as given -- dict_op does
    the snake_case/kebab-case translation itself when it builds paths.
    """
    if not isinstance(d, dict):
        return d
    result = {}
    for k, v in d.items():
        if v is None or v is False:
            continue
        if v is True:
            result[k] = {}
        elif isinstance(v, dict):
            cleaned = autoclean(v)
            if cleaned:
                result[k] = cleaned
        else:
            result[k] = v
    return result


def from_device(d):
    """have-side inverse of autoclean, for building the public argspec
    output: kebab-case -> snake_case keys, presence node -> True, recurse.
    """
    if not isinstance(d, dict):
        return d
    result = {}
    for k, v in d.items():
        snake_k = k.replace("-", "_")
        if isinstance(v, dict):
            result[snake_k] = True if not v else from_device(v)
        else:
            result[snake_k] = v
    return result


def to_tag_dict(value):
    """Coerce a VyOS tag-node value (bare str/list, or already a dict)
    to the {key: {}} shape dict_op always expects for a dict-typed key.
    """
    if not value:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        return {value: {}}
    if isinstance(value, list):
        return {str(v): {} for v in value}
    return {}


def normalize_have(raw, tag_keys=()):
    """Coerce the given tag-node keys' subtrees so dict_op only ever sees
    dicts for them -- VyOS's REST API collapses a single-child tag node to
    a plain string (or a list for multiple), the same class of quirk
    dict_op itself already corrects for ordinary list leaves. Every other
    key is already a plain scalar/dict leaf and passes through untouched.
    """
    if not raw or not isinstance(raw, dict):
        return {}
    result = {}
    for k, v in raw.items():
        if isinstance(v, dict):
            result[k] = normalize_have(v, tag_keys)
        elif isinstance(v, (list, str)) and v:
            result[k] = to_tag_dict(v) if k in tag_keys else v
        else:
            result[k] = v
    return result


def cast_by_spec(entry, options):
    """Cast have-side string leaves to their ARGUMENT_SPEC-declared type.

    Entirely argspec-driven -- no per-field name knowledge. This is what
    lets from_device() stay purely structural (kebab->snake only) while
    the public have/gathered output still reports ints as ints, without
    a hand-maintained list of "which leaves happen to be numeric".
    Handles list-of-dicts (elements="dict") and scalar-element lists
    (elements="int"/etc, including VyOS's single-value collapse) alike.
    """
    if not isinstance(entry, dict):
        return entry
    for key, spec in (options or {}).items():
        if key not in entry or entry[key] is None:
            continue
        spec_type = spec.get("type")
        if spec_type == "int":
            entry[key] = int(entry[key])
        elif spec_type == "dict":
            cast_by_spec(entry[key], spec.get("options"))
        elif spec_type == "list":
            val = entry[key]
            if not isinstance(val, list):
                val = [val]
            elements = spec.get("elements")
            if elements == "dict":
                for item in val:
                    cast_by_spec(item, spec.get("options"))
            elif elements == "int":
                val = [int(v) for v in val]
            entry[key] = val
    return entry


def scope_to_spec(have, options, exclude=()):
    """Filter have's keys down to ones a module's own argspec actually
    declares (in kebab-case form), so dict_op purge/set calls never touch
    a subtree owned by a different module sharing the same device-tree
    root (e.g. a neighbor's nested address-family, owned by a sibling
    *_address_family module, is invisible to a module whose argspec never
    declared it) -- this protects against any such foreign subtree, present
    or future, without hardcoding its name.
    """
    if not isinstance(have, dict):
        return {}
    owned = {k.replace("_", "-") for k in (options or {}) if k not in exclude}
    return {k: v for k, v in have.items() if k in owned}


def dict_op(want, have, base_path, op="set"):
    """Generic dict diff engine for VyOS REST API.

    Compares want (snake_case, from YAML) against have (kebab-case, from
    device) and generates API command tuples. All key normalization between
    snake_case and kebab-case happens here — modules never need to convert.

    Set operations on the two datasets:
        op="set"    want - have       present: apply what is missing
        op="delete" want ∩ have       absent:  remove what exists
        op="purge"  have - want       replaced: remove what is extra

    Args:
        want (dict): Desired config, snake_case keys (from YAML/argspec).
        have (dict): Current config, kebab-case keys (raw from device API).
        base_path (list): Base API path — the only module-specific knowledge.
        op (str): "set", "delete", or "purge".

    Returns:
        list: Tuples of ("set", path) or ("delete", path).
    """
    cmds = []

    # Index have by normalized key for O(1) lookup.
    # Preserves original kebab-case key for use in API paths.
    have_idx = {k.replace("-", "_"): (k, v) for k, v in (have or {}).items()}

    if op == "purge":
        # have - want: delete have keys not present in want
        # Scoped naturally by _BASE — only this subtree is in have
        want_keys = {k.replace("-", "_") for k in (want or {})}
        for norm_k, (orig_k, have_v) in have_idx.items():
            if norm_k not in want_keys:
                cmds.append(("delete", base_path + [orig_k]))
            elif isinstance(have_v, dict):
                want_nested = (want or {}).get(norm_k) or (want or {}).get(orig_k) or {}
                if isinstance(want_nested, dict):
                    cmds += dict_op(want_nested, have_v, base_path + [orig_k], op="purge")
            elif isinstance(have_v, (list, str)):
                # List-valued leaf (e.g. a multi-value leafNode): purge
                # extra have-only items not present in want's list, the
                # same way op="set"/"delete" already diff list values.
                # Device may return a single value as a string instead
                # of a list -- same quirk correction as the list branch
                # below.
                want_nested = (want or {}).get(norm_k, (want or {}).get(orig_k))
                if isinstance(want_nested, list):
                    have_list = [have_v] if isinstance(have_v, str) else have_v
                    want_set = {str(i) for i in want_nested}
                    for item in have_list:
                        if str(item) not in want_set:
                            cmds.append(("delete", base_path + [orig_k, str(item)]))
        return cmds

    for key, want_val in (want or {}).items():
        if want_val is None:
            continue

        # Normalize want key for lookup, get original device key for path
        norm_key = key.replace("-", "_")
        orig_key, have_val = have_idx.get(norm_key, (key.replace("_", "-"), None))
        path = base_path + [orig_key]

        if isinstance(want_val, dict):
            if not want_val:
                # Presence node
                if op == "set" and have_val is None:
                    cmds.append(("set", path))
                elif op == "delete" and have_val is not None:
                    cmds.append(("delete", path))
            else:
                # Recurse — have_val passed raw, conversion happens recursively
                cmds += dict_op(want_val, have_val or {}, path, op)

        elif isinstance(want_val, list):
            # Device may return a single value as a string instead of a list
            if isinstance(have_val, str):
                have_val = [have_val]
            have_set = set(str(i) for i in (have_val or []))
            if op == "set":
                # want - have: add missing items
                for item in want_val:
                    if str(item) not in have_set:
                        cmds.append(("set", path + [str(item)]))
            elif op == "delete":
                # want ∩ have: remove items that exist
                for item in want_val:
                    if str(item) in have_set:
                        cmds.append(("delete", path + [str(item)]))

        else:
            # Scalar leaf
            have_str = str(have_val) if have_val is not None else ""
            if op == "set" and str(want_val) != have_str:
                cmds.append(("set", path + [str(want_val)]))
            elif op == "delete" and have_val is not None:
                cmds.append(("delete", path))

    return cmds


class VyOSModule:
    """Thin wrapper around VyOSRestClient for resource modules."""

    def __init__(self, module):
        self._module = module
        self._client = VyOSRestClient(module)

    def get_config(self, path=None):
        """Retrieve the configuration subtree at *path*.

        Returns raw device dict with kebab-case keys.
        """
        try:
            result = self._client.retrieve_show_config(path or [])
            return result.get("data") or {}
        except VyOSRestError:
            return {}

    def apply_commands(self, commands):
        if not commands:
            return []
        payload = []
        for cmd in commands:
            if isinstance(cmd, dict):
                op, path = cmd["op"], list(cmd["path"])
            else:
                op, path = cmd[0], list(cmd[1])
            payload.append({"op": op, "path": path})
        try:
            return self._client.configure_batch(payload)
        except VyOSRestError as exc:
            self._module.fail_json(
                msg="apply_commands failed: {e}".format(e=str(exc)),
            )

    def _apply_set(self, path, value=None):
        """Set a config path, retrying with a shortened path on failure."""
        try:
            self._client.configure_set(path, value)
            return {"op": "set", "path": path, "status": "ok"}
        except VyOSRestError as exc:
            if len(path) >= 3:
                short_path = path[:-2] + [path[-1]]
                try:
                    self._client.configure_set(short_path, value)
                    return {"op": "set", "path": short_path, "status": "ok-adapted"}
                except VyOSRestError:
                    pass
            raise VyOSRestError(
                "set {p} failed: {e}".format(p=" ".join(path), e=str(exc)),
            )

    def _apply_delete(self, path):
        """Delete a config path; silently ignore if already absent."""
        try:
            self._client.configure_delete(path)
            return {"op": "delete", "path": path, "status": "ok"}
        except VyOSRestError:
            return {"op": "delete", "path": path, "status": "noop"}

    def show(self, path):
        """Run an operational show command via the /show endpoint.

        Raises VyOSRestError on failure; callers that need per-command
        error reporting (e.g. vyos_command) rely on this propagating
        rather than being indistinguishable from a valid empty response.
        """
        result = self._client.show(path)
        return result.get("data") or ""

    def save_config(self, file_path=None):
        """Save the running configuration to disk."""
        try:
            self._client.config_file_save(file_path)
            return True
        except VyOSRestError:
            return False

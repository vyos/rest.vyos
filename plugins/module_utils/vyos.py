"""
VyOSModule — high-level wrapper used by vyos.rest resource modules.

Provides ``get_config()``, ``apply_commands()``, and ``save_config()``
on top of ``VyOSRestClient``, so resource modules can work with simple
``("set", path)`` / ``("delete", path)`` command tuples rather than
calling the REST client directly.

Version-adaptive paths
----------------------
Some VyOS config paths changed between minor versions (e.g. the NTP
``allow-client address`` node was removed in 1.5+).  ``apply_commands``
handles this transparently: if a ``set`` command is rejected by the device
it retries with the last path segment removed (one level up), covering
the most common schema simplifications.  A ``delete`` that fails is
treated as a no-op (already absent).
"""

from __future__ import absolute_import, division, print_function


__metaclass__ = type

from ansible_collections.vyos.rest.plugins.module_utils.vyos_rest import (
    VyOSRestClient,
    VyOSRestError,
)


class VyOSModule:
    """Thin wrapper around VyOSRestClient for resource modules.

    Args:
        module: AnsibleModule instance.
    """

    def __init__(self, module):
        self._module = module
        self._client = VyOSRestClient(module)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def get_config(self, path=None):
        """Retrieve the configuration subtree at *path*.

        Args:
            path (list, optional): Config path tokens. ``[]`` or ``None``
                returns the entire running configuration.

        Returns:
            dict: Configuration subtree, or ``{}`` if the path doesn't exist.
        """
        try:
            result = self._client.retrieve_show_config(path or [])
            return result.get("data") or {}
        except VyOSRestError:
            return {}

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    def apply_commands(self, commands):
        """Execute a list of ``(op, path)`` command tuples against the device.

        Args:
            commands (list): Each item is a 2-tuple ``(op, path)`` where:
                - *op* is ``"set"`` or ``"delete"``
                - *path* is a list of config path tokens

                Optionally a 3-tuple ``(op, path, value)`` for leaf nodes
                that carry a value.

        Returns:
            list: Results from each command (dicts with ``op`` and ``path``).

        Raises:
            VyOSRestError: If a command fails and cannot be recovered.

        Notes:
            **Version-adaptive set:** if a ``set`` is rejected by the device,
            the method retries once with the last path segment removed.
            This handles schema simplifications between VyOS releases
            (e.g. ``allow-client address <prefix>`` -> ``allow-client <prefix>``
            in VyOS 1.5+).

            **Idempotent delete:** ``delete`` failures are silently ignored
            (the path is already absent).
        """
        results = []

        for cmd in commands:
            # Support two command formats:
            # Tuple: ("set", ["path", "tokens"])  or  ("set", ["path"], "value")
            # Dict:  {"op": "set", "path": ["path", "tokens"]}
            if isinstance(cmd, dict):
                op = cmd["op"]
                path = list(cmd["path"])
                value = cmd.get("value")
            else:
                op = cmd[0]
                path = list(cmd[1])
                value = cmd[2] if len(cmd) > 2 else None

            if op == "set":
                results.append(self._apply_set(path, value))
            elif op == "delete":
                results.append(self._apply_delete(path))
            else:
                self._module.fail_json(
                    msg="Unknown command op '{op}' in apply_commands".format(op=op),
                )

        return results

    def _apply_set(self, path, value=None):
        """Set a config path, retrying with a shortened path on failure."""
        try:
            self._client.configure_set(path, value)
            return {"op": "set", "path": path, "status": "ok"}
        except VyOSRestError as exc:
            # Retry without the second-to-last segment (version-adaptive).
            # Example: ["service","ntp","allow-client","address","10.0.0.0/24"]
            #       -> ["service","ntp","allow-client","10.0.0.0/24"]
            # Only attempt if path is long enough to have an intermediate node.
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

    # ------------------------------------------------------------------
    # Persist
    # ------------------------------------------------------------------

    def save_config(self, file_path=None):
        """Save the running configuration to disk.

        Args:
            file_path (str, optional): Destination path on the device.
                Defaults to ``/config/config.boot``.

        Returns:
            bool: ``True`` if saved successfully, ``False`` otherwise.
        """
        try:
            self._client.config_file_save(file_path)
            return True
        except VyOSRestError:
            return False

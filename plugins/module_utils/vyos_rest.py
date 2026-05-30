"""
VyOS REST API client utility — supports both connection modes.
"""

from __future__ import absolute_import, division, print_function


__metaclass__ = type

import json
import os


try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

try:
    import urllib3

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except ImportError:
    pass

from ansible.module_utils._text import to_text
from ansible.module_utils.basic import env_fallback
from ansible.module_utils.connection import Connection, ConnectionError
from ansible.module_utils.urls import open_url


class VyOSRestError(Exception):
    """Raised when the VyOS REST API returns an error or is unreachable."""

    pass


class VyOSRestClient:
    """Unified VyOS REST API client.

    Automatically selects transport:
    * **httpapi** when module._socket_path is set (ansible_connection=httpapi).
    * **local HTTP** falls back to direct open_url calls otherwise.
    """

    def __init__(self, module):
        self.module = module
        socket_path = getattr(module, "_socket_path", None) or os.environ.get("ANSIBLE_SOCKET")
        if socket_path and os.path.exists(socket_path):
            self._mode = "httpapi"
            self._conn = Connection(socket_path)
        else:
            self._mode = "local"
            self._init_local()

    def _init_local(self):
        p = self.module.params
        host = p.get("hostname") or ""
        if not host:
            self.module.fail_json(
                msg=(
                    "No device address available. Either:\n"
                    "  * Set ansible_connection=ansible.netcommon.httpapi with "
                    "ansible_network_os=vyos.rest.vyos in inventory (recommended), or\n"
                    "  * Set the 'hostname' task parameter, or\n"
                    "  * Export VYOS_HOST=<address>"
                ),
            )
        self.hostname = host
        self.port = p.get("port") or 443
        self.api_key = p.get("api_key") or ""
        self.timeout = p.get("timeout") or 30
        self.verify_ssl = bool(p.get("verify_ssl"))
        self.base_url = "https://{host}:{port}".format(host=self.hostname, port=self.port)

    def _post(self, endpoint, payload):
        if self._mode == "httpapi":
            return self._post_httpapi(endpoint, payload)
        return self._post_local(endpoint, payload)

    def _post_httpapi(self, endpoint, payload):
        try:
            result = self._conn.send_request(endpoint=endpoint, **payload)
            return result
        except ConnectionError as exc:
            raise VyOSRestError(str(exc))
        except Exception as exc:
            raise VyOSRestError(
                "httpapi send_request to {ep} failed: {e}".format(ep=endpoint, e=str(exc)),
            )

    def _post_local(self, endpoint, payload):
        url = "{base}{ep}".format(base=self.base_url, ep=endpoint)
        body = json.dumps(payload)
        form = urlencode({"data": body, "key": self.api_key})
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        try:
            response = open_url(
                url,
                data=form,
                headers=headers,
                method="POST",
                timeout=self.timeout,
                validate_certs=self.verify_ssl,
            )
            raw = to_text(response.read())
        except Exception as exc:
            raise VyOSRestError("HTTP POST to {url} failed: {e}".format(url=url, e=str(exc)))
        try:
            result = json.loads(raw)
        except ValueError:
            raise VyOSRestError("Invalid JSON from {url}: {raw}".format(url=url, raw=raw))
        if not result.get("success"):
            raise VyOSRestError(
                "VyOS API error at {url}: {err}".format(
                    url=url,
                    err=result.get("error", "unknown"),
                ),
            )
        return result

    def _get(self, endpoint, params=None):
        if self._mode == "httpapi":
            try:
                return self._conn.get_info()
            except Exception as exc:
                raise VyOSRestError("httpapi get_info failed: {e}".format(e=str(exc)))
        url = "{base}{ep}".format(base=self.base_url, ep=endpoint)
        if params:
            qs = "&".join("{k}={v}".format(k=k, v=v) for k, v in params.items())
            url = "{url}?{qs}".format(url=url, qs=qs)
        try:
            response = open_url(
                url,
                method="GET",
                timeout=self.timeout,
                validate_certs=self.verify_ssl,
            )
            return json.loads(to_text(response.read()))
        except Exception as exc:
            raise VyOSRestError("HTTP GET to {url} failed: {e}".format(url=url, e=str(exc)))

    # High-level helpers — identical interface regardless of transport
    def configure_set(self, path, value=None):
        payload = {"op": "set", "path": path}
        if value is not None:
            payload["value"] = value
        return self._post("/configure", payload)

    def configure_delete(self, path):
        return self._post("/configure", {"op": "delete", "path": path})

    def configure_comment(self, path, comment):
        return self._post("/configure", {"op": "comment", "path": path, "value": comment})

    def retrieve_show_config(self, path=None):
        return self._post("/retrieve", {"op": "showConfig", "path": path or []})

    def retrieve_return_values(self, path):
        return self._post("/retrieve", {"op": "returnValues", "path": path})

    def retrieve_return_value(self, path):
        return self._post("/retrieve", {"op": "returnValue", "path": path})

    def retrieve_exists(self, path):
        result = self._post("/retrieve", {"op": "exists", "path": path})
        return bool(result.get("data"))

    def show(self, path):
        return self._post("/show", {"op": "show", "path": path})

    def generate(self, path):
        return self._post("/generate", {"op": "generate", "path": path})

    def reset(self, path):
        return self._post("/reset", {"op": "reset", "path": path})

    def reboot(self, at="now"):
        return self._post("/reboot", {"op": "reboot", "path": [at]})

    def poweroff(self, at="now"):
        return self._post("/poweroff", {"op": "poweroff", "path": [at]})

    def image_add(self, url):
        return self._post("/image", {"op": "add", "url": url})

    def image_delete(self, name):
        return self._post("/image", {"op": "delete", "name": name})

    def configure_batch(self, commands):
        """Send all commands as a single atomic commit."""
        if self._mode == "httpapi":
            try:
                return self._conn.send_request(
                    endpoint="/configure",
                    _raw_list=commands,
                )
            except ConnectionError as exc:
                raise VyOSRestError(str(exc))
            except Exception as exc:
                raise VyOSRestError(
                    "configure_batch failed: {e}".format(e=str(exc)),
                )

    def config_file_save(self, path=None):
        payload = {"op": "save"}
        if path:
            payload["file"] = path
        return self._post("/config-file", payload)

    def config_file_load(self, path):
        return self._post("/config-file", {"op": "load", "file": path})

    def info(self, version=None, hostname=None):
        params = {}
        if version is not None:
            params["version"] = str(version).lower()
        if hostname is not None:
            params["hostname"] = str(hostname).lower()
        return self._get("/info", params or None)


# Shared argument spec — only used in local mode; ignored when httpapi is active
VYOS_REST_CONNECTION_ARGSPEC = dict(
    hostname=dict(
        type="str",
        required=False,
        default=None,
        fallback=(env_fallback, ["VYOS_HOST"]),
    ),
    port=dict(
        type="int",
        default=443,
        fallback=(env_fallback, ["VYOS_PORT"]),
    ),
    api_key=dict(
        type="str",
        required=False,
        default=None,
        no_log=True,
        fallback=(env_fallback, ["VYOS_API_KEY"]),
    ),
    timeout=dict(type="int", default=30),
    verify_ssl=dict(
        type="bool",
        default=False,
        fallback=(env_fallback, ["VYOS_VERIFY_SSL"]),
    ),
)

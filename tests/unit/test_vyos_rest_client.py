"""Unit tests for vyos_rest module_utils."""

import json

from unittest.mock import MagicMock, patch

import pytest


# Minimal AnsibleModule mock
class FakeModule:
    def __init__(self, params):
        self.params = params

    def fail_json(self, **kwargs):
        raise AssertionError("fail_json called: {0}".format(kwargs))


def _make_client(params=None):
    from ansible_collections.vyos.rest.plugins.module_utils.vyos_rest import (
        VyOSRestClient,
    )

    p = {
        "hostname": "192.0.2.1",
        "port": 443,
        "api_key": "test-key",
        "timeout": 10,
        "verify_ssl": False,
    }
    if params:
        p.update(params)
    return VyOSRestClient(FakeModule(p))


def _ok_response(data):
    raw = json.dumps({"success": True, "data": data, "error": None})
    mock_resp = MagicMock()
    mock_resp.read.return_value = raw.encode()
    return mock_resp


class TestVyOSRestClientInit:
    def test_base_url(self):
        client = _make_client()
        assert client.base_url == "https://192.0.2.1:443"

    def test_custom_port(self):
        client = _make_client({"port": 8443})
        assert client.base_url == "https://192.0.2.1:8443"


class TestConfigureSet:
    def test_set_path_only(self):
        client = _make_client()
        with patch(
            "ansible_collections.vyos.rest.plugins.module_utils.vyos_rest.open_url",
            return_value=_ok_response(None),
        ) as mock_open:
            client.configure_set(["interfaces", "ethernet", "eth0"])
            call_args = mock_open.call_args
            data_field = call_args[1]["data"] if "data" in call_args[1] else call_args[0][1]
            assert '"op": "set"' in data_field
            assert '"interfaces"' in data_field

    def test_set_path_with_value(self):
        client = _make_client()
        with patch(
            "ansible_collections.vyos.rest.plugins.module_utils.vyos_rest.open_url",
            return_value=_ok_response(None),
        ) as mock_open:
            client.configure_set(["system", "host-name"], "vyos")
            call_args = mock_open.call_args
            data_field = call_args[1]["data"] if "data" in call_args[1] else call_args[0][1]
            assert '"value": "vyos"' in data_field


class TestConfigureDelete:
    def test_delete(self):
        client = _make_client()
        with patch(
            "ansible_collections.vyos.rest.plugins.module_utils.vyos_rest.open_url",
            return_value=_ok_response(None),
        ) as mock_open:
            client.configure_delete(["protocols", "static", "route"])
            call_args = mock_open.call_args
            data_field = call_args[1]["data"] if "data" in call_args[1] else call_args[0][1]
            assert '"op": "delete"' in data_field


class TestRetrieve:
    def test_show_config(self):
        client = _make_client()
        expected = {"interfaces": {"ethernet": {"eth0": {"address": "dhcp"}}}}
        with patch(
            "ansible_collections.vyos.rest.plugins.module_utils.vyos_rest.open_url",
            return_value=_ok_response(expected),
        ):
            result = client.retrieve_show_config([])
            assert result["data"] == expected

    def test_exists_true(self):
        client = _make_client()
        with patch(
            "ansible_collections.vyos.rest.plugins.module_utils.vyos_rest.open_url",
            return_value=_ok_response(True),
        ):
            assert client.retrieve_exists(["service", "ntp"]) is True

    def test_exists_false(self):
        client = _make_client()
        with patch(
            "ansible_collections.vyos.rest.plugins.module_utils.vyos_rest.open_url",
            return_value=_ok_response(False),
        ):
            assert client.retrieve_exists(["service", "nonexistent"]) is False


class TestErrorHandling:
    def test_api_failure_raises(self):
        from ansible_collections.vyos.rest.plugins.module_utils.vyos_rest import (
            VyOSRestError,
        )

        client = _make_client()
        err_response = MagicMock()
        err_response.read.return_value = json.dumps(
            {"success": False, "data": None, "error": "path not found"},
        ).encode()
        with patch(
            "ansible_collections.vyos.rest.plugins.module_utils.vyos_rest.open_url",
            return_value=err_response,
        ):
            with pytest.raises(VyOSRestError, match="path not found"):
                client.configure_set(["bad", "path"])

    def test_invalid_json_raises(self):
        from ansible_collections.vyos.rest.plugins.module_utils.vyos_rest import (
            VyOSRestError,
        )

        client = _make_client()
        bad_response = MagicMock()
        bad_response.read.return_value = b"not json"
        with patch(
            "ansible_collections.vyos.rest.plugins.module_utils.vyos_rest.open_url",
            return_value=bad_response,
        ):
            with pytest.raises(VyOSRestError, match="Invalid JSON"):
                client.retrieve_show_config([])

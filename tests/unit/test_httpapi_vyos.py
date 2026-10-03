# -*- coding: utf-8 -*-
"""Unit tests for plugins/httpapi/vyos.py

Tests cover all three auth methods (key, header, bearer) and token
caching behaviour. The Ansible connection layer is mocked so no
real device is needed.
"""
from __future__ import absolute_import, division, print_function


__metaclass__ = type

import json
import time
import unittest

from io import BytesIO
from unittest.mock import MagicMock, patch

from ansible.errors import AnsibleConnectionFailure
from ansible.module_utils.connection import ConnectionError
from ansible_collections.vyos.rest.plugins.httpapi.vyos import HttpApi


def _make_response(payload, status=200):
    """Return a (response, BytesIO) pair like connection.send() does."""
    resp = MagicMock()
    resp.status = status
    return resp, BytesIO(json.dumps(payload).encode())


class TestHttpApiInit(unittest.TestCase):
    def _plugin(self, auth_method="key", api_key="testkey"):
        conn = MagicMock()
        plugin = HttpApi(conn)
        plugin.get_option = lambda opt: {
            "api_key": api_key,
            "auth_method": auth_method,
        }.get(opt)
        return plugin

    def test_bearer_token_initially_none(self):
        plugin = self._plugin()
        self.assertIsNone(plugin._bearer_token)
        self.assertEqual(plugin._bearer_token_expiry, 0)

    def test_logout_clears_token(self):
        plugin = self._plugin()
        plugin._bearer_token = "sometoken"
        plugin._bearer_token_expiry = 9999999999
        plugin.logout()
        self.assertIsNone(plugin._bearer_token)
        self.assertEqual(plugin._bearer_token_expiry, 0)


class TestGetApiKey(unittest.TestCase):
    def _plugin(self, key=None, env_key=None):
        conn = MagicMock()
        plugin = HttpApi(conn)
        plugin.get_option = lambda opt: key if opt == "api_key" else "key"
        if env_key is not None:
            import os

            os.environ["VYOS_API_KEY"] = env_key
        return plugin

    def tearDown(self):
        import os

        os.environ.pop("VYOS_API_KEY", None)

    def test_returns_option_key(self):
        plugin = self._plugin(key="mykey")
        self.assertEqual(plugin._get_api_key(), "mykey")

    def test_falls_back_to_env_var(self):
        plugin = self._plugin(key=None, env_key="envkey")
        self.assertEqual(plugin._get_api_key(), "envkey")

    def test_raises_when_no_key(self):
        plugin = self._plugin(key=None)
        with self.assertRaises(ConnectionError):
            plugin._get_api_key()


class TestSendRequestKeyMethod(unittest.TestCase):
    def _plugin(self, auth_method="key", api_key="testkey"):
        conn = MagicMock()
        plugin = HttpApi(conn)
        plugin.get_option = lambda opt: {
            "api_key": api_key,
            "auth_method": auth_method,
        }.get(opt)
        return plugin

    def test_key_method_sends_form_field(self):
        plugin = self._plugin(auth_method="key")
        plugin.connection.send.return_value = _make_response(
            {"success": True, "data": {"host-name": "vyos"}, "error": None},
        )
        result = plugin.send_request("/retrieve", op="showConfig", path=["system"])
        self.assertTrue(result["success"])
        call_kwargs = plugin.connection.send.call_args
        self.assertIn("key=testkey", call_kwargs[1]["data"])
        self.assertNotIn("X-API-Key", call_kwargs[1].get("headers", {}))

    def test_key_method_raises_on_success_false(self):
        plugin = self._plugin(auth_method="key")
        plugin.connection.send.return_value = _make_response(
            {"success": False, "error": "Invalid key", "data": None},
        )
        with self.assertRaises(ConnectionError) as ctx:
            plugin.send_request("/retrieve", op="showConfig", path=[])
        self.assertIn("Invalid key", str(ctx.exception))


class TestSendRequestHeaderMethod(unittest.TestCase):
    def _plugin(self, api_key="testkey"):
        conn = MagicMock()
        plugin = HttpApi(conn)
        plugin.get_option = lambda opt: {
            "api_key": api_key,
            "auth_method": "header",
        }.get(opt)
        return plugin

    def test_header_method_sends_x_api_key_header(self):
        plugin = self._plugin()
        plugin.connection.send.return_value = _make_response(
            {"success": True, "data": {}, "error": None},
        )
        plugin.send_request("/retrieve", op="showConfig", path=[])
        call_kwargs = plugin.connection.send.call_args[1]
        self.assertEqual(call_kwargs["headers"]["X-API-Key"], "testkey")
        self.assertNotIn("key=", call_kwargs["data"])

    def test_header_method_no_key_in_body(self):
        plugin = self._plugin()
        plugin.connection.send.return_value = _make_response(
            {"success": True, "data": {}, "error": None},
        )
        plugin.send_request("/retrieve", op="showConfig", path=[])
        call_kwargs = plugin.connection.send.call_args[1]
        self.assertNotIn("key=testkey", call_kwargs["data"])


class TestSendRequestBearerMethod(unittest.TestCase):
    def _plugin(self, api_key="testkey"):
        conn = MagicMock()
        plugin = HttpApi(conn)
        plugin.get_option = lambda opt: {
            "api_key": api_key,
            "auth_method": "bearer",
        }.get(opt)
        return plugin

    def _token_response(self, token="jwt123", expires_in=3600):
        return _make_response(
            {
                "success": True,
                "data": {"token": token, "expires_in": expires_in},
                "error": None,
            },
        )

    def _retrieve_response(self):
        return _make_response(
            {"success": True, "data": {"host-name": "vyos"}, "error": None},
        )

    def test_bearer_fetches_token_then_sends_auth_header(self):
        plugin = self._plugin()
        plugin.connection.send.side_effect = [
            self._token_response(),
            self._retrieve_response(),
        ]
        result = plugin.send_request("/retrieve", op="showConfig", path=[])
        self.assertTrue(result["success"])
        # First call should be to /token
        first_call = plugin.connection.send.call_args_list[0]
        self.assertEqual(first_call[0][0], "/token")
        # Second call should have Authorization header
        second_call = plugin.connection.send.call_args_list[1]
        self.assertEqual(
            second_call[1]["headers"]["Authorization"],
            "Bearer jwt123",
        )

    def test_bearer_caches_token(self):
        plugin = self._plugin()
        plugin.connection.send.side_effect = [
            self._token_response(),
            self._retrieve_response(),
            self._retrieve_response(),
        ]
        plugin.send_request("/retrieve", op="showConfig", path=[])
        plugin.send_request("/retrieve", op="showConfig", path=[])
        # /token should only be called once
        token_calls = [c for c in plugin.connection.send.call_args_list if c[0][0] == "/token"]
        self.assertEqual(len(token_calls), 1)

    def test_bearer_refreshes_expired_token(self):
        plugin = self._plugin()
        # Set an already-expired token
        plugin._bearer_token = "oldtoken"
        plugin._bearer_token_expiry = time.time() - 100
        plugin.connection.send.side_effect = [
            self._token_response(token="newtoken"),
            self._retrieve_response(),
        ]
        plugin.send_request("/retrieve", op="showConfig", path=[])
        token_calls = [c for c in plugin.connection.send.call_args_list if c[0][0] == "/token"]
        self.assertEqual(len(token_calls), 1)
        self.assertEqual(plugin._bearer_token, "newtoken")

    def test_bearer_raises_on_token_failure(self):
        plugin = self._plugin()
        plugin.connection.send.return_value = _make_response(
            {"success": False, "error": "Invalid key", "data": None},
        )
        with self.assertRaises(ConnectionError) as ctx:
            plugin.send_request("/retrieve", op="showConfig", path=[])
        self.assertIn("Invalid key", str(ctx.exception))


class TestHandleHttpError(unittest.TestCase):
    def test_401_raises_connection_failure(self):
        conn = MagicMock()
        plugin = HttpApi(conn)
        exc = MagicMock()
        exc.code = 401
        with self.assertRaises(AnsibleConnectionFailure):
            plugin.handle_httperror(exc)

    def test_other_errors_returned(self):
        conn = MagicMock()
        plugin = HttpApi(conn)
        exc = MagicMock()
        exc.code = 500
        result = plugin.handle_httperror(exc)
        self.assertEqual(result, exc)


if __name__ == "__main__":
    unittest.main()


class TestSendRequestMtlsMethod(unittest.TestCase):
    def _plugin(self):
        conn = MagicMock()
        plugin = HttpApi(conn)
        plugin.get_option = lambda opt: {
            "auth_method": "mtls",
        }.get(opt)
        return plugin

    def test_mtls_sends_no_api_key(self):
        plugin = self._plugin()
        plugin.connection.send.return_value = (
            MagicMock(status=200),
            BytesIO(
                json.dumps(
                    {"success": True, "data": {}, "error": None},
                ).encode(),
            ),
        )
        plugin.send_request("/retrieve", op="showConfig", path=[])
        call_kwargs = plugin.connection.send.call_args[1]
        self.assertNotIn("key=", call_kwargs["data"])
        self.assertNotIn("X-API-Key", call_kwargs.get("headers", {}))
        self.assertNotIn("Authorization", call_kwargs.get("headers", {}))

    def test_mtls_sends_no_authorization_header(self):
        plugin = self._plugin()
        plugin.connection.send.return_value = (
            MagicMock(status=200),
            BytesIO(
                json.dumps(
                    {"success": True, "data": {}, "error": None},
                ).encode(),
            ),
        )
        plugin.send_request("/retrieve", op="showConfig", path=[])
        headers = plugin.connection.send.call_args[1].get("headers", {})
        self.assertNotIn("Authorization", headers)


class TestSendRequestOidcMethod(unittest.TestCase):
    def _plugin(
        self,
        token_url="http://idp/token",
        client_id="vyos-api",
        client_secret="secret",
    ):
        conn = MagicMock()
        plugin = HttpApi(conn)
        plugin.get_option = lambda opt: {
            "auth_method": "oidc",
            "oidc_token_url": token_url,
            "oidc_client_id": client_id,
            "oidc_client_secret": client_secret,
        }.get(opt)
        return plugin

    def _idp_response(self, token="oidctoken123", expires_in=3600):
        return json.dumps(
            {
                "access_token": token,
                "expires_in": expires_in,
                "token_type": "Bearer",
            },
        ).encode()

    def _retrieve_response(self):
        return (
            MagicMock(status=200),
            BytesIO(
                json.dumps(
                    {"success": True, "data": {"host-name": "vyos"}, "error": None},
                ).encode(),
            ),
        )

    def test_oidc_fetches_token_from_idp(self):
        plugin = self._plugin()
        with patch("ansible_collections.vyos.rest.plugins.httpapi.vyos.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = self._idp_response()
            mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_resp)
            mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
            plugin.connection.send.return_value = self._retrieve_response()
            plugin.send_request("/retrieve", op="showConfig", path=[])

        call_kwargs = plugin.connection.send.call_args[1]
        self.assertEqual(
            call_kwargs["headers"]["Authorization"],
            "Bearer oidctoken123",
        )

    def test_oidc_caches_token(self):
        plugin = self._plugin()
        with patch("ansible_collections.vyos.rest.plugins.httpapi.vyos.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = self._idp_response()
            mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_resp)
            mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
            plugin.connection.send.return_value = self._retrieve_response()
            plugin.send_request("/retrieve", op="showConfig", path=[])
            plugin.connection.send.return_value = self._retrieve_response()
            plugin.send_request("/retrieve", op="showConfig", path=[])
            # urlopen should only be called once
            self.assertEqual(mock_urlopen.call_count, 1)

    def test_oidc_refreshes_expired_token(self):
        plugin = self._plugin()
        plugin._oidc_token = "oldtoken"
        plugin._oidc_token_expiry = time.time() - 100
        with patch("ansible_collections.vyos.rest.plugins.httpapi.vyos.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = self._idp_response(token="newtoken")
            mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_resp)
            mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
            plugin.connection.send.return_value = self._retrieve_response()
            plugin.send_request("/retrieve", op="showConfig", path=[])
        self.assertEqual(plugin._oidc_token, "newtoken")

    def test_oidc_raises_when_token_url_missing(self):
        plugin = self._plugin(token_url=None)
        with self.assertRaises(ConnectionError) as ctx:
            plugin.send_request("/retrieve", op="showConfig", path=[])
        self.assertIn("oidc_token_url", str(ctx.exception))

    def test_oidc_raises_when_idp_unreachable(self):
        plugin = self._plugin()
        with patch("ansible_collections.vyos.rest.plugins.httpapi.vyos.urlopen") as mock_urlopen:
            mock_urlopen.side_effect = Exception("Connection refused")
            with self.assertRaises(ConnectionError) as ctx:
                plugin.send_request("/retrieve", op="showConfig", path=[])
        self.assertIn("OIDC token fetch failed", str(ctx.exception))

    def test_oidc_raises_when_access_token_missing(self):
        plugin = self._plugin()
        with patch("ansible_collections.vyos.rest.plugins.httpapi.vyos.urlopen") as mock_urlopen:
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps({"error": "invalid_client"}).encode()
            mock_urlopen.return_value.__enter__ = MagicMock(return_value=mock_resp)
            mock_urlopen.return_value.__exit__ = MagicMock(return_value=False)
            with self.assertRaises(ConnectionError) as ctx:
                plugin.send_request("/retrieve", op="showConfig", path=[])
        self.assertIn("access_token", str(ctx.exception))

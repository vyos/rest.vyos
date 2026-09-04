.. _vyos.rest.vyos_httpapi:


**************
vyos.rest.vyos
**************

**HttpApi plugin for VyOS REST API**


Version added: 1.0.0

.. contents::
   :local:
   :depth: 1


Synopsis
--------
- This HttpApi plugin provides methods to connect to VyOS devices via their HTTPS REST API.
- Use with ``ansible_connection=ansible.netcommon.httpapi`` and ``ansible_network_os=vyos.rest.vyos``.
- The VyOS REST API must be enabled with ``set service https api keys id ansible key YOUR_KEY``, ``set service https api rest``, then ``commit && save``.




Parameters
----------

.. raw:: html

    <table  border=0 cellpadding=0 class="documentation-table">
        <tr>
            <th colspan="1">Parameter</th>
            <th>Choices/<font color="blue">Defaults</font></th>
                <th>Configuration</th>
            <th width="100%">Comments</th>
        </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>api_key</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">string</span>
                    </div>
                </td>
                <td>
                </td>
                    <td>
                                <div>env:VYOS_API_KEY</div>
                                <div>var: ansible_httpapi_api_key</div>
                                <div>var: ansible_vyos_api_key</div>
                    </td>
                <td>
                        <div>The API key configured on the VyOS device.</div>
                        <div>Set <code>ansible_httpapi_api_key</code> in inventory or the <code>VYOS_API_KEY</code> environment variable.</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>auth_method</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">string</span>
                    </div>
                </td>
                <td>
                        <ul style="margin: 0; padding: 0"><b>Choices:</b>
                                    <li><div style="color: blue"><b>key</b>&nbsp;&larr;</div></li>
                                    <li>header</li>
                                    <li>bearer</li>
                                    <li>mtls</li>
                                    <li>oidc</li>
                        </ul>
                </td>
                    <td>
                                <div>var: ansible_httpapi_vyos_auth_method</div>
                                <div>var: ansible_vyos_auth_method</div>
                    </td>
                <td>
                        <div>Authentication method to use.</div>
                        <div><code>key</code> sends the API key as a form field (default, backward-compatible).</div>
                        <div><code>header</code> sends the API key as an <code>X-API-Key</code> header.</div>
                        <div><code>bearer</code> exchanges the API key for a short-lived JWT via <code>POST /token</code> and sends it as an Authorization Bearer header for subsequent requests.</div>
                        <div><code>mtls</code> uses mutual TLS client certificate authentication. No API key is sent. Requires <code>ansible_httpapi_client_cert</code> and <code>ansible_httpapi_client_key</code> to be set at the connection level.</div>
                        <div><code>oidc</code> fetches a Bearer token from an external identity provider using the OAuth2 client credentials grant and sends it as an Authorization Bearer header. Requires <code>ansible_vyos_oidc_token_url</code>, <code>ansible_vyos_oidc_client_id</code>, and <code>ansible_vyos_oidc_client_secret</code>.</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>oidc_client_id</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">string</span>
                    </div>
                </td>
                <td>
                </td>
                    <td>
                                <div>var: ansible_vyos_oidc_client_id</div>
                    </td>
                <td>
                        <div>OAuth2 client ID for the client credentials grant.</div>
                        <div>Required when <code>auth_method=oidc</code>.</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>oidc_client_secret</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">string</span>
                    </div>
                </td>
                <td>
                </td>
                    <td>
                                <div>var: ansible_vyos_oidc_client_secret</div>
                    </td>
                <td>
                        <div>OAuth2 client secret for the client credentials grant.</div>
                        <div>Required when <code>auth_method=oidc</code>.</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>oidc_token_url</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">string</span>
                    </div>
                </td>
                <td>
                </td>
                    <td>
                                <div>var: ansible_vyos_oidc_token_url</div>
                    </td>
                <td>
                        <div>Full URL of the OAuth2/OIDC token endpoint.</div>
                        <div>E.g. <code>https://keycloak.example.com/realms/vyos/protocol/openid-connect/token</code>.</div>
                        <div>Required when <code>auth_method=oidc</code>.</div>
                </td>
            </tr>
    </table>
    <br/>


Notes
-----

.. note::
   - Bearer tokens are cached in memory for the duration of the connection and refreshed automatically 30 seconds before expiry.
   - Token expiry is controlled on the device via ``set service https api rest authentication expiration <seconds>``.
   - For mTLS, set ``ansible_httpapi_client_cert`` and ``ansible_httpapi_client_key`` at the connection level. The netcommon httpapi connection plugin handles the TLS handshake automatically.
   - OIDC tokens are cached and refreshed using the ``expires_in`` value returned by the identity provider.







Status
------


Authors
~~~~~~~

- VyOS Community (@vyos)


.. hint::
    Configuration entries for each entry type have a low to high priority order. For example, a variable that is lower in the list will override a variable that is higher up.

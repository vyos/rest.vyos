.. _vyos.rest.vyos_httpapi:


**************
vyos.rest.vyos
**************

**VyOS REST API**



.. contents::
   :local:
   :depth: 1


Synopsis
--------
- HTTPAPI plugin for interacting with VyOS REST API.
- Supports multiple authentication methods against the VyOS REST API -- ``key`` (API key in the request body), ``header`` (API key as an ``X-API-Key`` header), ``bearer`` (a VyOS-issued bearer token, fetched and cached), ``mtls`` (mutual TLS, no application-level credential), and ``oidc`` (a bearer token obtained from an external OpenID Connect provider via the client_credentials grant, fetched and cached).




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
                            <div> ini entries:
                                    <p>[httpapi]<br>api_key = VALUE</p>
                            </div>
                                <div>env:ANSIBLE_HTTPAPI_API_KEY</div>
                                <div>env:VYOS_API_KEY</div>
                                <div>var: ansible_httpapi_api_key</div>
                    </td>
                <td>
                        <div>VyOS API key. Required for auth_method <code>key</code>, <code>header</code>, and <code>bearer</code>.</div>
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
                            <div> ini entries:
                                    <p>[httpapi]<br>auth_method = key</p>
                            </div>
                                <div>var: ansible_httpapi_auth_method</div>
                    </td>
                <td>
                        <div>Authentication method to use against the VyOS REST API.</div>
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
                            <div> ini entries:
                                    <p>[httpapi]<br>oidc_client_id = VALUE</p>
                            </div>
                                <div>var: ansible_httpapi_oidc_client_id</div>
                    </td>
                <td>
                        <div>OIDC client ID for the client_credentials grant.</div>
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
                            <div> ini entries:
                                    <p>[httpapi]<br>oidc_client_secret = VALUE</p>
                            </div>
                                <div>var: ansible_httpapi_oidc_client_secret</div>
                    </td>
                <td>
                        <div>OIDC client secret for the client_credentials grant.</div>
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
                            <div> ini entries:
                                    <p>[httpapi]<br>oidc_token_url = VALUE</p>
                            </div>
                                <div>var: ansible_httpapi_oidc_token_url</div>
                    </td>
                <td>
                        <div>Token endpoint URL of the OIDC provider. Required for auth_method <code>oidc</code>.</div>
                </td>
            </tr>
    </table>
    <br/>








Status
------


Authors
~~~~~~~

- Evgeny Molotkov (@eomnom62)


.. hint::
    Configuration entries for each entry type have a low to high priority order. For example, a variable that is lower in the list will override a variable that is higher up.

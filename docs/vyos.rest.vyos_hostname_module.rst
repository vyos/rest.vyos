.. _vyos.rest.vyos_hostname_module:


***********************
vyos.rest.vyos_hostname
***********************

**Manage the hostname of a VyOS device using REST API**


Version added: 1.0.0

.. contents::
   :local:
   :depth: 1


Synopsis
--------
- Configures the system hostname on VyOS network devices via the REST API.
- Supports idempotent configuration — no change is made if the desired hostname already matches the running configuration.
- Uses REST API (``connection=httpapi``) instead of CLI.




Parameters
----------

.. raw:: html

    <table  border=0 cellpadding=0 class="documentation-table">
        <tr>
            <th colspan="2">Parameter</th>
            <th>Choices/<font color="blue">Defaults</font></th>
            <th width="100%">Comments</th>
        </tr>
            <tr>
                <td colspan="2">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>config</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">dictionary</span>
                    </div>
                </td>
                <td>
                </td>
                <td>
                        <div>Hostname configuration dictionary.</div>
                </td>
            </tr>
                                <tr>
                    <td class="elbow-placeholder"></td>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>hostname</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">string</span>
                    </div>
                </td>
                <td>
                </td>
                <td>
                        <div>The hostname to set on the VyOS device.</div>
                        <div>Must be a valid RFC 1123 hostname.</div>
                </td>
            </tr>

            <tr>
                <td colspan="2">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>state</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">string</span>
                    </div>
                </td>
                <td>
                        <ul style="margin: 0; padding: 0"><b>Choices:</b>
                                    <li><div style="color: blue"><b>merged</b>&nbsp;&larr;</div></li>
                                    <li>replaced</li>
                                    <li>overridden</li>
                                    <li>deleted</li>
                                    <li>gathered</li>
                        </ul>
                </td>
                <td>
                        <div>The desired state of the hostname configuration.</div>
                        <div><code>merged</code>, <code>replaced</code>, and <code>overridden</code> are identical for this single-value resource — all three ensure the hostname is set to the value specified in <code>config</code>.</div>
                        <div><code>deleted</code> removes the configured hostname, reverting to the device default.</div>
                        <div><code>gathered</code> retrieves the current hostname from the device and returns it as structured data in the <code>gathered</code> key. No changes are made to the device.</div>
                </td>
            </tr>
    </table>
    <br/>


Notes
-----

.. note::
   - Tested against VyOS 1.3 (equuleus) and 1.4 (sagitta).
   - Requires ``ansible_connection=httpapi`` with the VyOS httpapi plugin.
   - The ``ansible_network_os`` inventory variable must be set to ``vyos.rest.vyos``.



Examples
--------

.. code-block:: yaml

    # Before state:
    # -------------
    # vyos@router:~$ show configuration commands | grep host-name
    # set system host-name 'vyostest'

    - name: Set hostname using merged state
      vyos.rest.vyos_hostname:
        config:
          hostname: vyos
        state: merged

    # After state:
    # ------------
    # set system host-name 'vyos'

    # ------------------------------------------------------------------------

    # Before state:
    # -------------
    # set system host-name 'vyos'

    - name: Override hostname (identical behaviour to merged for this resource)
      vyos.rest.vyos_hostname:
        config:
          hostname: vyosTest
        state: overridden

    # After state:
    # ------------
    # set system host-name 'vyosTest'

    # ------------------------------------------------------------------------

    # Before state:
    # -------------
    # set system host-name 'vyos'

    - name: Replace hostname
      vyos.rest.vyos_hostname:
        config:
          hostname: vyosRouter
        state: replaced

    # After state:
    # ------------
    # set system host-name 'vyosRouter'

    # ------------------------------------------------------------------------

    # Before state:
    # -------------
    # set system host-name 'vyos'

    - name: Delete configured hostname
      vyos.rest.vyos_hostname:
        state: deleted

    # After state:
    # ------------
    # (no host-name entry — device reverts to default)

    # ------------------------------------------------------------------------

    - name: Gather current hostname from device
      vyos.rest.vyos_hostname:
        state: gathered

    # Module result:
    # --------------
    # "gathered": {
    #     "hostname": "vyos"
    # }

    # ------------------------------------------------------------------------

    - name: Idempotency — no change when hostname already matches
      vyos.rest.vyos_hostname:
        config:
          hostname: vyos
        state: merged

    # Module result (hostname already 'vyos'):
    # ----------------------------------------
    # "changed": false



Return Values
-------------
Common return values are documented `here <https://docs.ansible.com/ansible/latest/reference_appendices/common_return_values.html#common-return-values>`_, the following are the fields unique to this module:

.. raw:: html

    <table border=0 cellpadding=0 class="documentation-table">
        <tr>
            <th colspan="1">Key</th>
            <th>Returned</th>
            <th width="100%">Description</th>
        </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="return-"></div>
                    <b>after</b>
                    <a class="ansibleOptionLink" href="#return-" title="Permalink to this return value"></a>
                    <div style="font-size: small">
                      <span style="color: purple">dictionary</span>
                    </div>
                </td>
                <td>when changed</td>
                <td>
                            <div>Hostname configuration on the device after this module ran.</div>
                    <br/>
                        <div style="font-size: smaller"><b>Sample:</b></div>
                        <div style="font-size: smaller; color: blue; word-wrap: break-word; word-break: break-all;">{&#x27;hostname&#x27;: &#x27;vyos&#x27;}</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="return-"></div>
                    <b>before</b>
                    <a class="ansibleOptionLink" href="#return-" title="Permalink to this return value"></a>
                    <div style="font-size: small">
                      <span style="color: purple">dictionary</span>
                    </div>
                </td>
                <td>when <em>state</em> is <code>merged</code>, <code>replaced</code>, <code>overridden</code> or <code>deleted</code></td>
                <td>
                            <div>Hostname configuration on the device before this module ran.</div>
                    <br/>
                        <div style="font-size: smaller"><b>Sample:</b></div>
                        <div style="font-size: smaller; color: blue; word-wrap: break-word; word-break: break-all;">{&#x27;hostname&#x27;: &#x27;vyostest&#x27;}</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="return-"></div>
                    <b>commands</b>
                    <a class="ansibleOptionLink" href="#return-" title="Permalink to this return value"></a>
                    <div style="font-size: small">
                      <span style="color: purple">list</span>
                    </div>
                </td>
                <td>when <em>state</em> is <code>merged</code>, <code>replaced</code>, <code>overridden</code> or <code>deleted</code></td>
                <td>
                            <div>List of API command dicts sent to the device.</div>
                    <br/>
                        <div style="font-size: smaller"><b>Sample:</b></div>
                        <div style="font-size: smaller; color: blue; word-wrap: break-word; word-break: break-all;">[{&#x27;op&#x27;: &#x27;set&#x27;, &#x27;path&#x27;: [&#x27;system&#x27;, &#x27;host-name&#x27;, &#x27;vyos&#x27;]}]</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="return-"></div>
                    <b>gathered</b>
                    <a class="ansibleOptionLink" href="#return-" title="Permalink to this return value"></a>
                    <div style="font-size: small">
                      <span style="color: purple">dictionary</span>
                    </div>
                </td>
                <td>when <em>state</em> is <code>gathered</code></td>
                <td>
                            <div>Current hostname configuration retrieved from the device as structured data. Returned only when <em>state</em> is <code>gathered</code>.</div>
                    <br/>
                        <div style="font-size: smaller"><b>Sample:</b></div>
                        <div style="font-size: smaller; color: blue; word-wrap: break-word; word-break: break-all;">{&#x27;hostname&#x27;: &#x27;vyos&#x27;}</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="return-"></div>
                    <b>response</b>
                    <a class="ansibleOptionLink" href="#return-" title="Permalink to this return value"></a>
                    <div style="font-size: small">
                      <span style="color: purple">dictionary</span>
                    </div>
                </td>
                <td>when changes are applied</td>
                <td>
                            <div>Raw response returned by the VyOS REST API.</div>
                    <br/>
                        <div style="font-size: smaller"><b>Sample:</b></div>
                        <div style="font-size: smaller; color: blue; word-wrap: break-word; word-break: break-all;">{&#x27;success&#x27;: True, &#x27;data&#x27;: None, &#x27;error&#x27;: None}</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="return-"></div>
                    <b>saved</b>
                    <a class="ansibleOptionLink" href="#return-" title="Permalink to this return value"></a>
                    <div style="font-size: small">
                      <span style="color: purple">dictionary</span>
                    </div>
                </td>
                <td>when changes are applied</td>
                <td>
                            <div>Result of the save_config call issued after applying changes.</div>
                    <br/>
                </td>
            </tr>
    </table>
    <br/><br/>


Status
------


Authors
~~~~~~~

- Your Name (@yourhandle)

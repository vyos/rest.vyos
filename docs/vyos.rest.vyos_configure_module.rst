.. _vyos.rest.vyos_configure_module:


************************
vyos.rest.vyos_configure
************************

**Manage VyOS device configuration via the REST API.**


Version added: 1.0.0

.. contents::
   :local:
   :depth: 1


Synopsis
--------
- Sends one or more ``set`` or ``delete`` configuration commands to a VyOS device via its HTTPS REST API (``/configure`` endpoint).
- Each command in *commands* is executed and committed atomically.
- Supports Ansible check-mode (``check_mode=yes``) - no changes are applied.



Requirements
------------
The below requirements are needed on the host that executes this module.

- VyOS 1.3+


Parameters
----------

.. raw:: html

    <table  border=0 cellpadding=0 class="documentation-table">
        <tr>
            <th colspan="1">Parameter</th>
            <th>Choices/<font color="blue">Defaults</font></th>
            <th width="100%">Comments</th>
        </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>api_key</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">string</span>
                         / <span style="color: red">required</span>
                    </div>
                </td>
                <td>
                </td>
                <td>
                        <div>API key configured on the device.</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>commands</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">list</span>
                         / <span style="color: purple">elements=raw</span>
                         / <span style="color: red">required</span>
                    </div>
                </td>
                <td>
                </td>
                <td>
                        <div>List of VyOS configuration commands.</div>
                        <div>Each item may be either a plain string in VyOS CLI syntax (e.g. <code>set interfaces ethernet eth0 description &#x27;WAN&#x27;</code>) or a dict with keys <code>op</code>, <code>path</code>, and optionally <code>value</code>.</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>hostname</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">string</span>
                         / <span style="color: red">required</span>
                    </div>
                </td>
                <td>
                </td>
                <td>
                        <div>IP address or FQDN of the VyOS device.</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>port</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">integer</span>
                    </div>
                </td>
                <td>
                        <b>Default:</b><br/><div style="color: blue">443</div>
                </td>
                <td>
                        <div>HTTPS port for the REST API.</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>save</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">boolean</span>
                    </div>
                </td>
                <td>
                        <ul style="margin: 0; padding: 0"><b>Choices:</b>
                                    <li><div style="color: blue"><b>no</b>&nbsp;&larr;</div></li>
                                    <li>yes</li>
                        </ul>
                </td>
                <td>
                        <div>Whether to save the configuration to disk after a successful commit.</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>timeout</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">integer</span>
                    </div>
                </td>
                <td>
                        <b>Default:</b><br/><div style="color: blue">30</div>
                </td>
                <td>
                        <div>Request timeout in seconds.</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>verify_ssl</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">boolean</span>
                    </div>
                </td>
                <td>
                        <ul style="margin: 0; padding: 0"><b>Choices:</b>
                                    <li><div style="color: blue"><b>no</b>&nbsp;&larr;</div></li>
                                    <li>yes</li>
                        </ul>
                </td>
                <td>
                        <div>Validate the device&#x27;s TLS certificate.</div>
                </td>
            </tr>
    </table>
    <br/>


Notes
-----

.. note::
   - The VyOS HTTP API must be enabled on the device before using this module.
   - Enable with ``set service https api keys id <ID> key <KEY>`` and ``set service https api rest``, then ``commit && save``.
   - Tested against VyOS 1.3 and 1.4.


See Also
--------

.. seealso::

   :ref:`vyos.rest.vyos_retrieve_module`
      The official documentation on the **vyos.rest.vyos_retrieve** module.
   :ref:`vyos.rest.vyos_show_module`
      The official documentation on the **vyos.rest.vyos_show** module.


Examples
--------

.. code-block:: yaml

    - name: Set hostname via REST API
      vyos.rest.vyos_configure:
        hostname: 192.168.1.1
        api_key: MY-KEY
        commands:
          - "set system host-name vyos-router"

    - name: Configure an interface description and address
      vyos.rest.vyos_configure:
        hostname: 192.168.1.1
        api_key: MY-KEY
        commands:
          - "set interfaces ethernet eth1 description 'UPLINK'"
          - "set interfaces ethernet eth1 address 10.0.0.1/30"
        save: true

    - name: Delete a static route using dict syntax
      vyos.rest.vyos_configure:
        hostname: 192.168.1.1
        api_key: MY-KEY
        commands:
          - op: delete
            path: ["protocols", "static", "route", "192.0.2.0/24"]



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
                    <b>changed</b>
                    <a class="ansibleOptionLink" href="#return-" title="Permalink to this return value"></a>
                    <div style="font-size: small">
                      <span style="color: purple">boolean</span>
                    </div>
                </td>
                <td>always</td>
                <td>
                            <div>Whether the device configuration was modified.</div>
                    <br/>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="return-"></div>
                    <b>commands_sent</b>
                    <a class="ansibleOptionLink" href="#return-" title="Permalink to this return value"></a>
                    <div style="font-size: small">
                      <span style="color: purple">list</span>
                       / <span style="color: purple">elements=dictionary</span>
                    </div>
                </td>
                <td>always</td>
                <td>
                            <div>The list of commands dispatched to the API.</div>
                    <br/>
                        <div style="font-size: smaller"><b>Sample:</b></div>
                        <div style="font-size: smaller; color: blue; word-wrap: break-word; word-break: break-all;">[{&#x27;op&#x27;: &#x27;set&#x27;, &#x27;path&#x27;: [&#x27;system&#x27;, &#x27;host-name&#x27;], &#x27;value&#x27;: &#x27;vyos-router&#x27;}]</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="return-"></div>
                    <b>saved</b>
                    <a class="ansibleOptionLink" href="#return-" title="Permalink to this return value"></a>
                    <div style="font-size: small">
                      <span style="color: purple">boolean</span>
                    </div>
                </td>
                <td>always</td>
                <td>
                            <div>Whether the configuration was saved to disk.</div>
                    <br/>
                </td>
            </tr>
    </table>
    <br/><br/>


Status
------


Authors
~~~~~~~

- VyOS Community (@vyos)

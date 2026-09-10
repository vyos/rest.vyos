.. _vyos.rest.vyos_configure_module:


************************
vyos.rest.vyos_configure
************************

**Send raw set/delete commands to a VyOS device via REST API.**


Version added: 1.0.0

.. contents::
   :local:
   :depth: 1


Synopsis
--------
- Sends one or more set/delete configuration commands to a VyOS device via the HTTPS REST API as a single atomic batch commit.
- Useful for configuration not covered by dedicated resource modules, or for test setup and teardown tasks.
- Commands are parsed from CLI-style strings (``set ...`` / ``delete ...``).




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
                    <b>commands</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">list</span>
                         / <span style="color: purple">elements=string</span>
                         / <span style="color: red">required</span>
                    </div>
                </td>
                <td>
                </td>
                <td>
                        <div>List of CLI-style configuration commands.</div>
                        <div>Each command must start with <code>set</code> or <code>delete</code>.</div>
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
                        <div>Whether to save the configuration after applying commands.</div>
                </td>
            </tr>
    </table>
    <br/>



See Also
--------

.. seealso::

   :ref:`vyos.vyos.vyos_config_module`
      The official documentation on the **vyos.vyos.vyos_config** module.


Examples
--------

.. code-block:: yaml

    - name: Add loopback address for testing
      vyos.rest.vyos_configure:
        commands:
          - set interfaces loopback lo address 20.1.1.1/32
        save: false

    - name: Remove loopback address after testing
      vyos.rest.vyos_configure:
        commands:
          - delete interfaces loopback lo address 20.1.1.1/32
        save: false

    - name: Multiple commands in one atomic commit
      vyos.rest.vyos_configure:
        commands:
          - set system host-name vyos-test
          - set system domain-name example.com
        save: true



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
                    <b>commands</b>
                    <a class="ansibleOptionLink" href="#return-" title="Permalink to this return value"></a>
                    <div style="font-size: small">
                      <span style="color: purple">list</span>
                    </div>
                </td>
                <td>always</td>
                <td>
                            <div>Parsed command payloads sent to the device.</div>
                    <br/>
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
                <td>when commands are applied</td>
                <td>
                            <div>Raw API response.</div>
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

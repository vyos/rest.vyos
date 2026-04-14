.. _vyos.rest.vyos_banner_module:


*********************
vyos.rest.vyos_banner
*********************

**Manage login banners on VyOS devices using REST API**


Version added: 1.0.0

.. contents::
   :local:
   :depth: 1


Synopsis
--------
- Configure pre-login and post-login banners on VyOS devices via REST API.
- Supports idempotent configuration using structured data.
- Multiline banner text is supported via YAML block scalars.
- Uses REST API (``connection=httpapi``) instead of CLI.
- VyOS stores multiline banners as a single string with literal ``\\n`` separators.




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
                         / <span style="color: red">required</span>
                    </div>
                </td>
                <td>
                </td>
                <td>
                        <div>Banner configuration.</div>
                </td>
            </tr>
                                <tr>
                    <td class="elbow-placeholder"></td>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>banner</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">string</span>
                         / <span style="color: red">required</span>
                    </div>
                </td>
                <td>
                        <ul style="margin: 0; padding: 0"><b>Choices:</b>
                                    <li>pre-login</li>
                                    <li>post-login</li>
                        </ul>
                </td>
                <td>
                        <div>Banner type to configure.</div>
                </td>
            </tr>
            <tr>
                    <td class="elbow-placeholder"></td>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>text</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">string</span>
                    </div>
                </td>
                <td>
                </td>
                <td>
                        <div>Banner text. Supports multiline strings via YAML block scalar (|).</div>
                        <div>Internally, real newlines are converted to literal <code>\\n</code> as VyOS expects.</div>
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
                        <div>Desired state of the configuration.</div>
                </td>
            </tr>
    </table>
    <br/>


Notes
-----

.. note::
   - This module requires ``ansible_connection=httpapi``.
   - Banner text comparison is whitespace-normalized for idempotency.
   - VyOS stores banner text as a leaf string value with literal ``\\n`` for newlines.
   - For ``merged``, ``replaced``, and ``overridden`` states, the behaviour is identical for this single-leaf resource — the banner value is set to the desired text.



Examples
--------

.. code-block:: yaml

    - name: Configure single-line pre-login banner
      vyos.rest.vyos_banner:
        config:
          banner: pre-login
          text: "Unauthorized access is prohibited"
        state: merged

    - name: Configure multiline post-login banner
      vyos.rest.vyos_banner:
        config:
          banner: post-login
          text: |
            Welcome to VyOS
            Authorized users only
            Disconnect if you are not authorized
        state: merged

    - name: Replace post-login banner
      vyos.rest.vyos_banner:
        config:
          banner: post-login
          text: "Welcome to VyOS"
        state: replaced

    - name: Remove pre-login banner
      vyos.rest.vyos_banner:
        config:
          banner: pre-login
        state: deleted

    - name: Gather banner configuration
      vyos.rest.vyos_banner:
        config:
          banner: pre-login
        state: gathered



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
                            <div>Configuration after changes (text uses real newlines).</div>
                    <br/>
                        <div style="font-size: smaller"><b>Sample:</b></div>
                        <div style="font-size: smaller; color: blue; word-wrap: break-word; word-break: break-all;">{&#x27;banner&#x27;: &#x27;pre-login&#x27;, &#x27;text&#x27;: &#x27;New banner text&#x27;}</div>
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
                <td>always</td>
                <td>
                            <div>Configuration before changes (text uses real newlines).</div>
                    <br/>
                        <div style="font-size: smaller"><b>Sample:</b></div>
                        <div style="font-size: smaller; color: blue; word-wrap: break-word; word-break: break-all;">{&#x27;banner&#x27;: &#x27;pre-login&#x27;, &#x27;text&#x27;: &#x27;Old banner text&#x27;}</div>
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
                <td>when changes are required</td>
                <td>
                            <div>List of API command dicts sent to the device.</div>
                    <br/>
                        <div style="font-size: smaller"><b>Sample:</b></div>
                        <div style="font-size: smaller; color: blue; word-wrap: break-word; word-break: break-all;">[{&#x27;op&#x27;: &#x27;set&#x27;, &#x27;path&#x27;: [&#x27;system&#x27;, &#x27;login&#x27;, &#x27;banner&#x27;, &#x27;pre-login&#x27;], &#x27;value&#x27;: &#x27;New banner text&#x27;}]</div>
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
                <td>when state is gathered</td>
                <td>
                            <div>Current device configuration (text uses real newlines).</div>
                    <br/>
                        <div style="font-size: smaller"><b>Sample:</b></div>
                        <div style="font-size: smaller; color: blue; word-wrap: break-word; word-break: break-all;">{&#x27;banner&#x27;: &#x27;pre-login&#x27;, &#x27;text&#x27;: &#x27;Current banner text&#x27;}</div>
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
                            <div>Raw response from VyOS REST API.</div>
                    <br/>
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
                            <div>Result of save_config call after applying changes.</div>
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

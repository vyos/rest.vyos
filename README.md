# vyos.rest

Ansible collection for managing VyOS via REST API.

<!--start collection content-->
### Httpapi plugins
Name | Description
--- | ---
[vyos.rest.vyos](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_httpapi.rst)|HttpApi plugin for VyOS REST API

### Modules
Name | Description
--- | ---
[vyos.rest.vyos_banner](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_banner_module.rst)|Manage multiline banners on VyOS devices via REST API.
[vyos.rest.vyos_configure](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_configure_module.rst)|Send raw set/delete commands to a VyOS device via REST API.
[vyos.rest.vyos_hostname](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_hostname_module.rst)|Manage the system hostname on a VyOS device via the REST API.
[vyos.rest.vyos_lldp_global](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_lldp_global_module.rst)|Manage LLDP global configuration on VyOS via REST API.
[vyos.rest.vyos_logging_global](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_logging_global_module.rst)|Manage syslog configuration on VyOS devices using REST API
[vyos.rest.vyos_ntp_global](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_ntp_global_module.rst)|Manage NTP configuration on VyOS devices using REST API
[vyos.rest.vyos_route_maps](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_route_maps_module.rst)|Manage route-map configuration on VyOS devices using REST API
[vyos.rest.vyos_snmp_server](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_snmp_server_module.rst)|Manage SNMP server configuration on VyOS devices using REST API

<!--end collection content-->

<!--start requires_ansible-->
## Ansible version compatibility

This collection has been tested against the following Ansible versions: **>=2.15.0**.

Plugins and modules within a collection may be tested with only specific Ansible versions.
A collection may contain metadata that identifies these versions.
PEP440 is the schema used to describe the versions of Ansible.
<!--end requires_ansible-->

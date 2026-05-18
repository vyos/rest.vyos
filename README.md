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
[vyos.rest.vyos_bgp_address_family](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_bgp_address_family_module.rst)|BGP Address Family resource module via REST API.
[vyos.rest.vyos_bgp_global](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_bgp_global_module.rst)|Manage BGP global configuration on VyOS via the REST API.
[vyos.rest.vyos_config_file](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_config_file_module.rst)|Save or load VyOS configuration files via the REST API.
[vyos.rest.vyos_configure](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_configure_module.rst)|Manage VyOS device configuration via the REST API.
[vyos.rest.vyos_facts](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_facts_module.rst)|Get facts about VyOS devices via REST API.
[vyos.rest.vyos_firewall_global](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_firewall_global_module.rst)|Firewall global resource module via REST API.
[vyos.rest.vyos_firewall_interfaces](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_firewall_interfaces_module.rst)|Firewall interfaces resource module via REST API.
[vyos.rest.vyos_firewall_rules](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_firewall_rules_module.rst)|Manage firewall rules on VyOS via the REST API.
[vyos.rest.vyos_generate](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_generate_module.rst)|Execute generate commands on a VyOS device via REST API.
[vyos.rest.vyos_hostname](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_hostname_module.rst)|Manage the system hostname on a VyOS device via the REST API.
[vyos.rest.vyos_image](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_image_module.rst)|Manage VyOS system images via the REST API.
[vyos.rest.vyos_interfaces](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_interfaces_module.rst)|Manage interface attributes on a VyOS device via the REST API.
[vyos.rest.vyos_l3_interfaces](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_l3_interfaces_module.rst)|Manage L3 interface attributes on VyOS via the REST API.
[vyos.rest.vyos_lag_interfaces](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_lag_interfaces_module.rst)|LAG/bonding interfaces resource module via REST API.
[vyos.rest.vyos_lldp_global](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_lldp_global_module.rst)|Manage LLDP global configuration on VyOS via REST API.
[vyos.rest.vyos_lldp_interfaces](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_lldp_interfaces_module.rst)|LLDP interfaces resource module via REST API.
[vyos.rest.vyos_logging_global](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_logging_global_module.rst)|Manage syslog configuration on VyOS devices using REST API
[vyos.rest.vyos_ntp_global](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_ntp_global_module.rst)|Manage NTP configuration on VyOS devices using REST API
[vyos.rest.vyos_ospf_interfaces](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_ospf_interfaces_module.rst)|OSPF Interfaces Resource Module via REST API.
[vyos.rest.vyos_ospfv2](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_ospfv2_module.rst)|OSPFv2 resource module via REST API.
[vyos.rest.vyos_ospfv3](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_ospfv3_module.rst)|OSPFv3 resource module via REST API.
[vyos.rest.vyos_ping](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_ping_module.rst)|Test reachability using ping via VyOS REST API.
[vyos.rest.vyos_prefix_lists](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_prefix_lists_module.rst)|Prefix-Lists resource module via REST API.
[vyos.rest.vyos_reset](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_reset_module.rst)|Execute reset commands on a VyOS device via REST API.
[vyos.rest.vyos_route_maps](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_route_maps_module.rst)|Route Map resource module via REST API.
[vyos.rest.vyos_show](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_show_module.rst)|Execute op-mode show commands on a VyOS device via REST API.
[vyos.rest.vyos_snmp_server](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_snmp_server_module.rst)|Manage SNMP server configuration on VyOS devices using REST API
[vyos.rest.vyos_static_routes](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_static_routes_module.rst)|Manage static routes on VyOS via the REST API.
[vyos.rest.vyos_system](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_system_module.rst)|Manage system settings on VyOS via the REST API.
[vyos.rest.vyos_user](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_user_module.rst)|Manage local users on VyOS via the REST API.
[vyos.rest.vyos_vlan](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_vlan_module.rst)|Manage VLANs on VyOS network devices via REST API.

<!--end collection content-->

<!--start requires_ansible-->
## Ansible version compatibility

This collection has been tested against the following Ansible versions: **>=2.15.0**.

Plugins and modules within a collection may be tested with only specific Ansible versions.
A collection may contain metadata that identifies these versions.
PEP440 is the schema used to describe the versions of Ansible.
<!--end requires_ansible-->

# vyos.rest

Ansible collection for managing VyOS network devices via the HTTPS REST API,
as an alternative to the SSH/CLI-based `vyos.vyos` collection.

## Requirements

- VyOS 1.3 or later
- Ansible >= 2.15.0
- `ansible.netcommon` >= 2.5.1
- `ansible.utils`

## Configuring VyOS for REST API access

Before using this collection, enable the REST API on each VyOS device:

```
set service https api keys id ansible key YOUR_SECRET_KEY
set service https api rest
commit
save
```

> **Note:** Choose a strong random key. The key is sent with every API
> request and acts as the authentication credential.

## Inventory configuration

Add the following variables to your inventory for each VyOS host:

```ini
[vyos]
vyos-router-01 ansible_host=192.168.1.1

[vyos:vars]
ansible_connection=ansible.netcommon.httpapi
ansible_network_os=vyos.rest.vyos
ansible_httpapi_use_ssl=true
ansible_httpapi_validate_certs=false
ansible_httpapi_api_key=YOUR_SECRET_KEY
```

Or in YAML format:

```yaml
all:
  hosts:
    vyos-router-01:
      ansible_host: 192.168.1.1
      ansible_connection: ansible.netcommon.httpapi
      ansible_network_os: vyos.rest.vyos
      ansible_httpapi_use_ssl: true
      ansible_httpapi_validate_certs: false
      ansible_httpapi_api_key: YOUR_SECRET_KEY
```

## Installation

```bash
ansible-galaxy collection install vyos.rest
```

Or from source:

```bash
git clone https://github.com/vyos/vyos.rest.git
ansible-galaxy collection install vyos.rest/ --force
```

<!--start collection content-->
### Httpapi plugins
Name | Description
--- | ---
[vyos.rest.vyos](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_httpapi.rst)|HttpApi plugin for VyOS REST API

### Modules

Modules marked ⚠️ are not yet available in this release.

Name | Description
--- | ---
[vyos.rest.vyos_banner](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_banner_module.rst)|Manage multiline banners on VyOS devices via REST API.
[vyos.rest.vyos_configure](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_configure_module.rst)|Send raw set/delete commands to a VyOS device via REST API.
[vyos.rest.vyos_hostname](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_hostname_module.rst)|Manage the system hostname on a VyOS device via the REST API.
[vyos.rest.vyos_lldp_global](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_lldp_global_module.rst)|Manage LLDP global configuration on VyOS via REST API.
[vyos.rest.vyos_logging_global](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_logging_global_module.rst)|Manage syslog configuration on VyOS devices using REST API.
[vyos.rest.vyos_ntp_global](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_ntp_global_module.rst)|Manage NTP configuration on VyOS devices using REST API.
[vyos.rest.vyos_prefix_lists](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_prefix_lists_module.rst)|⚠️ Manage prefix-list configuration on VyOS devices using REST API. *(not yet available)*
[vyos.rest.vyos_route_maps](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_route_maps_module.rst)|Manage route-map configuration on VyOS devices using REST API.
[vyos.rest.vyos_snmp_server](https://github.com/vyos/vyos.rest/blob/main/docs/vyos.rest.vyos_snmp_server_module.rst)|Manage SNMP server configuration on VyOS devices using REST API.

<!--end collection content-->

<!--start requires_ansible-->
## Ansible version compatibility

This collection has been tested against the following Ansible versions: **>=2.15.0**.

Plugins and modules within a collection may be tested with only specific Ansible versions.
A collection may contain metadata that identifies these versions.
PEP440 is the schema used to describe the versions of Ansible.
<!--end requires_ansible-->

## Relation to vyos.vyos

This collection mirrors the module interface of the
[vyos.vyos](https://github.com/vyos/vyos.vyos) collection but communicates
over HTTPS REST instead of SSH/network_cli. It is suitable for environments
where SSH access is restricted or where the REST API is preferred for
automation.

| Feature | vyos.vyos | vyos.rest |
|---------|-----------|-----------|
| Transport | SSH / network_cli | HTTPS REST |
| Connection plugin | `ansible.netcommon.network_cli` | `ansible.netcommon.httpapi` |
| VyOS requirement | Any | VyOS 1.3+ with REST API enabled |
| Atomic commits | Per-command | Batch (single commit) |

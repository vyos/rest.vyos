# vyos.rest Test Framework

Equivalent structure to `vyos.vyos` CLI collection tests, adapted for
the REST API connection model.

## Structure

```
tests/
├── unit/
│   ├── modules/
│   │   ├── base.py                      # VyOSModuleTestCase base class + load_fixture
│   │   ├── test_vyos_ntp_global.py
│   │   ├── test_vyos_logging_global.py
│   │   ├── test_vyos_prefix_lists.py
│   │   └── test_vyos_route_maps.py
│   └── fixtures/
│       ├── ntp_global_running.json      # Confirmed API responses from device
│       ├── logging_global_running.json
│       ├── prefix_lists_running.json
│       ├── route_maps_running.json
│       ├── snmp_server_running.json
│       └── lldp_global_running.json
└── integration/
    ├── network-integration.cfg
    ├── inventory.network                # Edit before running
    └── targets/
        ├── vyos_ntp_global/tasks/main.yaml
        ├── vyos_logging_global/tasks/main.yaml
        ├── vyos_prefix_lists/tasks/main.yaml
        ├── vyos_route_maps/tasks/main.yaml
        ├── vyos_lldp_global/tasks/main.yaml
        ├── vyos_snmp_server/tasks/main.yaml
        ├── vyos_hostname/tasks/main.yaml
        └── vyos_banner/tasks/main.yaml
```

## Unit Tests

Unit tests cover:
- `normalize_config` / `normalize_running` — argspec and API parsing
- `build_commands` diff logic — all states (merged/replaced/overridden/deleted)
- Fixture-based parsing — confirmed API shapes from the actual device

No device connection needed. Each test imports the module's functions
directly and calls them with mock data or fixture JSON.

### Run all unit tests

```bash
# From collection root
ansible-test units tests/unit/modules/ --python 3.12

# Or with pytest directly (no ansible-test required)
cd /path/to/ansible_collections/vyos/rest
python -m pytest tests/unit/modules/ -v
```

### Run a single module's tests

```bash
ansible-test units tests/unit/modules/test_vyos_ntp_global.py --python 3.12
python -m pytest tests/unit/modules/test_vyos_ntp_global.py -v
```

## Integration Tests

Integration tests run against a live VyOS device. Each target:
1. Tears down any existing config for that resource
2. Tests merged (including idempotency)
3. Tests gathered
4. Tests replaced (including idempotency)
5. Tests deleted (including idempotency)
6. Tears down after

### Prerequisites

Edit `tests/integration/inventory.network` with your device details.

### Run all integration tests

```bash
ansible-test network-integration \
  --inventory tests/integration/inventory.network \
  vyos_*
```

### Run a single module's integration test

```bash
ansible-test network-integration \
  --inventory tests/integration/inventory.network \
  vyos_ntp_global

# Or with ansible-playbook directly
ansible-playbook \
  -i tests/integration/inventory.network \
  tests/integration/targets/vyos_ntp_global/tasks/main.yaml
```

## Adding Tests for a New Module

1. Add a fixture: `tests/unit/fixtures/<module>_running.json`
   - Copy the exact API response from a `curl showConfig` call
   - This ensures tests reflect real device behaviour

2. Add unit tests: `tests/unit/modules/test_<module>.py`
   - Subclass `VyOSModuleTestCase` for fixture-based tests
   - Test `normalize_*`, `get_running_config`, `build_commands` directly

3. Add integration target: `tests/integration/targets/<module>/tasks/main.yaml`
   - Follow the teardown → merged → idempotent → gathered → replaced → deleted pattern

## Key Differences from CLI Collection Tests

| CLI collection | REST collection |
|---|---|
| Mocks `connection.get` returning CLI text | Mocks `vyos.get_config()` returning JSON dict |
| Fixture files are `.cfg` text (CLI output) | Fixture files are `.json` (API response) |
| Tests parse CLI text via `rm_templates` | Tests parse API dicts via `normalize_running` |
| `ansible-test units --docker` for isolation | Can run with `pytest` directly, no docker needed |

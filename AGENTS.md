# AGENTS.md

## Project purpose

Ansible Galaxy collection `vyos.rest` — modules and an httpapi plugin to manage VyOS devices via the **HTTP/REST API** (as opposed to SSH/CLI, which is what the sister `vyos.vyos` collection uses). Modules cover hostname, banner, and similar object-level resources; the httpapi plugin (`vyos.rest.vyos`) wraps the VyOS HTTP API endpoint exposed by `vyos-1x`'s `services` layer.

## Tech stack

- Python (Ansible collection, no setup.py).
- `pyproject.toml` configures `black` (line-length 100) and `pytest` (with `xdist -n 2`).
- `requirements.txt` / `test-requirements.txt` for runtime/test deps.
- `galaxy.yml` for collection metadata.

## Build / test / run

```sh
ansible-galaxy collection build       # produces vyos-rest-<ver>.tar.gz
ansible-galaxy collection install vyos-rest-<ver>.tar.gz
pytest                                # runs collection tests
black.                               # format
```

## Repository layout

- `plugins/` — Ansible plugins; `plugins/httpapi/vyos.py` is the REST-API httpapi shim, `plugins/modules/*.py` the resource modules.
- `meta/` — Ansible meta (`runtime.yml`, redirects).
- `docs/` — generated module docs.
- `changelogs/` — `antsibull-changelog` fragments.
- `galaxy.yml`, `pyproject.toml`, `requirements.txt`, `test-requirements.txt`.

## Cross-repo context

Companion to `vyos/vyos.vyos` (the SSH-based Ansible collection). Both target VyOS, but `rest.vyos` requires the VyOS HTTP API — provided at runtime by `vyos-1x`'s `src/services/` plus the runtime-deps Debian wrapper `vyos/vyos-http-api-tools` (FastAPI/uvicorn/ariadne). When the API surface in `vyos-1x` changes, the httpapi plugin and modules here are what consumers feel.

## Conventions

- Default branch `current`.
- Commit / PR title format: `component: T12345: description` (Phorge task ID at https://vyos.dev).
- Format: `black` (line length 100). Test runner: `pytest` with `pytest-xdist`.
- Has `CODEOWNERS` (audit baseline). Public, GPL-licensed.

## Mirror relationship

No mirror twin (no `VyOS-Networks/rest.vyos`). Sole home is here.

## Notes for future contributors

- Treat the VyOS HTTP API as the contract: changes in `vyos-1x/src/services/` may require synchronized updates here. There is no CI-enforced contract test today.
- Old name "rest.vyos" reflects the Galaxy-collection naming (`vyos.rest`); don't rename to `vyos-rest` casually — it's a Galaxy identifier.

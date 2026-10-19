# frappe-crm-multi-company — Agent Operating Guide

AGPL-3.0-or-later Frappe v16 app on top of Frappe CRM (`crm`) and ERPNext. Several businesses in one CRM: each
lead and deal has a business, and quotations go out under the company the business bills under on the day. No
fork of Frappe or CRM: two document events and one whitelisted-method override.

## Model

- **CRM Business** (named by `business_name`): `companies` (CRM Business Company: company, valid_from, valid_to;
  inclusive, open at a missing end; no overlaps) and `public_sites` (CRM Business Site: a Public Site name; a site
  belongs to one business). Validation lives in the controller, the logic in `rules.py`.
- **`crm_business`** Link on CRM Lead and CRM Deal (custom fields from `install.py`). A lead takes it from its
  `public_site` (public_site_router's field); a deal from its lead. CRM's `create_deal` copies same-named fields, so
  converting a lead carries it; `set_deal_business` covers deals linked to a lead another way. An existing value is
  never overwritten.
- **Quotations:** `business.get_quotation_url` overrides CRM's whitelisted method, calls it, then sets `company`
  from the deal's business for today. No business, or no company on that date: CRM's default stands.

## Code

- `rules.py`: pure (no Frappe): periods, overlap/order checks, contested sites, the URL parameter. Tested in `tests/`.
- `business.py`: lookups, the two document events and the override.
- `install.py` (after_install + after_migrate, idempotent): the custom fields and a Business section in the CRM
  lead and deal side panels (only if missing).

## Testing

Pure logic: `uv run --no-project --python 3.14 --with pytest python -I -m pytest`. Frappe-backed (real DB):
`tests/e2e/run.sh` builds a podman bench (ERPNext v16 image + CRM at production's pin + the crm_heat_tracking and
public_site_router checkouts beside this one + this app) and runs `bench run-tests` for this app and
crm_heat_tracking, so a CRM bump is proven against both. Lint: `uvx ruff format --check . && uvx ruff check .`

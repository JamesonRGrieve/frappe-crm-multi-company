<!-- SPDX-License-Identifier: AGPL-3.0-or-later -->
# frappe-crm-multi-company

Run several businesses out of one Frappe CRM. Each lead and deal belongs to a **business**, and a deal's quotation
goes out under the company that business bills under on the day it's quoted.

Frappe CRM quotes every deal under the single company set in ERPNext CRM Settings. That's fine for one company and
wrong as soon as one ERP serves several: a 3S Hub repair and a Zephyrex project would both be quoted by whichever
company is in that one setting. It also can't follow a business that changes hands, such as a side business billed
by a sole proprietorship until year end and by its new corporation after.

## What it does

- **CRM Business** records: a name, the companies it bills under with the dates each applies (inclusive, open at
  either end), and the Public Sites its website leads come from.
- A **Business** field on CRM Lead and CRM Deal, filterable in the CRM app and shown in the side panels.
- A lead from a business's website gets that business (from the lead's Public Site, set by
  [public_site_router](https://github.com/JamesonRGrieve/frappe-public-site-router)). Converting a lead to a deal
  carries the business across.
- CRM's **Create Quotation** sets the company the deal's business bills under that day. A deal without a business,
  or a business with no company on that date, keeps CRM's default company.

Periods may not overlap and a Public Site belongs to one business; saving a CRM Business that breaks either is
refused.

## Setup

1. Install on a site with ERPNext 16 and Frappe CRM (`bench get-app`, `bench --site <site> install-app crm_multi_company`).
   CRM must be at [f9a4562](https://github.com/frappe/crm/commit/f9a456282bb9854a44c950a16cf598656859d5c7) or
   later: earlier commits call an ERPNext function ERPNext 16 removed, so their ERPNext CRM Settings can't be enabled.
2. Turn on ERPNext CRM Settings (same site) and pick the default company.
3. Add a CRM Business per business, with its companies and Public Sites.
4. Set the Business on existing leads and deals; new website leads get it automatically.

## How it works

No fork of Frappe or CRM. A `validate` document event on CRM Lead and CRM Deal fills the business, and
`override_whitelisted_methods` wraps CRM's `get_quotation_url`: CRM builds the quotation link as usual and this app
replaces its `company`.

## Development

```
uv run --no-project --python 3.14 --with pytest python -I -m pytest      # pure logic
uvx ruff format --check . && uvx ruff check .                           # format and lint
tests/e2e/run.sh                                                        # Frappe-backed tests on a podman bench
```

## License

AGPL-3.0-or-later.

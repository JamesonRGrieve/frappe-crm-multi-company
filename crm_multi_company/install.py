# SPDX-License-Identifier: AGPL-3.0-or-later
"""Install and migrate: the Business field on CRM Lead and CRM Deal, and a Business section in the CRM app's
lead and deal side panels. Idempotent, and leaves changes made in the ERP alone: a panel section is added only
when missing."""

from __future__ import annotations

import json

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from crm_multi_company.business import BUSINESS, DEAL, FIELD, LEAD

PANEL_SECTION = "crm_business_section"
SIDE_PANELS = (f"{LEAD}-Side Panel", f"{DEAL}-Side Panel")


def business_field(insert_after: str) -> dict:
	return {
		"fieldname": FIELD,
		"fieldtype": "Link",
		"label": "Business",
		"options": BUSINESS,
		"insert_after": insert_after,
		"in_standard_filter": 1,
		"in_list_view": 1,
		"description": "The business this belongs to; its company for the quotation date is the one quoted under.",
	}


CUSTOM_FIELDS = {LEAD: [business_field("source")], DEAL: [business_field("source")]}


def after_install() -> None:
	ensure()


def after_migrate() -> None:
	ensure()


def ensure() -> None:
	create_custom_fields(CUSTOM_FIELDS, update=True)
	for panel in SIDE_PANELS:
		ensure_panel_section(panel)


def ensure_panel_section(panel: str) -> None:
	if not frappe.db.exists("CRM Fields Layout", panel):
		return
	layout = frappe.get_doc("CRM Fields Layout", panel)
	sections = json.loads(layout.layout or "[]")
	if any(section.get("name") == PANEL_SECTION for section in sections):
		return
	section = {
		"label": "Business",
		"name": PANEL_SECTION,
		"opened": True,
		"columns": [{"name": "crm_business_column", "fields": [FIELD]}],
	}
	layout.layout = json.dumps([section, *sections])
	layout.save(ignore_permissions=True)

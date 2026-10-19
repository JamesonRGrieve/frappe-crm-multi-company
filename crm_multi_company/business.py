# SPDX-License-Identifier: AGPL-3.0-or-later
"""Frappe glue: a lead's business from its Public Site, a deal's from its lead, and the quotation link's company
from the deal's business on the day the quotation is made.

Frappe CRM quotes every deal under the one company in ERPNext CRM Settings. Its Create Quotation button calls
``get_quotation_url``; this app overrides that whitelisted method (``override_whitelisted_methods``), lets CRM build
the URL as usual, and sets the company the deal's business bills under today. A deal without a business, or a
business with no company on that date, keeps CRM's default.
"""

from __future__ import annotations

from datetime import date

import frappe
from frappe.model.document import Document
from frappe.utils import getdate

from crm_multi_company import rules

BUSINESS = "CRM Business"
BUSINESS_SITE = "CRM Business Site"
LEAD = "CRM Lead"
DEAL = "CRM Deal"
FIELD = "crm_business"
PUBLIC_SITE_FIELD = "public_site"


def periods(business: str) -> list[rules.CompanyPeriod]:
	return periods_of(frappe.get_cached_doc(BUSINESS, business))


def periods_of(doc: Document) -> list[rules.CompanyPeriod]:
	"""A CRM Business document's company table as periods."""
	return [
		rules.CompanyPeriod(
			row.company,
			getdate(row.valid_from) if row.valid_from else None,
			getdate(row.valid_to) if row.valid_to else None,
		)
		for row in doc.companies
	]


def company_for(business: str, on: date) -> str | None:
	"""The company the business bills under on the date (None when it has none then)."""
	return rules.company_on(periods(business), on)


def business_for_site(public_site: str) -> str | None:
	return frappe.db.get_value(BUSINESS_SITE, {"public_site": public_site, "parenttype": BUSINESS}, "parent")


def set_lead_business(doc: Document, method: str | None = None) -> None:
	"""A lead from a business's website belongs to that business (kept if already set)."""
	site = doc.get(PUBLIC_SITE_FIELD)
	if not doc.get(FIELD) and site:
		doc.set(FIELD, business_for_site(site))


def set_deal_business(doc: Document, method: str | None = None) -> None:
	"""A deal belongs to its lead's business. Converting a lead copies the field already (CRM copies same-named
	fields); this covers deals linked to a lead some other way."""
	if not doc.get(FIELD) and doc.get("lead"):
		doc.set(FIELD, frappe.db.get_value(LEAD, doc.lead, FIELD))


@frappe.whitelist()
def get_quotation_url(crm_deal: str, organization: str | None = None) -> str:
	from crm.fcrm.doctype.erpnext_crm_settings.erpnext_crm_settings import get_quotation_url as crm_quotation_url

	url = crm_quotation_url(crm_deal, organization)
	business = frappe.db.get_value(DEAL, crm_deal, FIELD)
	company = company_for(business, getdate()) if business else None
	return rules.with_query_value(url, "company", company) if company else url

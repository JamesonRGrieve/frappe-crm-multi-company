# SPDX-License-Identifier: AGPL-3.0-or-later
"""Integration tests on a real site (``bench run-tests --app crm_multi_company``): the install, a website lead
getting its business, a deal taking its lead's business, CRM Business validation, and the quotation link's
company from the business on the day."""

from __future__ import annotations

import secrets
from urllib.parse import unquote

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate

from crm_multi_company import business, install

DEFAULT_COMPANY = "CRMMC Default Co"
OLD_COMPANY = "CRMMC Sole Prop"
NEW_COMPANY = "CRMMC Corp"
COMPANIES = {DEFAULT_COMPANY: "CMD", OLD_COMPANY: "CMS", NEW_COMPANY: "CMC"}
CURRENCY = "CAD"
COUNTRY = "Canada"


def unique(prefix: str) -> str:
	return f"{prefix} {secrets.token_hex(4)}"


def ensure_company(name: str, abbr: str) -> None:
	if not frappe.db.exists("Company", name):
		frappe.get_doc(
			{"doctype": "Company", "company_name": name, "abbr": abbr, "default_currency": CURRENCY, "country": COUNTRY}
		).insert(ignore_permissions=True)


class TestCRMBusiness(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		install.ensure()
		for name, abbr in COMPANIES.items():
			ensure_company(name, abbr)
		settings = frappe.get_single("ERPNext CRM Settings")
		settings.enabled = 1
		settings.is_erpnext_in_different_site = 0
		settings.erpnext_company = DEFAULT_COMPANY
		settings.save(ignore_permissions=True)

	def make_business(self, companies, sites=()):
		return frappe.get_doc(
			{
				"doctype": business.BUSINESS,
				"business_name": unique("Biz"),
				"companies": [{"company": c, "valid_from": f, "valid_to": t} for c, f, t in companies],
				"public_sites": [{"public_site": s} for s in sites],
			}
		).insert(ignore_permissions=True)

	def make_lead(self, **values):
		return frappe.get_doc({"doctype": "CRM Lead", "first_name": unique("Lead"), **values}).insert(
			ignore_permissions=True
		)

	def make_deal(self, **values):
		return frappe.get_doc({"doctype": "CRM Deal", "status": "Qualification", **values}).insert(
			ignore_permissions=True
		)

	def quotation_company(self, deal: str) -> str | None:
		url = business.get_quotation_url(deal)
		params = dict(part.split("=", 1) for part in url.split("?", 1)[1].split("&"))
		return unquote(params["company"]) if "company" in params else None

	def test_install_adds_the_business_field_and_panel_sections(self):
		for doctype in (business.LEAD, business.DEAL):
			self.assertEqual(frappe.get_meta(doctype).get_field(business.FIELD).options, business.BUSINESS)
		install.ensure()  # idempotent: a second run adds nothing
		for panel in install.SIDE_PANELS:
			if frappe.db.exists("CRM Fields Layout", panel):
				layout = frappe.parse_json(frappe.db.get_value("CRM Fields Layout", panel, "layout"))
				self.assertEqual(sum(1 for s in layout if s.get("name") == install.PANEL_SECTION), 1)

	def test_website_lead_gets_its_business(self):
		site = unique("Site")
		biz = self.make_business([(OLD_COMPANY, None, None)], [site])
		lead = self.make_lead(public_site=site)
		self.assertEqual(lead.get(business.FIELD), biz.name)

	def test_lead_keeps_a_business_set_by_hand(self):
		site = unique("Site")
		self.make_business([(OLD_COMPANY, None, None)], [site])
		other = self.make_business([(NEW_COMPANY, None, None)])
		lead = self.make_lead(public_site=site, **{business.FIELD: other.name})
		self.assertEqual(lead.get(business.FIELD), other.name)

	def test_deal_takes_its_leads_business(self):
		site = unique("Site")
		biz = self.make_business([(OLD_COMPANY, None, None)], [site])
		lead = self.make_lead(public_site=site)
		deal = self.make_deal(lead=lead.name)
		self.assertEqual(deal.get(business.FIELD), biz.name)

	def test_overlapping_periods_are_refused(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_business([(OLD_COMPANY, None, "2026-12-31"), (NEW_COMPANY, "2026-12-31", None)])

	def test_backwards_period_is_refused(self):
		with self.assertRaises(frappe.ValidationError):
			self.make_business([(OLD_COMPANY, "2027-01-01", "2026-01-01")])

	def test_a_site_belongs_to_one_business(self):
		site = unique("Site")
		self.make_business([(OLD_COMPANY, None, None)], [site])
		with self.assertRaises(frappe.ValidationError):
			self.make_business([(NEW_COMPANY, None, None)], [site])

	def test_quotation_uses_the_company_for_today(self):
		today = getdate()
		biz = self.make_business(
			[(OLD_COMPANY, None, add_days(today, -1)), (NEW_COMPANY, today, None)],
		)
		deal = self.make_deal(**{business.FIELD: biz.name})
		self.assertEqual(self.quotation_company(deal.name), NEW_COMPANY)

	def test_quotation_before_the_cutover_uses_the_old_company(self):
		today = getdate()
		biz = self.make_business(
			[(OLD_COMPANY, None, add_days(today, 30)), (NEW_COMPANY, add_days(today, 31), None)],
		)
		deal = self.make_deal(**{business.FIELD: biz.name})
		self.assertEqual(self.quotation_company(deal.name), OLD_COMPANY)

	def test_quotation_without_a_business_keeps_crms_default(self):
		deal = self.make_deal()
		self.assertEqual(self.quotation_company(deal.name), DEFAULT_COMPANY)

	def test_quotation_in_a_gap_keeps_crms_default(self):
		biz = self.make_business([(OLD_COMPANY, add_days(getdate(), 10), None)])
		deal = self.make_deal(**{business.FIELD: biz.name})
		self.assertEqual(self.quotation_company(deal.name), DEFAULT_COMPANY)

	def test_crms_whitelisted_method_is_overridden(self):
		overrides = frappe.get_hooks("override_whitelisted_methods")
		key = "crm.fcrm.doctype.erpnext_crm_settings.erpnext_crm_settings.get_quotation_url"
		self.assertEqual(overrides[key][-1], "crm_multi_company.business.get_quotation_url")

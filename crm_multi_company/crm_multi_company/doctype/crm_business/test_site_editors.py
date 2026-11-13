# SPDX-License-Identifier: AGPL-3.0-or-later
"""Site Editors on a real site: an editor listed on one business's Public Site sees that business's leads, deals and
their tasks and notes, and nothing of another business or of leads with no business; a Sales Manager who isn't a
scoped Site Editor still sees every lead."""

from __future__ import annotations

import secrets

import frappe
from frappe.tests import IntegrationTestCase
from public_site_router import site_editors as router_editors

from crm_multi_company import business, install

EDITOR = "cmc-site-editor@cmc.test"
MANAGER = "cmc-sales-manager@cmc.test"


def unique(prefix: str) -> str:
	return f"{prefix} {secrets.token_hex(4)}"


def make_user(email: str, roles: list[str]) -> None:
	if not frappe.db.exists("User", email):
		frappe.get_doc(
			{"doctype": "User", "email": email, "first_name": email.split("@")[0], "send_welcome_email": 0}
		).insert(ignore_permissions=True)
	user = frappe.get_doc("User", email)
	user.set("roles", [])
	user.add_roles(*roles)


def make_site(prefix: str, editors: list[str]) -> str:
	name = unique("Site")
	frappe.get_doc(
		{
			"doctype": "Public Site",
			"site_name": name,
			"enabled": 1,
			"route_prefix": f"{prefix}-{secrets.token_hex(3)}",
			"home_route": "home",
			"domains": [{"domain": f"{secrets.token_hex(4)}.cmc.test"}],
			"editors": [{"user": u} for u in editors],
		}
	).insert(ignore_permissions=True)
	return name


def as_user(user: str) -> None:
	frappe.set_user(user)
	router_editors.clear_scope_cache()


class TestSiteEditorLeads(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		install.ensure()
		router_editors.ensure_role()
		make_user(EDITOR, ["Site Editor", "Sales Manager"])
		make_user(MANAGER, ["Sales Manager"])

	def setUp(self):
		frappe.set_user("Administrator")
		own_site = make_site("own", [EDITOR])
		other_site = make_site("other", [])
		self.own_business = self.make_business(own_site)
		self.other_business = self.make_business(other_site)
		self.own_lead = self.make_lead(business.FIELD, self.own_business)
		self.other_lead = self.make_lead(business.FIELD, self.other_business)
		self.loose_lead = self.make_lead(business.FIELD, None)
		self.own_note = self.make_note(self.own_lead)
		self.other_note = self.make_note(self.other_lead)
		router_editors.clear_scope_cache()

	def tearDown(self):
		frappe.set_user("Administrator")
		router_editors.clear_scope_cache()

	def make_business(self, site: str) -> str:
		return (
			frappe.get_doc(
				{"doctype": business.BUSINESS, "business_name": unique("Biz"), "public_sites": [{"public_site": site}]}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def make_lead(self, field: str, value: str | None) -> str:
		return (
			frappe.get_doc({"doctype": business.LEAD, "first_name": unique("Lead"), field: value})
			.insert(ignore_permissions=True)
			.name
		)

	def make_note(self, lead: str) -> str:
		return (
			frappe.get_doc(
				{
					"doctype": "FCRM Note",
					"title": unique("Note"),
					"reference_doctype": business.LEAD,
					"reference_docname": lead,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def test_editor_lists_only_own_business_leads(self):
		as_user(EDITOR)
		names = set(frappe.get_list(business.LEAD, pluck="name"))
		self.assertIn(self.own_lead, names)
		self.assertNotIn(self.other_lead, names)
		self.assertNotIn(self.loose_lead, names)

	def test_editor_cannot_open_another_business_lead(self):
		as_user(EDITOR)
		self.assertTrue(frappe.has_permission(business.LEAD, "read", self.own_lead))
		self.assertFalse(frappe.has_permission(business.LEAD, "read", self.other_lead))
		self.assertFalse(frappe.has_permission(business.LEAD, "read", self.loose_lead))

	def test_notes_follow_their_lead(self):
		as_user(EDITOR)
		names = set(frappe.get_list("FCRM Note", pluck="name"))
		self.assertIn(self.own_note, names)
		self.assertNotIn(self.other_note, names)
		self.assertFalse(frappe.has_permission("FCRM Note", "read", self.other_note))

	def test_deals_by_business(self):
		own = frappe.get_doc({"doctype": business.DEAL, "status": "Qualification", "lead": self.own_lead}).insert(
			ignore_permissions=True
		)
		other = frappe.get_doc({"doctype": business.DEAL, "status": "Qualification", "lead": self.other_lead}).insert(
			ignore_permissions=True
		)
		as_user(EDITOR)
		names = set(frappe.get_list(business.DEAL, pluck="name"))
		self.assertIn(own.name, names)
		self.assertNotIn(other.name, names)

	def test_sales_manager_who_is_not_a_site_editor_sees_every_lead(self):
		as_user(MANAGER)
		names = set(frappe.get_list(business.LEAD, pluck="name"))
		self.assertTrue({self.own_lead, self.other_lead, self.loose_lead} <= names)

# SPDX-License-Identifier: AGPL-3.0-or-later
"""Site Editors (public_site_router) see only the CRM records of their own sites' businesses.

A Site Editor listed on a Public Site edits only that site in Builder (``public_site_router.site_editors``). Here the
same scope narrows the CRM: a lead or deal is theirs when its business (``crm_business``) has one of their sites,
and a task, note or call log when the lead or deal it belongs to is. A lead with no business belongs to no site, so a
Site Editor never sees it. Frappe ANDs these with CRM's own hooks (a Sales User still sees only their own or assigned
leads); users who aren't scoped Site Editors are untouched.
"""

from __future__ import annotations

from typing import Any

import frappe

from crm_multi_company import rules
from crm_multi_company.business import BUSINESS, BUSINESS_SITE, DEAL, FIELD, LEAD


def _scope(user: str | None) -> Any:
	from public_site_router.site_editors import scope_for

	return scope_for(user)


def businesses(user: str | None = None) -> list[str] | None:
	"""The businesses whose records a scoped Site Editor sees, or None when the user isn't scoped."""
	scope = _scope(user)
	if scope is None:
		return None
	sites = [site.name for site in scope.sites]
	if not sites:
		return []
	return frappe.get_all(
		BUSINESS_SITE, filters={"parenttype": BUSINESS, "public_site": ["in", sites]}, pluck="parent", distinct=True
	)


def _conditions(user: str | None, build: Any) -> str:
	allowed = businesses(user)
	return "" if allowed is None else build(allowed)


def lead_conditions(user: str | None = None, doctype: str | None = None) -> str:
	return _conditions(user, lambda b: rules.business_condition(f"`tab{LEAD}`.`{FIELD}`", b, frappe.db.escape))


def deal_conditions(user: str | None = None, doctype: str | None = None) -> str:
	return _conditions(user, lambda b: rules.business_condition(f"`tab{DEAL}`.`{FIELD}`", b, frappe.db.escape))


def reference_conditions(user: str | None = None, doctype: str | None = None) -> str:
	return _conditions(
		user, lambda b: rules.reference_condition(f"`tab{doctype}`", LEAD, DEAL, FIELD, b, frappe.db.escape)
	)


def record_permission(doc: Any, ptype: str | None = None, user: str | None = None, **_kwargs: Any) -> bool:
	"""A lead or deal of one of the editor's businesses."""
	allowed = businesses(user)
	return allowed is None or doc.get(FIELD) in allowed


def reference_permission(doc: Any, ptype: str | None = None, user: str | None = None, **_kwargs: Any) -> bool:
	"""A task, note or call log of a lead or deal of one of the editor's businesses."""
	allowed = businesses(user)
	if allowed is None:
		return True
	if doc.get("reference_doctype") not in (LEAD, DEAL) or not doc.get("reference_docname"):
		return False
	return frappe.db.get_value(doc.reference_doctype, doc.reference_docname, FIELD) in allowed

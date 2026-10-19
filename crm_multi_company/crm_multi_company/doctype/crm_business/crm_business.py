# SPDX-License-Identifier: AGPL-3.0-or-later
import frappe
from frappe import _
from frappe.model.document import Document

from crm_multi_company import business, rules


class CRMBusiness(Document):
	def validate(self) -> None:
		self.validate_periods()
		self.validate_sites()

	def validate_periods(self) -> None:
		periods = business.periods_of(self)
		for period in rules.backwards_periods(periods):
			frappe.throw(_("{0}: Valid From is after Valid To").format(period.company))
		for first, second in rules.overlapping_periods(periods):
			frappe.throw(
				_("{0} and {1} overlap: the business can bill under only one company on any date").format(
					first.company, second.company
				)
			)

	def validate_sites(self) -> None:
		own = [row.public_site for row in self.public_sites]
		if len(own) != len(set(own)):
			frappe.throw(_("A Public Site is listed twice"))
		others = frappe.get_all(
			business.BUSINESS_SITE,
			filters={"parenttype": business.BUSINESS, "parent": ["!=", self.name], "public_site": ["in", own or [""]]},
			fields=["parent", "public_site"],
		)
		claims = [(self.name, site) for site in own] + [(o.parent, o.public_site) for o in others]
		for site, owners in rules.contested_sites(claims).items():
			frappe.throw(_("{0} already belongs to {1}").format(site, ", ".join(sorted(owners - {self.name}))))

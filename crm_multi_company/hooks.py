# SPDX-License-Identifier: AGPL-3.0-or-later
from . import __version__ as _version

app_name = "crm_multi_company"
app_title = "CRM Multi Company"
app_publisher = "Zephyrex Technologies Limited"
app_description = "Several businesses in one Frappe CRM: each lead and deal belongs to a business, and quotations go out under the company that business bills under on the day"
app_email = "jameson@zephyrex.ca"
app_license = "AGPL-3.0-or-later"
app_version = _version

# CRM for leads and deals; ERPNext for Company and Quotation; the Public Site router for a business's sites and
# their Site Editors.
required_apps = ["frappe", "erpnext", "crm", "public_site_router"]

# The Business field on leads and deals, and its CRM side-panel section (idempotent).
after_install = "crm_multi_company.install.after_install"
after_migrate = ["crm_multi_company.install.after_migrate"]

doc_events = {
	"CRM Lead": {"validate": "crm_multi_company.business.set_lead_business"},
	"CRM Deal": {"validate": "crm_multi_company.business.set_deal_business"},
}

# CRM's Create Quotation button: the company comes from the deal's business instead of the one company in
# ERPNext CRM Settings.
override_whitelisted_methods = {
	"crm.fcrm.doctype.erpnext_crm_settings.erpnext_crm_settings.get_quotation_url": "crm_multi_company.business.get_quotation_url",
}

# Site Editors (public_site_router) see only the leads, deals and their tasks, notes and call logs of their own
# sites' businesses; ANDed with CRM's own hooks.
permission_query_conditions = {
	"CRM Lead": "crm_multi_company.site_editors.lead_conditions",
	"CRM Deal": "crm_multi_company.site_editors.deal_conditions",
	"CRM Task": "crm_multi_company.site_editors.reference_conditions",
	"FCRM Note": "crm_multi_company.site_editors.reference_conditions",
	"CRM Call Log": "crm_multi_company.site_editors.reference_conditions",
}
has_permission = {
	"CRM Lead": "crm_multi_company.site_editors.record_permission",
	"CRM Deal": "crm_multi_company.site_editors.record_permission",
	"CRM Task": "crm_multi_company.site_editors.reference_permission",
	"FCRM Note": "crm_multi_company.site_editors.reference_permission",
	"CRM Call Log": "crm_multi_company.site_editors.reference_permission",
}

# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for the pure rules (no bench): dated company periods, the overlap and order checks, contested
public sites, and setting the company on a quotation URL."""

from datetime import date

from crm_multi_company.rules import (
	CompanyPeriod,
	backwards_periods,
	company_on,
	contested_sites,
	overlapping_periods,
	with_query_value,
)

SOLE_PROP = CompanyPeriod("Jameson Grieve", None, date(2026, 12, 31))
CORP = CompanyPeriod("3S Hub Inc", date(2027, 1, 1), None)


def test_company_on_switches_at_the_cutover():
	periods = [SOLE_PROP, CORP]
	assert company_on(periods, date(2026, 12, 31)) == "Jameson Grieve"
	assert company_on(periods, date(2027, 1, 1)) == "3S Hub Inc"
	assert company_on(periods, date(2020, 5, 1)) == "Jameson Grieve"
	assert company_on(periods, date(2030, 5, 1)) == "3S Hub Inc"


def test_company_on_returns_none_in_a_gap():
	periods = [CompanyPeriod("A", date(2026, 1, 1), date(2026, 6, 30)), CompanyPeriod("B", date(2026, 8, 1), None)]
	assert company_on(periods, date(2026, 7, 15)) is None
	assert company_on([], date(2026, 7, 15)) is None


def test_an_open_period_covers_every_date():
	assert company_on([CompanyPeriod("Always")], date(1999, 1, 1)) == "Always"


def test_adjacent_periods_do_not_overlap():
	assert overlapping_periods([SOLE_PROP, CORP]) == []


def test_sharing_one_day_overlaps():
	a = CompanyPeriod("A", None, date(2027, 1, 1))
	assert overlapping_periods([a, CORP]) == [(a, CORP)]


def test_two_open_periods_overlap():
	a, b = CompanyPeriod("A"), CompanyPeriod("B", date(2030, 1, 1))
	assert overlapping_periods([a, b]) == [(a, b)]


def test_backwards_period_is_reported():
	bad = CompanyPeriod("A", date(2027, 1, 1), date(2026, 1, 1))
	assert backwards_periods([SOLE_PROP, bad]) == [bad]
	assert not SOLE_PROP.is_backwards()


def test_contested_sites_lists_only_shared_sites():
	claims = [("3S Hub", "3S Hub Store"), ("3S Hub", "3S Hub Blog"), ("Zephyrex", "3S Hub Blog")]
	assert contested_sites(claims) == {"3S Hub Blog": {"3S Hub", "Zephyrex"}}
	assert contested_sites([("3S Hub", "3S Hub Store")]) == {}


def test_with_query_value_replaces_the_company():
	url = "https://erp.example/app/quotation/new?quotation_to=CRM Deal&company=Jameson Grieve&crm_deal=CRM-DEAL-1"
	assert with_query_value(url, "company", "3S Hub Inc") == (
		"https://erp.example/app/quotation/new?quotation_to=CRM Deal&crm_deal=CRM-DEAL-1&company=3S%20Hub%20Inc"
	)


def test_with_query_value_appends_when_missing():
	assert with_query_value("https://x/new?a=1", "company", "B&C") == "https://x/new?a=1&company=B%26C"
	assert with_query_value("https://x/new", "company", "B") == "https://x/new?company=B"


def test_with_query_value_does_not_touch_a_similar_key():
	assert with_query_value("https://x/new?company_name=X", "company", "B") == "https://x/new?company_name=X&company=B"

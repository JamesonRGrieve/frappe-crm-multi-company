# SPDX-License-Identifier: AGPL-3.0-or-later
"""Which company a business bills under on a date, and the checks that keep a business's periods unambiguous.

Pure: no Frappe import, unit-tested in tests/. A business bills under one company per day; its periods are
inclusive date ranges, open at either end when a bound is missing.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from urllib.parse import quote


@dataclass(frozen=True)
class CompanyPeriod:
	company: str
	valid_from: date | None = None
	valid_to: date | None = None

	def covers(self, on: date) -> bool:
		return (self.valid_from is None or self.valid_from <= on) and (self.valid_to is None or on <= self.valid_to)

	def is_backwards(self) -> bool:
		return self.valid_from is not None and self.valid_to is not None and self.valid_from > self.valid_to

	def overlaps(self, other: CompanyPeriod) -> bool:
		starts_before_other_ends = (
			self.valid_from is None or other.valid_to is None or self.valid_from <= other.valid_to
		)
		ends_after_other_starts = self.valid_to is None or other.valid_from is None or other.valid_from <= self.valid_to
		return starts_before_other_ends and ends_after_other_starts


def company_on(periods: list[CompanyPeriod], on: date) -> str | None:
	"""The company whose period covers the date, or None when no period does."""
	return next((p.company for p in periods if p.covers(on)), None)


def backwards_periods(periods: list[CompanyPeriod]) -> list[CompanyPeriod]:
	return [p for p in periods if p.is_backwards()]


def overlapping_periods(periods: list[CompanyPeriod]) -> list[tuple[CompanyPeriod, CompanyPeriod]]:
	"""Every pair of periods sharing a day: a business can bill under only one company on any date."""
	return [(a, b) for i, a in enumerate(periods) for b in periods[i + 1 :] if a.overlaps(b)]


def contested_sites(claims: list[tuple[str, str]]) -> dict[str, set[str]]:
	"""Public sites claimed by more than one business, from (business, site) pairs."""
	owners: dict[str, set[str]] = {}
	for business, site in claims:
		owners.setdefault(site, set()).add(business)
	return {site: businesses for site, businesses in owners.items() if len(businesses) > 1}


def with_query_value(url: str, key: str, value: str) -> str:
	"""The URL with one query parameter set (replaced if present, appended if not), the value URL-encoded."""
	base, _, query = url.partition("?")
	pairs = [part for part in query.split("&") if part and part.split("=", 1)[0] != key]
	pairs.append(f"{key}={quote(value)}")
	return f"{base}?{'&'.join(pairs)}"


def business_condition(column: str, businesses: list[str], quote: Callable[[str], str]) -> str:
	"""SQL limiting ``column`` (a business link) to ``businesses``; nothing at all when there are none."""
	if not businesses:
		return "1=0"
	return f"{column} in ({', '.join(quote(b) for b in businesses)})"


def reference_condition(
	table: str, lead: str, deal: str, field: str, businesses: list[str], quote: Callable[[str], str]
) -> str:
	"""SQL limiting a referencing doctype's rows to those of leads or deals of ``businesses``."""
	if not businesses:
		return "1=0"
	inside = ", ".join(quote(b) for b in businesses)
	return (
		f"(({table}.reference_doctype = {quote(lead)} and {table}.reference_docname in"
		f" (select name from `tab{lead}` where `{field}` in ({inside})))"
		f" or ({table}.reference_doctype = {quote(deal)} and {table}.reference_docname in"
		f" (select name from `tab{deal}` where `{field}` in ({inside}))))"
	)

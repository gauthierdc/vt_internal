# Copyright (c) 2026, Verre & Transparence and contributors
# For license information, please see license.txt

"""CA facturé, variation « n.s. » et marge de sélection — sans site Frappe."""

from __future__ import annotations

import unittest
from pathlib import Path

from vt_internal.vt_internal.utils.ca_facture import (
	aggregate_margin,
	ca_facture_predicate,
	period_variation,
)


class TestCaFacturePredicate(unittest.TestCase):
	def test_ht_submitted_excludes_down_payments_only(self):
		sql = ca_facture_predicate()
		self.assertIn("si.docstatus = 1", sql)
		self.assertIn("is_down_payment_invoice", sql)
		# Avoirs included: their negative total nets the CA. No hours gate.
		self.assertNotIn("is_return", sql)
		self.assertNotIn("custom_estimated_labor_hours", sql)

	def test_call_sites_share_the_predicate(self):
		pkg = Path(__file__).resolve().parents[1]
		api = (pkg / "api" / "chantiers.py").read_text(encoding="utf-8")
		report = (pkg / "report" / "👷chantiers" / "👷chantiers.py").read_text(encoding="utf-8")
		self.assertIn("ca_facture_predicate()", api)
		self.assertIn("ca_facture_conditions()", report)
		# Every CA sum uses the shared predicate. The hours gate may remain
		# on the billed-hours ratio and the dropped-off chantier detector.
		ca_selects = [
			block.split("GROUP BY", 1)[0]
			for block in api.split("SELECT")
			if "SUM(si.total)" in block.split("FROM", 1)[0]
		]
		self.assertEqual(len(ca_selects), 4)
		for block in ca_selects:
			self.assertIn("{ca_where}", block)
			self.assertNotIn("is_return", block)
			self.assertNotIn("custom_estimated_labor_hours", block)
		self.assertNotIn(
			'"p.custom_estimated_labor_hours > 1"',
			report.split("heures_facturees_where", 1)[0],
		)


class TestPeriodVariation(unittest.TestCase):
	def test_nearly_empty_base_is_not_significant(self):
		# Prior CA ~1 k€ vs 178 k€ (cost center created mid prior window).
		result = period_variation(178_000, 1_000)
		self.assertTrue(result["insignificant"])
		self.assertEqual(result["delta_text"], "n.s.")
		self.assertIsNone(result["delta"])

	def test_zero_base_is_not_significant(self):
		result = period_variation(96_000, 0)
		self.assertEqual(result["delta_text"], "n.s.")

	def test_comparable_base_shows_percent(self):
		result = period_variation(178_000, 90_000)
		self.assertFalse(result["insignificant"])
		self.assertEqual(result["delta"], 98)
		self.assertEqual(result["delta_text"], "▲ +98%")
		self.assertEqual(result["delta_class"], "good")

	def test_drop_is_bad_unless_inverted(self):
		down = period_variation(100, 200)
		self.assertEqual(down["delta_text"], "▼ -50%")
		self.assertEqual(down["delta_class"], "bad")
		costs = period_variation(100, 200, invert=True)
		self.assertEqual(costs["delta_class"], "good")

	def test_flat_and_empty(self):
		self.assertEqual(period_variation(10, 10)["delta_text"], "= 0%")
		self.assertEqual(period_variation(0, 0)["delta_text"], "")
		self.assertEqual(period_variation(10, None)["delta_text"], "")

	def test_boundary_at_five_percent_still_shows_percent(self):
		# Exactly 5 % of current is not "under" the threshold.
		result = period_variation(100_000, 5_000)
		self.assertFalse(result["insignificant"])
		self.assertEqual(result["delta"], 1900)


class TestAggregateMargin(unittest.TestCase):
	def test_weighted_by_sales_not_by_row_count(self):
		rows = [
			{"vente": 100, "cout_reel": 90},  # 10 %
			{"vente": 900, "cout_reel": 450},  # 50 %
		]
		result = aggregate_margin(rows)
		# (1000 - 540) / 1000 = 46 %, not the 30 % average of the two rates.
		self.assertEqual(result["pct"], 46)
		self.assertEqual(result["eur"], 460)

	def test_no_sales_has_no_rate(self):
		result = aggregate_margin([{"vente": 0, "cout_reel": 40}, {}])
		self.assertIsNone(result["pct"])
		self.assertEqual(result["eur"], -40)


if __name__ == "__main__":
	unittest.main()

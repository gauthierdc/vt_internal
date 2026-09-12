# Copyright (c) 2026, Verre & Transparence and contributors
# Tests unitaires de la vente/coût théoriques (sans site Frappe).

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

if "frappe" not in sys.modules:
	sys.modules["frappe"] = MagicMock()

_MODULE_PATH = Path(__file__).with_name("margin_utils.py")
_SPEC = importlib.util.spec_from_file_location("vt_margin_utils", _MODULE_PATH)
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)

compute_theoretical = _MOD.compute_theoretical
get_theoretical = _MOD.get_theoretical
get_theoretical_map = _MOD.get_theoretical_map
calculate_margin = _MOD.calculate_margin

# CC-2607-025-like: parent Menuiserie sells for 2300.73€, packed qty×rate ~7623€,
# plus non-bundle lines 556.96€ → SO total 2857.69€. Old get_theoretical
# excluded the parent then added packed rates → ~8180€.
CC_2607_025_SOI = [
	{
		"name": "soi-menuiserie",
		"project": "CC-2604-526-258055",
		"amount": 2300.73,
		"qty": 1,
		"base_unit_cost_price": 1800.0,
		"product_bundle_name": "Menuiserie",
		"custom_pose_vt": 0,
	},
	{
		"name": "soi-pose",
		"project": "CC-2604-526-258055",
		"amount": 400.00,
		"qty": 8,
		"base_unit_cost_price": 25.0,
		"product_bundle_name": "",
		"custom_pose_vt": 1,
	},
	{
		"name": "soi-achat",
		"project": "CC-2604-526-258055",
		"amount": 156.96,
		"qty": 1,
		"base_unit_cost_price": 80.0,
		"product_bundle_name": "",
		"custom_pose_vt": 0,
	},
]
CC_2607_025_PACKED = [
	{
		"project": "CC-2604-526-258055",
		"parent_detail_docname": "soi-menuiserie",
		"qty": 2,
		"rate": 2000.0,
		"base_unit_cost_price": 400.0,
		"custom_pose_vt": 0,
	},
	{
		"project": "CC-2604-526-258055",
		"parent_detail_docname": "soi-menuiserie",
		"qty": 3,
		"rate": 1207.67,
		"base_unit_cost_price": 150.0,
		"custom_pose_vt": 1,
	},
]
SO_TOTAL = 2857.69
PACKED_RATE_SUM = 2 * 2000.0 + 3 * 1207.67  # 7623.01
BUGGY_VENTE = 400.00 + 156.96 + PACKED_RATE_SUM  # ~8179.97


class TestComputeTheoreticalBundleVente(unittest.TestCase):
	def test_vente_uses_bundle_parent_amount_not_packed_rates(self):
		vente, _cost = compute_theoretical(CC_2607_025_SOI, CC_2607_025_PACKED, "global")
		self.assertAlmostEqual(vente, SO_TOTAL, places=2)
		self.assertNotAlmostEqual(vente, BUGGY_VENTE, places=2)
		self.assertLess(vente, PACKED_RATE_SUM)

	def test_packed_sell_rates_are_ignored_even_when_larger_than_parent(self):
		soi = [
			{
				"name": "soi-bundle",
				"amount": 100.0,
				"qty": 1,
				"base_unit_cost_price": 40.0,
				"product_bundle_name": "Bundle",
				"custom_pose_vt": 0,
			}
		]
		packed = [
			{
				"parent_detail_docname": "soi-bundle",
				"qty": 10,
				"rate": 50.0,
				"base_unit_cost_price": 3.0,
				"custom_pose_vt": 0,
			}
		]
		vente, cost = compute_theoretical(soi, packed, "global")
		self.assertAlmostEqual(vente, 100.0)
		self.assertAlmostEqual(cost, 30.0)

	def test_cost_uses_packed_unit_cost_not_parent_and_not_packed_rate(self):
		_vente, cost = compute_theoretical(CC_2607_025_SOI, CC_2607_025_PACKED, "global")
		# packed 2×400 + 3×150 = 1250; pose 8×25 = 200; achat 1×80 = 80
		self.assertAlmostEqual(cost, 1530.0)
		# parent 1800 must not be added on top of packed costs
		self.assertNotAlmostEqual(cost, 1530.0 + 1800.0)

	def test_fallback_to_parent_cost_when_packed_costs_are_zero(self):
		packed = [
			{
				"parent_detail_docname": "soi-menuiserie",
				"qty": 2,
				"rate": 2000.0,
				"base_unit_cost_price": 0,
				"custom_pose_vt": 0,
			}
		]
		_vente, cost = compute_theoretical(
			[CC_2607_025_SOI[0]],
			packed,
			"global",
		)
		self.assertAlmostEqual(cost, 1800.0)

	def test_axis_filters_use_item_flags_on_relevant_lines(self):
		vente_tp, cost_tp = compute_theoretical(
			CC_2607_025_SOI, CC_2607_025_PACKED, "Temps passé"
		)
		vente_ach, cost_ach = compute_theoretical(
			CC_2607_025_SOI, CC_2607_025_PACKED, "Achats"
		)
		# Vente: parent bundle + non-bundle SOI flags (not packed children)
		self.assertAlmostEqual(vente_tp, 400.00)
		self.assertAlmostEqual(vente_ach, 2300.73 + 156.96)
		# Cost: packed children flags for the bundle + non-bundle SOI flags
		self.assertAlmostEqual(cost_tp, 3 * 150.0 + 8 * 25.0)
		self.assertAlmostEqual(cost_ach, 2 * 400.0 + 80.0)
		self.assertAlmostEqual(vente_tp + vente_ach, SO_TOTAL, places=2)

	def test_empty_inputs(self):
		self.assertEqual(compute_theoretical([], [], "global"), (0.0, 0.0))
		self.assertEqual(compute_theoretical(None, None, "Achats"), (0.0, 0.0))


class TestGetTheoreticalWiring(unittest.TestCase):
	def tearDown(self):
		_MOD.frappe.db.sql.reset_mock()

	def test_get_theoretical_reads_soi_and_packed_then_uses_parent_amount(self):
		_MOD.frappe.db.sql.side_effect = [CC_2607_025_SOI, CC_2607_025_PACKED]
		vente, cost = get_theoretical("CC-2604-526-258055", "global")
		self.assertAlmostEqual(vente, SO_TOTAL, places=2)
		self.assertAlmostEqual(cost, 1530.0)
		self.assertEqual(_MOD.frappe.db.sql.call_count, 2)
		soi_sql = _MOD.frappe.db.sql.call_args_list[0][0][0]
		packed_sql = _MOD.frappe.db.sql.call_args_list[1][0][0]
		self.assertIn("tabSales Order Item", soi_sql)
		self.assertNotIn("product_bundle_name", soi_sql.split("WHERE", 1)[1])
		self.assertIn("tabPacked Item", packed_sql)
		self.assertNotIn("pi.qty * pi.rate", packed_sql)

	def test_get_theoretical_map_groups_by_project(self):
		other_soi = [
			{
				"name": "soi-other",
				"project": "PRJ-OTHER",
				"amount": 50.0,
				"qty": 1,
				"base_unit_cost_price": 10.0,
				"product_bundle_name": "",
				"custom_pose_vt": 0,
			}
		]
		_MOD.frappe.db.sql.side_effect = [
			CC_2607_025_SOI + other_soi,
			CC_2607_025_PACKED,
		]
		result = get_theoretical_map(["CC-2604-526-258055", "PRJ-OTHER"])
		self.assertAlmostEqual(result["CC-2604-526-258055"][0], SO_TOTAL, places=2)
		self.assertAlmostEqual(result["PRJ-OTHER"], (50.0, 10.0))


class TestCalculateMargin(unittest.TestCase):
	def test_margin_and_zero_vente(self):
		self.assertAlmostEqual(calculate_margin(100, 40), 60.0)
		self.assertEqual(calculate_margin(0, 10), 0)
		self.assertEqual(calculate_margin(None, 10), 0)


if __name__ == "__main__":
	unittest.main()

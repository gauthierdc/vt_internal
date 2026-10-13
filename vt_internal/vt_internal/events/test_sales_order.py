# Copyright (c) 2026, Verre & Transparence and contributors
# Heures théoriques de la commande client (sans site Frappe).

import sys
import types
import unittest
from unittest.mock import MagicMock

if "frappe" not in sys.modules:
	sys.modules["frappe"] = MagicMock()

from vt_internal.vt_internal.events import sales_order as sales_order_events
from vt_internal.vt_internal.events.sales_order import before_update_after_submit, validate

# CC-2511-426 : custom_labour_hours stocké avec le bruit flottant des quantités.
CC_2511_426_HOURS = 1910.055555565


class _Line:
	def __init__(self, item_code, qty, row_print_style="", row_type=""):
		self.item_code = item_code
		self.qty = qty
		self.row_print_style = row_print_style
		self.row_type = row_type
		self.project = None
		self.cost_center = "CC-SFML"


class _Doc:
	def __init__(self, items, packed, labour_hours=0):
		self.flags = types.SimpleNamespace()
		self.grand_total = 1000
		self.advance_paid = 0
		self.items = items
		self.packed_items = packed
		self.project = None
		self.cost_center = "CC-SFML"
		self.custom_labour_hours = labour_hours


def _pose_catalog(catalog):
	def get_value(doctype, name, fieldname):
		pose, hours = catalog[name]
		if fieldname == "custom_pose_vt":
			return pose
		if fieldname == "custom_number_of_labor_hours":
			return hours
		raise AssertionError(fieldname)

	return get_value


class TestSalesOrderLabourHours(unittest.TestCase):
	def setUp(self):
		self._get_value = sales_order_events.frappe.db.get_value

	def tearDown(self):
		sales_order_events.frappe.db.get_value = self._get_value

	def test_validate_rounds_cc_2511_426_to_two_decimals(self):
		# Correction manuelle : le hook la réécrit, mais avec la valeur arrondie.
		sales_order_events.frappe.db.get_value = _pose_catalog({"POSE": (1, 1)})
		doc = _Doc([_Line("POSE", CC_2511_426_HOURS)], [], labour_hours=1910.06)

		validate(doc)

		self.assertEqual(doc.custom_labour_hours, 1910.06)
		self.assertNotEqual(doc.custom_labour_hours, CC_2511_426_HOURS)

	def test_noisy_quantities_sum_pose_lines_and_packed_items_only(self):
		sales_order_events.frappe.db.get_value = _pose_catalog({
			"POSE": (1, 10),
			"VERRE": (0, 99),
			"POSE-PACK": (1, 20),
			"PACK-HORS-POSE": (0, 8),
		})
		doc = _Doc(
			[
				_Line("POSE", 33.944444434),
				_Line("VERRE", 100),
			],
			[
				_Line("POSE-PACK", 26.111111132),
				_Line("PACK-HORS-POSE", 5),
			],
			labour_hours=1,
		)

		validate(doc)

		# 33.944444434×10 + 26.111111132×20 = 861.66666698 → 861.67
		self.assertEqual(doc.custom_labour_hours, 861.67)

	def test_submitted_save_overwrites_manual_value_with_rounded_sum(self):
		sales_order_events.frappe.db.get_value = _pose_catalog({"POSE": (1, 1)})
		doc = _Doc([_Line("POSE", CC_2511_426_HOURS)], [], labour_hours=1900)

		before_update_after_submit(doc)

		self.assertEqual(doc.custom_labour_hours, 1910.06)

# Copyright (c) 2026, Verre & Transparence and contributors
# Arrondi des heures théoriques du panneau projet (sans site Frappe).

import sys
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock

if "frappe" not in sys.modules:
	sys.modules["frappe"] = MagicMock()

from vt_internal.vt_internal.api.project_details import round_labour_hours_and_diff

# STARIMMO-320540 : CC-2511-426 (1910.055555565 h) + autre commande (360 h).
# Le temps réel est déjà arrondi à 2 décimales (226.50 h).
STARIMMO_ORDERS = (
	SimpleNamespace(custom_labour_hours=1910.055555565),
	SimpleNamespace(custom_labour_hours=360),
)
STARIMMO_TIME_SPENT = 226.5


class TestProjectLabourHoursDisplay(unittest.TestCase):
	def test_starimmo_theoretical_hours_and_diff_are_rounded(self):
		labour_hours, diff_time = round_labour_hours_and_diff(STARIMMO_ORDERS, STARIMMO_TIME_SPENT)

		self.assertEqual(labour_hours, 2270.06)
		self.assertEqual(diff_time, -2043.56)
		self.assertEqual(f"{labour_hours} h", "2270.06 h")
		self.assertEqual(f"{diff_time} h", "-2043.56 h")

	def test_diff_does_not_keep_binary_noise(self):
		orders = (SimpleNamespace(custom_labour_hours=0.1),)
		labour_hours, diff_time = round_labour_hours_and_diff(orders, 0.3)

		self.assertEqual(labour_hours, 0.1)
		self.assertEqual(diff_time, 0.2)
		self.assertNotEqual(0.3 - 0.1, 0.2)

	def test_missing_labour_hours_count_as_zero(self):
		orders = (
			SimpleNamespace(custom_labour_hours=None),
			SimpleNamespace(custom_labour_hours=1.234),
		)
		labour_hours, diff_time = round_labour_hours_and_diff(orders, 0)

		self.assertEqual(labour_hours, 1.23)
		self.assertEqual(diff_time, -1.23)

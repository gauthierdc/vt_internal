# Copyright (c) 2026, Verre & Transparence and contributors
# For license information, please see license.txt

"""Définition unique du « CA facturé » de la vue Chantiers (sans site Frappe).

On exécute réellement `CA_AMOUNT` / `CA_WHERE` sur une table SQLite en mémoire
qui reproduit les colonnes utiles de `tabSales Invoice` : facture, avoir,
facture d'acompte, brouillon, annulée."""

import importlib.util
import sqlite3
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock

if "frappe" not in sys.modules:
	sys.modules["frappe"] = MagicMock()

_MARGIN_MOD = "vt_internal.vt_internal.utils.margin_utils"
if _MARGIN_MOD not in sys.modules:
	try:
		importlib.import_module(_MARGIN_MOD)
	except ImportError:
		stub = types.ModuleType(_MARGIN_MOD)
		stub.calculate_margin = stub.get_real_cost_map = stub.get_theoretical_map = MagicMock()
		sys.modules[_MARGIN_MOD] = stub

_SPEC = importlib.util.spec_from_file_location("vt_chantiers", Path(__file__).with_name("chantiers.py"))
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)

# (name, project, docstatus, is_return, is_down_payment_invoice, total, net_total)
INVOICES = [
	("SI-1", "P1", 1, 0, 0, 1100.0, 1000.0),  # facture validée, remise de 100
	("SI-2", "P1", 1, 1, 0, -220.0, -200.0),  # avoir validé
	("SI-3", "P1", 1, 0, 1, 500.0, 500.0),  # facture d'acompte
	("SI-4", "P1", 0, 0, 0, 999.0, 999.0),  # brouillon
	("SI-5", "P1", 2, 0, 0, 777.0, 777.0),  # annulée
	("SI-6", "P2", 1, 0, None, 300.0, 300.0),  # is_down_payment_invoice NULL
]


class TestCADefinition(unittest.TestCase):
	def setUp(self):
		self.db = sqlite3.connect(":memory:")
		self.db.execute(
			"CREATE TABLE `tabSales Invoice` (name TEXT, project TEXT, docstatus INT,"
			" is_return INT, is_down_payment_invoice INT, total REAL, net_total REAL)"
		)
		self.db.executemany("INSERT INTO `tabSales Invoice` VALUES (?, ?, ?, ?, ?, ?, ?)", INVOICES)

	def tearDown(self):
		self.db.close()

	def _ca(self, group=False):
		sql = f"SELECT si.project, SUM({_MOD.CA_AMOUNT}) FROM `tabSales Invoice` si WHERE {_MOD.CA_WHERE}"
		if group:
			return dict(self.db.execute(sql + " GROUP BY si.project ORDER BY si.project").fetchall())
		return self.db.execute(sql).fetchone()[1]

	def test_net_total_credit_notes_deducted_down_payments_excluded(self):
		# 1000 (net après remise) − 200 (avoir) + 300 ; acompte, brouillon, annulée exclus
		self.assertAlmostEqual(self._ca(), 1100.0)

	def test_per_project(self):
		self.assertEqual(self._ca(group=True), {"P1": 800.0, "P2": 300.0})

	def test_included_documents(self):
		names = [
			r[0]
			for r in self.db.execute(
				f"SELECT si.name FROM `tabSales Invoice` si WHERE {_MOD.CA_WHERE} ORDER BY si.name"
			)
		]
		self.assertEqual(names, ["SI-1", "SI-2", "SI-6"])

	def test_definition_does_not_filter_on_returns(self):
		# Les avoirs doivent rester inclus : aucune condition sur is_return.
		self.assertNotIn("is_return", _MOD.CA_WHERE)
		self.assertEqual(_MOD.CA_AMOUNT, "si.net_total")


if __name__ == "__main__":
	unittest.main()

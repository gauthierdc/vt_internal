# Copyright (c) 2026, Verre & Transparence and contributors
# Tests de la résolution du fournisseur par défaut (sans site Frappe).
# Données = extrait réel de la prod (10/10/2026) + lignes cibles du setup.

import doctest
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

if "frappe" not in sys.modules:
	sys.modules["frappe"] = MagicMock()

_SPEC = importlib.util.spec_from_file_location("vt_item_defaults", Path(__file__).with_name("item_defaults.py"))
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)
resolve = _MOD.resolve_default_supplier

MAV, VS, EDC = "Miroiterie Avignonnaise", "Vitrerie Stéphanoise", "EDC SARL"
TREE = {
	"Verres trempés AA": "Verres trempés",
	"Verres trempés BP": "Verres trempés",
	"Verres trempés": "Verres trempés - feuilletés trempés",
	"Verres trempés - feuilletés trempés": "Verres",
	"Verres float": "Verres monolithiques",
	"Verres imprimés": "Verres monolithiques",
	"Verres monolithiques": "Verres",
	"Verres": "Miroiterie",
	"Double vitrage standard": "Double vitrage compositions",
	"Double vitrage compositions": "Double vitrage",
	"Double vitrage": "Miroiterie",
	"Miroiterie": "Tous les groupes d'articles",
}
ROWS = {
	("Item Group", "Verres trempés - feuilletés trempés", MAV): "08BMV000",
	("Item Group", "Verres trempés - feuilletés trempés", VS): "08BMV000",
	("Item Group", "Verres", MAV): "INTERNE MAV",
	("Item Group", "Verres", VS): "INTERNE",
	("Item Group", "Verres trempés BP", VS): "08BMV000",  # existe déjà en prod
	("Item", "5R-X-4", MAV): "MIDI MIROITERIE",
	("Item", "5R-X-4", VS): "VIA",
	("Item", "1506DARKBP", VS): "08BMV000",
}


def r(code, group, company):
	return resolve({"name": code, "item_group": group}, company, lambda pt, p, c: ROWS.get((pt, p, c)), TREE.get)


class TestDefaultSupplier(unittest.TestCase):
	def test_mav_trempe(self):
		self.assertEqual(r("TREMPE-AA", "Verres trempés AA", MAV), "08BMV000")

	def test_mav_float(self):
		self.assertEqual(r("FLOAT", "Verres float", MAV), "INTERNE MAV")

	def test_vs_imprime(self):
		self.assertEqual(r("IMP", "Verres imprimés", VS), "INTERNE")

	def test_edc_empty(self):
		self.assertIsNone(r("TREMPE-AA", "Verres trempés AA", EDC))
		self.assertIsNone(r("FLOAT", "Verres float", EDC))

	def test_item_default_wins(self):
		self.assertEqual(r("5R-X-4", "Double vitrage standard", MAV), "MIDI MIROITERIE")
		self.assertEqual(r("5R-X-4", "Double vitrage standard", VS), "VIA")
		self.assertEqual(r("1506DARKBP", "Verres trempés BP", VS), "08BMV000")
		self.assertEqual(r("1506DARKBP", "Verres trempés BP", MAV), "08BMV000")

	def test_no_company(self):
		self.assertIsNone(r("FLOAT", "Verres float", None))

	def test_loop_guard(self):
		self.assertIsNone(resolve({"name": "X", "item_group": "A"}, MAV, lambda *a: None, {"A": "B", "B": "A"}.get))


def load_tests(loader, tests, ignore):
	tests.addTests(doctest.DocTestSuite(_MOD))
	return tests


if __name__ == "__main__":
	unittest.main()

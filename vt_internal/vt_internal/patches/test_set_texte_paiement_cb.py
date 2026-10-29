# Copyright (c) 2026, Verre & Transparence and contributors
# For license information, please see license.txt

"""Patch Company.custom_texte_paiement_cb : MAV et VS, sans écraser une saisie."""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path

MAV = "04.90.86.63.19 (Tapez 1, n'hésitez pas à me laisser un message sur le répondeur)"
VS = "04 77 50 92 29 (Tapez 1, n'hésitez pas à me laisser un message sur le répondeur)"
FIELD = "custom_texte_paiement_cb"


class _DB:
	def __init__(self, companies=None, field_exists=False, column=False, quotation_terms=True):
		self.companies = dict(companies or {})
		self.field_exists = field_exists
		self.column = column
		self.quotation_terms = quotation_terms
		self.updates = []
		self.company_table = True

	def table_exists(self, doctype):
		if doctype == "Company":
			return self.company_table
		raise AssertionError(doctype)

	def exists(self, doctype, name=None):
		if doctype == "Custom Field":
			filters = name or {}
			return bool(
				self.field_exists and filters.get("dt") == "Company" and filters.get("fieldname") == FIELD
			)
		if doctype == "Company":
			return name in self.companies
		raise AssertionError((doctype, name))

	def has_column(self, doctype, fieldname):
		if doctype == "Company" and fieldname == "custom_quotation_terms":
			return self.quotation_terms
		if doctype == "Company" and fieldname == FIELD:
			return self.column
		raise AssertionError((doctype, fieldname))

	def get_value(self, doctype, name, fieldname):
		if doctype != "Company" or fieldname != FIELD:
			raise AssertionError((doctype, name, fieldname))
		return self.companies[name]

	def set_value(self, doctype, name, fieldname, value):
		self.updates.append((doctype, name, fieldname, value))
		self.companies[name] = value
		self.column = True


def _load(frappe_mod):
	custom_field = types.ModuleType("frappe.custom.doctype.custom_field.custom_field")

	def create_custom_field(doctype, df, ignore_validate=False, is_system_generated=True):
		frappe_mod.created.append(
			{
				"doctype": doctype,
				"df": df,
				"ignore_validate": ignore_validate,
				"is_system_generated": is_system_generated,
			}
		)
		frappe_mod.db.field_exists = True
		frappe_mod.db.column = True

	custom_field.create_custom_field = create_custom_field
	needed = {
		"frappe": frappe_mod,
		"frappe.custom": types.ModuleType("frappe.custom"),
		"frappe.custom.doctype": types.ModuleType("frappe.custom.doctype"),
		"frappe.custom.doctype.custom_field": types.ModuleType("frappe.custom.doctype.custom_field"),
		"frappe.custom.doctype.custom_field.custom_field": custom_field,
	}
	previous = {name: sys.modules.get(name) for name in needed}
	sys.modules.update(needed)
	try:
		path = Path(__file__).with_name("set_texte_paiement_cb.py")
		spec = importlib.util.spec_from_file_location("vt_set_texte_paiement_cb_under_test", path)
		module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(module)
		return module
	finally:
		for name, module in previous.items():
			if module is None:
				sys.modules.pop(name, None)
			else:
				sys.modules[name] = module


class TestSetTextePaiementCb(unittest.TestCase):
	def setUp(self):
		self.frappe = types.ModuleType("frappe")
		self.frappe.created = []
		self.db = _DB(
			companies={
				"Miroiterie Avignonnaise": None,
				"Vitrerie Stéphanoise": None,
				"EDC SARL": None,
				"Vision d'O": "",
				"Serrurerie Ferronnerie Métallerie du Luberon": None,
			}
		)
		self.frappe.db = self.db
		self.mod = _load(self.frappe)

	def test_seed_values_are_the_phone_texts_only(self):
		self.assertEqual(self.mod.TEXTES_PAIEMENT_CB["Miroiterie Avignonnaise"], MAV)
		self.assertEqual(self.mod.TEXTES_PAIEMENT_CB["Vitrerie Stéphanoise"], VS)
		self.assertEqual(
			set(self.mod.TEXTES_PAIEMENT_CB), {"Miroiterie Avignonnaise", "Vitrerie Stéphanoise"}
		)
		self.assertEqual(self.mod.TEXTE_PAIEMENT_CB_FIELD, FIELD)

	def test_insert_after_quotation_terms_or_phone(self):
		self.assertEqual(self.mod.insert_after_field(True), "custom_quotation_terms")
		self.assertEqual(self.mod.insert_after_field(False), "phone_no")

	def test_execute_creates_field_and_fills_only_blank_mav_vs(self):
		self.db.companies["Vitrerie Stéphanoise"] = "déjà saisi"
		self.mod.execute()
		created = self.frappe.created[0]
		self.assertEqual(created["doctype"], "Company")
		self.assertEqual(created["df"]["fieldname"], FIELD)
		self.assertEqual(created["df"]["fieldtype"], "Small Text")
		self.assertEqual(created["df"]["insert_after"], "custom_quotation_terms")
		self.assertEqual(created["df"]["translatable"], 0)
		self.assertFalse(created["is_system_generated"])
		self.assertTrue(created["ignore_validate"])
		self.assertEqual(self.db.updates, [("Company", "Miroiterie Avignonnaise", FIELD, MAV)])
		self.assertEqual(self.db.companies["Vitrerie Stéphanoise"], "déjà saisi")
		self.assertIsNone(self.db.companies["EDC SARL"])
		self.assertEqual(self.db.companies["Vision d'O"], "")

	def test_execute_is_idempotent_and_skips_missing_company(self):
		self.mod.execute()
		self.frappe.created.clear()
		self.db.updates.clear()
		del self.db.companies["Vitrerie Stéphanoise"]
		self.mod.execute()
		self.assertEqual(self.frappe.created, [])
		self.assertEqual(self.db.updates, [])
		self.assertEqual(self.db.companies["Miroiterie Avignonnaise"], MAV)

	def test_whitespace_is_filled_and_phone_no_is_used_without_quotation_terms(self):
		self.db.quotation_terms = False
		self.db.companies["Miroiterie Avignonnaise"] = "  "
		self.mod.execute()
		self.assertEqual(self.frappe.created[0]["df"]["insert_after"], "phone_no")
		self.assertEqual(self.db.companies["Miroiterie Avignonnaise"], MAV)
		self.assertEqual(self.db.companies["Vitrerie Stéphanoise"], VS)

	def test_skips_when_company_table_is_absent(self):
		self.db.company_table = False
		self.mod.execute()
		self.assertEqual(self.frappe.created, [])
		self.assertEqual(self.db.updates, [])

	def test_no_write_when_the_column_is_still_missing(self):
		self.db.field_exists = True

		def create_custom_field(*_args, **_kwargs):
			raise AssertionError("le champ existe déjà")

		# Le module sous test a déjà lié create_custom_field. On simule une colonne absente.
		self.db.column = False
		self.mod.create_custom_field = create_custom_field
		self.mod.execute()
		self.assertEqual(self.db.updates, [])
		self.assertIsNone(self.db.companies["Miroiterie Avignonnaise"])

# Copyright (c) 2026, Verre & Transparence and contributors
# For license information, please see license.txt

"""get_texte_paiement_cb : invité, texte échappé, rien d'autre du devis."""

from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path


def _escape_html(text):
	if not isinstance(text, str):
		return text
	table = {
		"&": "&amp;",
		'"': "&quot;",
		"'": "&apos;",
		">": "&gt;",
		"<": "&lt;",
	}
	return "".join(table.get(char, char) for char in text)


def _whitelist(*args, **kwargs):
	def decorate(fn):
		fn.allow_guest = bool(kwargs.get("allow_guest"))
		return fn

	if args and callable(args[0]) and not kwargs:
		return decorate(args[0])
	return decorate


class _DB:
	def __init__(self, quotations=None, companies=None):
		self.quotations = quotations or {}
		self.companies = companies or {}
		self.calls = []
		self.raise_on_company = False

	def get_value(self, doctype, name, fieldname):
		self.calls.append((doctype, name, fieldname))
		if doctype == "Quotation" and fieldname == "company":
			return self.quotations.get(name)
		if doctype == "Company" and fieldname == "custom_texte_paiement_cb":
			if self.raise_on_company:
				raise RuntimeError("colonne absente")
			if name not in self.companies:
				return None
			return self.companies[name]
		raise AssertionError((doctype, name, fieldname))


def _load(frappe_mod):
	previous = sys.modules.get("frappe")
	sys.modules["frappe"] = frappe_mod
	try:
		path = Path(__file__).with_name("web_form.py")
		spec = importlib.util.spec_from_file_location("vt_web_form_paiement_under_test", path)
		module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(module)
		return module
	finally:
		if previous is None:
			sys.modules.pop("frappe", None)
		else:
			sys.modules["frappe"] = previous


MAV = "04.90.86.63.19 (Tapez 1, n'hésitez pas à me laisser un message sur le répondeur)"
VS = "04 77 50 92 29 (Tapez 1, n'hésitez pas à me laisser un message sur le répondeur)"


class TestTextePaiementCb(unittest.TestCase):
	def setUp(self):
		self.frappe = types.ModuleType("frappe")
		self.frappe.whitelist = _whitelist
		self.frappe.utils = types.SimpleNamespace(escape_html=_escape_html)
		self.frappe.logged = []

		def log_error(title=None, message=None):
			self.frappe.logged.append((title, message))

		self.frappe.log_error = log_error
		self.frappe.get_traceback = lambda: "trace"
		self.db = _DB()
		self.frappe.db = self.db
		self.mod = _load(self.frappe)

	def test_allow_guest_and_fieldname(self):
		self.assertTrue(self.mod.get_texte_paiement_cb.allow_guest)
		self.assertEqual(self.mod.TEXTE_PAIEMENT_CB_FIELD, "custom_texte_paiement_cb")

	def test_missing_or_invalid_quotation_returns_empty_without_query(self):
		for value in (None, "", "   ", 12, ["DEV-1"], {"name": "DEV-1"}, "bad\nname", "X" * 141):
			self.db.calls.clear()
			self.assertEqual(self.mod.get_texte_paiement_cb(value), "")
			self.assertEqual(self.db.calls, [])

	def test_unknown_quotation_returns_empty_and_does_not_read_company(self):
		self.assertEqual(self.mod.get_texte_paiement_cb("DEV-INCONNU"), "")
		self.assertEqual(self.db.calls, [("Quotation", "DEV-INCONNU", "company")])

	def test_strips_quotation_name(self):
		self.db.quotations["DEV-MAV-1"] = "Miroiterie Avignonnaise"
		self.db.companies["Miroiterie Avignonnaise"] = MAV
		self.assertEqual(self.mod.get_texte_paiement_cb("  DEV-MAV-1  "), MAV.replace("'", "&apos;"))
		self.assertEqual(self.db.calls[0], ("Quotation", "DEV-MAV-1", "company"))

	def test_mav_and_vs_return_only_escaped_phone_text(self):
		self.db.quotations["DEV-MAV-1"] = "Miroiterie Avignonnaise"
		self.db.quotations["DEV-VS-1"] = "Vitrerie Stéphanoise"
		self.db.companies["Miroiterie Avignonnaise"] = MAV
		self.db.companies["Vitrerie Stéphanoise"] = VS
		mav = self.mod.get_texte_paiement_cb("DEV-MAV-1")
		vs = self.mod.get_texte_paiement_cb("DEV-VS-1")
		self.assertEqual(mav, MAV.replace("'", "&apos;"))
		self.assertEqual(vs, VS.replace("'", "&apos;"))
		self.assertNotIn("Miroiterie", mav)
		self.assertNotIn("Vitrerie", vs)
		self.assertNotIn("<", mav)
		self.assertNotIn(">", mav)
		fields = {call[2] for call in self.db.calls}
		self.assertEqual(fields, {"company", "custom_texte_paiement_cb"})

	def test_blank_company_text_returns_empty(self):
		self.db.quotations["DEV-EDC-1"] = "EDC SARL"
		self.db.companies["EDC SARL"] = "   "
		self.assertEqual(self.mod.get_texte_paiement_cb("DEV-EDC-1"), "")
		self.db.companies["EDC SARL"] = None
		self.assertEqual(self.mod.get_texte_paiement_cb("DEV-EDC-1"), "")

	def test_script_and_ampersand_are_escaped(self):
		self.db.quotations["DEV-1"] = "SECRET"
		self.db.companies["SECRET"] = """<script>alert("x")</script> & n'hésitez"""
		result = self.mod.get_texte_paiement_cb("DEV-1")
		self.assertEqual(
			result,
			"&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt; &amp; n&apos;hésitez",
		)
		self.assertNotIn("<", result)
		self.assertNotIn("SECRET", result)

	def test_unsafe_escape_html_is_replaced(self):
		self.frappe.utils.escape_html = lambda text: text
		self.db.quotations["DEV-1"] = "MAV"
		self.db.companies["MAV"] = "<img src=x onerror=alert(1)>"
		result = self.mod.get_texte_paiement_cb("DEV-1")
		self.assertNotIn("<", result)
		self.assertIn("&lt;img", result)

	def test_database_error_returns_empty_for_the_guest(self):
		self.db.quotations["DEV-1"] = "MAV"
		self.db.raise_on_company = True
		self.assertEqual(self.mod.get_texte_paiement_cb("DEV-1"), "")
		self.assertEqual(self.frappe.logged[0][0], "Texte paiement CB")

# Copyright (c) 2026, Verre & Transparence and contributors
# Permissions Cost Center : pas de site Frappe.

import importlib.util
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


def _load(module_name, relative_path, frappe_mod):
	previous = sys.modules.get("frappe")
	sys.modules["frappe"] = frappe_mod
	try:
		spec = importlib.util.spec_from_file_location(module_name, Path(__file__).parent / relative_path)
		module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(module)
		return module
	finally:
		if previous is None:
			sys.modules.pop("frappe", None)
		else:
			sys.modules["frappe"] = previous


class _Frappe:
	def __init__(self, permissions=None, session_user="fleur.iraci@miroiterie-avignon.com"):
		self.session = SimpleNamespace(user=session_user)
		self.permissions = SimpleNamespace(get_user_permissions=lambda user=None: permissions or {})


AO = "MAV - AO REGION - MAV"


def _perm(doc, applicable_for=None, is_default=0):
	return {"doc": doc, "applicable_for": applicable_for, "is_default": is_default}


class TestCostCenterQuery(unittest.TestCase):
	def _mod(self, permissions, session_user="fleur.iraci@miroiterie-avignon.com"):
		return _load(
			"vt_cost_center_permissions_under_test",
			"cost_center.py",
			_Frappe(permissions, session_user),
		)

	def test_no_filter_without_cost_center_permission(self):
		mod = self._mod({})
		self.assertIsNone(mod.get_purchase_order_permission_query_conditions("alice@example.com"))
		self.assertIsNone(mod.get_expense_permission_query_conditions("alice@example.com"))

	def test_excludes_empty_cost_center_without_listing_allowed_values(self):
		mod = self._mod({"Cost Center": [_perm(AO, is_default=1)]})
		condition = mod.get_purchase_order_permission_query_conditions("fleur.iraci@miroiterie-avignon.com")
		self.assertEqual(
			condition,
			"(`tabPurchase Order`.`cost_center` is not null and `tabPurchase Order`.`cost_center` != '')",
		)
		self.assertNotIn(AO, condition)
		self.assertNotIn("descendants", condition.lower())
		self.assertNotIn(" in ", condition.lower())

	def test_expense_uses_its_own_table(self):
		mod = self._mod({"Cost Center": [_perm(AO)]})
		condition = mod.get_expense_permission_query_conditions("fleur.iraci@miroiterie-avignon.com")
		self.assertIn("`tabExpense`.`cost_center`", condition)
		self.assertNotIn("Purchase Order", condition)

	def test_permission_scoped_to_another_doctype_does_not_apply(self):
		mod = self._mod({"Cost Center": [_perm(AO, applicable_for="Sales Order")]})
		user = "fleur.iraci@miroiterie-avignon.com"
		self.assertIsNone(mod.get_purchase_order_permission_query_conditions(user))
		self.assertIsNone(mod.get_expense_permission_query_conditions(user))

	def test_permission_applicable_for_only_matches_that_doctype(self):
		mod = self._mod({"Cost Center": [_perm(AO, applicable_for="Purchase Order")]})
		user = "fleur.iraci@miroiterie-avignon.com"
		self.assertIsNotNone(mod.get_purchase_order_permission_query_conditions(user))
		self.assertIsNone(mod.get_expense_permission_query_conditions(user))

	def test_descendant_entry_still_counts_as_a_restriction(self):
		# get_user_permissions développe les descendants avec le même applicable_for.
		mod = self._mod({"Cost Center": [_perm("MAV - AO REGION - MAV - Agence", applicable_for=None)]})
		self.assertIsNotNone(mod.permission_query_conditions("fleur.iraci@miroiterie-avignon.com", "Expense"))

	def test_administrator_and_guest_are_not_restricted(self):
		perms = {"Cost Center": [_perm(AO)]}
		mod = self._mod(perms)
		self.assertIsNone(mod.permission_query_conditions("Administrator", "Purchase Order"))
		self.assertIsNone(mod.permission_query_conditions("Guest", "Expense"))

	def test_has_permission_denies_only_empty_cost_center(self):
		mod = self._mod({"Cost Center": [_perm(AO)]})
		user = "fleur.iraci@miroiterie-avignon.com"
		empty_values = (None, "", "   ")
		for value in empty_values:
			doc = SimpleNamespace(doctype="Purchase Order", get=lambda key, value=value: value)
			self.assertIs(mod.has_permission(doc, ptype="read", user=user), False)
		filled = SimpleNamespace(doctype="Expense", get=lambda key: AO)
		# None : on ne court-circuite pas les autres hooks ni le filtre standard.
		self.assertIsNone(mod.has_permission(filled, ptype="read", user=user))

	def test_has_permission_ignores_unrestricted_users(self):
		mod = self._mod({})
		doc = SimpleNamespace(doctype="Expense", get=lambda key: None)
		self.assertIsNone(mod.has_permission(doc, user="alice@example.com"))

	def test_hooks_register_both_doctypes(self):
		import vt_internal.hooks as hooks

		self.assertEqual(
			hooks.permission_query_conditions["Purchase Order"],
			"vt_internal.vt_internal.permissions.cost_center.get_purchase_order_permission_query_conditions",
		)
		self.assertEqual(
			hooks.permission_query_conditions["Expense"],
			"vt_internal.vt_internal.permissions.cost_center.get_expense_permission_query_conditions",
		)
		self.assertEqual(
			hooks.has_permission["Purchase Order"],
			"vt_internal.vt_internal.permissions.cost_center.has_permission",
		)
		self.assertEqual(
			hooks.has_permission["Expense"],
			"vt_internal.vt_internal.permissions.cost_center.has_permission",
		)


if __name__ == "__main__":
	unittest.main()

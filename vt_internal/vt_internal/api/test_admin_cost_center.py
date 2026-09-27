# Copyright (c) 2026, Verre & Transparence and contributors
# change_cost_center : pas de site Frappe.

import importlib.util
import sys
import unittest
from pathlib import Path


class _Thrown(Exception):
	pass


class _Doc:
	def __init__(self, data):
		self.__dict__.update(data)
		self.inserted = None
		self.saved = None

	def insert(self, **kwargs):
		self.inserted = kwargs

	def save(self, **kwargs):
		self.saved = kwargs


class _Frappe:
	def __init__(self):
		self.form_dict = {}
		self.permissions = {}
		self.deleted = []
		self.set_values = []
		self.user_defaults = {}
		self.cache_deletes = []
		self.docs = []
		self.db = self
		self.defaults = self
		self.cache = self

	def whitelist(self, *args, **kwargs):
		if args and callable(args[0]) and not kwargs:
			return args[0]

		def decorator(fn):
			return fn

		return decorator

	def throw(self, message):
		raise _Thrown(message)

	def get_value(self, doctype, filters, fieldname):
		for perm in self.permissions.get(filters["user"], []):
			if perm["allow"] == filters["allow"]:
				return perm["name"]
		return None

	def get_all(self, doctype, filters=None, pluck=None):
		filters = filters or {}
		names = []
		for perm in self.permissions.get(filters.get("user"), []):
			if perm["allow"] != filters.get("allow"):
				continue
			if filters.get("is_default") is not None and perm.get("is_default") != filters["is_default"]:
				continue
			name_filter = filters.get("name")
			if (
				isinstance(name_filter, list | tuple)
				and name_filter[0] == "!="
				and perm["name"] == name_filter[1]
			):
				continue
			names.append(perm[pluck] if pluck else perm)
		return names

	def get_doc(self, data, name=None):
		if isinstance(data, str):
			for user_perms in self.permissions.values():
				for perm in user_perms:
					if perm["name"] == name:
						doc = _Doc(dict(perm))
						self.docs.append(doc)
						return doc
			raise KeyError(name)
		doc = _Doc(dict(data))
		self.docs.append(doc)
		return doc

	def delete_doc(self, doctype, name, ignore_permissions=False):
		self.deleted.append((doctype, name, ignore_permissions))
		for user, perms in self.permissions.items():
			self.permissions[user] = [perm for perm in perms if perm["name"] != name]

	def set_value(self, doctype, name, field, value):
		self.set_values.append((doctype, name, field, value))
		for perms in self.permissions.values():
			for perm in perms:
				if perm["name"] == name:
					perm[field] = value

	def set_user_default(self, key, value, user=None):
		self.user_defaults[(user, key)] = value

	def clear_user_default(self, key, user=None):
		self.user_defaults.pop((user, key), None)

	def hdel(self, key, user):
		self.cache_deletes.append((key, user))


def _load(frappe_mod):
	previous = sys.modules.get("frappe")
	sys.modules["frappe"] = frappe_mod
	try:
		path = Path(__file__).with_name("admin.py")
		spec = importlib.util.spec_from_file_location("vt_admin_cost_center_under_test", path)
		module = importlib.util.module_from_spec(spec)
		spec.loader.exec_module(module)
		return module
	finally:
		if previous is None:
			sys.modules.pop("frappe", None)
		else:
			sys.modules["frappe"] = previous


AO = "MAV - AO REGION - MAV"
USER = "fleur.iraci@miroiterie-avignon.com"


class TestChangeCostCenter(unittest.TestCase):
	def setUp(self):
		self.frappe = _Frappe()
		self.mod = _load(self.frappe)

	def test_html_block_argument_names_via_form_dict(self):
		self.frappe.form_dict = {"user": USER, "cost_center": AO}
		self.mod.change_cost_center()
		doc = self.frappe.docs[0]
		self.assertEqual(doc.user, USER)
		self.assertEqual(doc.for_value, AO)
		self.assertEqual(doc.is_default, 1)
		self.assertEqual(doc.allow, "Cost Center")
		self.assertEqual(doc.apply_to_all_doctypes, 1)
		self.assertEqual(doc.inserted, {"ignore_permissions": True})
		self.assertEqual(self.frappe.user_defaults[(USER, "cost_center")], AO)
		self.assertIn(("user_permissions", USER), self.frappe.cache_deletes)

	def test_kwargs_match_the_desk_block(self):
		self.mod.change_cost_center(user=USER, cost_center=AO)
		self.assertEqual(self.frappe.docs[0].for_value, AO)
		self.assertEqual(self.frappe.user_defaults[(USER, "cost_center")], AO)

	def test_switch_sets_is_default_and_user_default(self):
		self.frappe.permissions[USER] = [
			{
				"name": "UP-1",
				"user": USER,
				"allow": "Cost Center",
				"for_value": "MAV - Autre - MAV",
				"is_default": 0,
				"apply_to_all_doctypes": 1,
			}
		]
		self.mod.change_cost_center(user=USER, cost_center=AO)
		doc = self.frappe.docs[0]
		self.assertEqual(doc.for_value, AO)
		self.assertEqual(doc.is_default, 1)
		self.assertEqual(doc.saved, {"ignore_permissions": True})
		self.assertFalse(any(call[2] == "for_value" for call in self.frappe.set_values))
		self.assertEqual(self.frappe.user_defaults[(USER, "cost_center")], AO)

	def test_other_default_is_cleared_before_save(self):
		self.frappe.permissions[USER] = [
			{
				"name": "UP-1",
				"user": USER,
				"allow": "Cost Center",
				"for_value": "MAV - Autre - MAV",
				"is_default": 0,
			},
			{
				"name": "UP-2",
				"user": USER,
				"allow": "Cost Center",
				"for_value": "MAV - Riviera - MAV",
				"is_default": 1,
			},
		]
		self.mod.change_cost_center(user=USER, cost_center=AO)
		self.assertIn(("User Permission", "UP-2", "is_default", 0), self.frappe.set_values)
		self.assertEqual(self.frappe.docs[0].name, "UP-1")
		self.assertEqual(self.frappe.docs[0].is_default, 1)

	def test_empty_value_removes_permission_and_default(self):
		self.frappe.permissions[USER] = [
			{"name": "UP-1", "user": USER, "allow": "Cost Center", "for_value": AO, "is_default": 1}
		]
		self.frappe.user_defaults[(USER, "cost_center")] = AO
		self.mod.change_cost_center(user=USER, cost_center="")
		self.assertEqual(self.frappe.deleted, [("User Permission", "UP-1", True)])
		self.assertNotIn((USER, "cost_center"), self.frappe.user_defaults)
		self.assertEqual(self.frappe.docs, [])
		self.assertFalse(any(call[2] == "for_value" for call in self.frappe.set_values))

	def test_missing_cost_center_does_not_also_rewrite_for_value(self):
		# L'ancien script traitait None != "" comme une mise à jour et faisait
		# delete + set_value dans le même appel.
		self.frappe.permissions[USER] = [
			{"name": "UP-1", "user": USER, "allow": "Cost Center", "for_value": AO, "is_default": 0}
		]
		self.frappe.form_dict = {"user": USER, "cost_center": None}
		self.mod.change_cost_center()
		self.assertEqual(self.frappe.deleted, [("User Permission", "UP-1", True)])
		self.assertEqual(self.frappe.set_values, [])

	def test_clear_without_permission_still_drops_stale_default(self):
		self.frappe.user_defaults[(USER, "cost_center")] = AO
		self.mod.change_cost_center(user=USER, cost_center="")
		self.assertEqual(self.frappe.deleted, [])
		self.assertNotIn((USER, "cost_center"), self.frappe.user_defaults)

	def test_missing_user_is_rejected(self):
		with self.assertRaises(_Thrown):
			self.mod.change_cost_center(cost_center=AO)


if __name__ == "__main__":
	unittest.main()

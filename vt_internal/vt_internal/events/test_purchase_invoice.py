"""Tests for Purchase Invoice event hooks.

Standalone (no bench / Frappe site): they reproduce the production
AttributeError when Purchase Invoice has no ``pending_purchase_invoice``
field in meta.
"""

from __future__ import annotations

import sys
import unittest
from unittest.mock import MagicMock

# Event module imports frappe at load time; bench is not available here.
if "frappe" not in sys.modules:
	sys.modules["frappe"] = MagicMock()

from vt_internal.vt_internal.events.purchase_invoice import after_insert, validate


class _MissingAttrDoc:
	"""Mimic a Frappe Document: missing fields raise AttributeError."""

	def __init__(self, **values):
		self.__dict__.update(values)
		self.saved = False

	def __getattr__(self, name):
		raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")

	def get(self, key, default=None):
		return self.__dict__.get(key, default)

	def save(self):
		self.saved = True


class TestPurchaseInvoiceEvents(unittest.TestCase):
	def setUp(self):
		sys.modules["frappe"].reset_mock()

	def test_direct_attr_access_raises_like_production(self):
		doc = _MissingAttrDoc()
		with self.assertRaises(AttributeError) as ctx:
			_ = doc.pending_purchase_invoice
		self.assertIn("pending_purchase_invoice", str(ctx.exception))

	def test_after_insert_without_pending_field(self):
		"""Repro: save a new Purchase Invoice / create from Supplier Invoice."""
		doc = _MissingAttrDoc(
			custom_mode_of_paiement=None,
			bill_date="2026-09-01",
			due_date="2026-10-01",
		)
		after_insert(doc)
		self.assertTrue(doc.saved)
		self.assertEqual(doc.due_date, "2026-10-01")

	def test_validate_without_pending_field_when_dates_match(self):
		"""validate also read the field when bill_date == due_date."""
		doc = _MissingAttrDoc(
			custom_mode_of_paiement=None,
			bill_date="2026-09-01",
			due_date="2026-09-01",
		)
		validate(doc)
		self.assertEqual(doc.due_date, "2026-09-01")

	def test_after_insert_copies_due_date_when_pending_is_set(self):
		doc = _MissingAttrDoc(
			custom_mode_of_paiement=None,
			pending_purchase_invoice="PPI-0001",
			due_date="2026-09-01",
		)
		frappe = sys.modules["frappe"]
		frappe.db.get_value.return_value = "2026-10-15"
		after_insert(doc)
		self.assertEqual(doc.due_date, "2026-10-15")
		frappe.db.get_value.assert_called_with("Pending Purchase Invoice", "PPI-0001", "due_date")

	def test_validate_copies_due_date_only_when_dates_match(self):
		frappe = sys.modules["frappe"]
		frappe.db.get_value.return_value = "2026-10-15"

		unchanged = _MissingAttrDoc(
			custom_mode_of_paiement=None,
			pending_purchase_invoice="PPI-0001",
			bill_date="2026-09-01",
			due_date="2026-09-15",
		)
		validate(unchanged)
		self.assertEqual(unchanged.due_date, "2026-09-15")

		matched = _MissingAttrDoc(
			custom_mode_of_paiement=None,
			pending_purchase_invoice="PPI-0001",
			bill_date="2026-09-01",
			due_date="2026-09-01",
		)
		validate(matched)
		self.assertEqual(matched.due_date, "2026-10-15")


if __name__ == "__main__":
	unittest.main()

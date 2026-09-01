"""Tests for Purchase Invoice event hooks.

Standalone (no bench / Frappe site): they reproduce the production
AttributeError when Purchase Invoice has no ``pending_purchase_invoice``
field in meta. The OCR due-date copy path is gone; hooks must still
survive that missing attribute.
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

	def test_validate_without_pending_field(self):
		"""validate must not touch pending_purchase_invoice."""
		doc = _MissingAttrDoc(
			custom_mode_of_paiement=None,
			bill_date="2026-09-01",
			due_date="2026-09-01",
		)
		validate(doc)
		self.assertEqual(doc.due_date, "2026-09-01")


if __name__ == "__main__":
	unittest.main()

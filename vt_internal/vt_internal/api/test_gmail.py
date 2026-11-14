# Copyright (c) 2026, Verre & Transparence and contributors
# For license information, please see license.txt

"""lookup_by_email : pas de site Frappe, frappe.get_list simulé."""

from __future__ import annotations

import copy
import importlib
import json
import re
import sys
import unittest
from urllib.parse import quote

OPERATORS = {"=", "!=", "<", ">", "<=", ">=", "in", "not in", "like", "not like"}
EMAIL_FIELDS = {"email_id", "matched_email"}
SLUGS = {
	"Customer": "customer",
	"Supplier": "supplier",
	"Lead": "lead",
	"Contact": "contact",
	"Quotation": "quotation",
	"Sales Order": "sales-order",
	"Sales Invoice": "sales-invoice",
	"Supplier Quotation": "supplier-quotation",
	"Purchase Order": "purchase-order",
	"Purchase Invoice": "purchase-invoice",
}
DOCTYPES = [
	"Contact",
	"Address",
	"Customer",
	"Supplier",
	"Lead",
	"Quotation",
	"Sales Order",
	"Sales Invoice",
	"Supplier Quotation",
	"Purchase Order",
	"Purchase Invoice",
]
SITE = "https://bureau.verretransparence.fr"


class PermissionError(Exception):
	pass


class FakeFrappe:
	"""get_list minimal : filtres, jointures enfant, LIKE SQL, droits."""

	def __init__(self):
		self.permissions = {doctype: True for doctype in DOCTYPES}
		self.tables = {doctype: [] for doctype in DOCTYPES}
		self.calls = []
		self.raise_permission = set()
		self.users = []
		self.utils = self
		self.PermissionError = PermissionError

	def whitelist(self, *args, **kwargs):
		if args and callable(args[0]) and not kwargs:
			return args[0]

		def decorator(fn):
			return fn

		return decorator

	def has_permission(self, doctype, ptype="read", **kwargs):
		perm = self.permissions.get(doctype, False)
		if perm is True:
			return ptype in ("read", "select")
		if isinstance(perm, set):
			return ptype in perm
		return False

	def get_url(self, uri=None):
		if uri:
			return SITE + uri
		return SITE

	def get_all(self, doctype, filters=None, pluck=None, **kwargs):
		assert doctype == "User" and filters == {"user_type": "System User"} and pluck == "email"
		return list(self.users)

	def get_url_to_form(self, doctype, name):
		slug = SLUGS[doctype]
		return f"{SITE}/app/{slug}/{quote(str(name), safe='')}"

	def get_list(
		self,
		doctype,
		filters=None,
		or_filters=None,
		fields=None,
		order_by=None,
		limit_page_length=20,
		**kwargs,
	):
		if "ignore_permissions" in kwargs or "ignore_user_permissions" in kwargs:
			raise AssertionError("les permissions ne doivent pas être ignorées")
		if not self.has_permission(doctype, "read") and not self.has_permission(doctype, "select"):
			raise PermissionError(doctype)
		if doctype in self.raise_permission:
			raise PermissionError(doctype)
		self.calls.append(
			{
				"doctype": doctype,
				"filters": copy.deepcopy(filters),
				"or_filters": copy.deepcopy(or_filters),
				"fields": list(fields or []),
			}
		)
		rows = [copy.deepcopy(row) for row in self.tables.get(doctype, [])]
		rows = [row for row in rows if _row_matches(row, filters) and _or_matches(row, or_filters)]
		expanded = []
		for row in rows:
			expanded.extend(_expand(row, fields))
		expanded = _order(expanded, order_by)
		if limit_page_length:
			expanded = expanded[: int(limit_page_length)]
		return [_project(row, fields) for row in expanded]


def _clauses(filters):
	if not filters:
		return []
	if isinstance(filters, dict):
		clauses = []
		for key, value in filters.items():
			if (
				isinstance(value, (list, tuple))
				and value
				and isinstance(value[0], str)
				and value[0] in OPERATORS
			):
				clauses.append((None, key, value[0], value[1]))
			else:
				clauses.append((None, key, "=", value))
		return clauses
	clauses = []
	for item in filters:
		if len(item) == 4:
			clauses.append((item[0], item[1], item[2], item[3]))
		elif len(item) == 3:
			clauses.append((None, item[0], item[1], item[2]))
		else:
			raise AssertionError(f"filtre inattendu: {item!r}")
	return clauses


def _row_matches(row, filters):
	return all(_clause_matches(row, clause) for clause in _clauses(filters))


def _or_matches(row, or_filters):
	clauses = _clauses(or_filters)
	if not clauses:
		return True
	return any(_clause_matches(row, clause) for clause in clauses)


def _clause_matches(row, clause):
	table, field, operator, expected = clause
	if table == "Contact Email":
		return any(_compare(value, operator, expected, field) for value in (row.get("emails") or []))
	if table == "Dynamic Link":
		return any(_compare(link.get(field), operator, expected, field) for link in (row.get("links") or []))
	return _compare(row.get(field), operator, expected, field)


def _compare(actual, operator, expected, field):
	if field in EMAIL_FIELDS and operator in {"=", "!="} and isinstance(expected, str):
		left = "" if actual is None else str(actual).strip().lower()
		right = expected.strip().lower()
		return left == right if operator == "=" else left != right
	if operator == "=":
		return actual == expected
	if operator == "!=":
		return actual != expected
	if operator == "<":
		return actual is not None and actual < expected
	if operator == ">":
		return actual is not None and actual > expected
	if operator == "<=":
		return actual is not None and actual <= expected
	if operator == ">=":
		return actual is not None and actual >= expected
	if operator == "in":
		return actual in expected
	if operator == "not in":
		return actual not in expected
	if operator == "like":
		return _like(actual, expected)
	if operator == "not like":
		return not _like(actual, expected)
	raise AssertionError(operator)


def _like(value, pattern):
	if value is None:
		return False
	regex = []
	index = 0
	while index < len(pattern):
		char = pattern[index]
		if char == "\\" and index + 1 < len(pattern):
			regex.append(re.escape(pattern[index + 1]))
			index += 2
			continue
		if char == "%":
			regex.append(".*")
		elif char == "_":
			regex.append(".")
		else:
			regex.append(re.escape(char))
		index += 1
	return re.fullmatch("".join(regex), str(value), re.IGNORECASE) is not None


def _expand(row, fields):
	fields = fields or []
	want_email = any("matched_email" in field for field in fields)
	want_link = any("link_doctype" in field for field in fields)
	rows = [dict(row)]
	if want_email:
		emails = list(row.get("emails") or [])
		if emails:
			rows = []
			for email in emails:
				copy_row = dict(row)
				copy_row["matched_email"] = email
				rows.append(copy_row)
		else:
			rows[0]["matched_email"] = None
	if want_link:
		expanded = []
		links = list(row.get("links") or [])
		bases = rows
		if not links:
			for base in bases:
				copy_row = dict(base)
				copy_row["link_doctype"] = None
				copy_row["link_name"] = None
				expanded.append(copy_row)
		else:
			for base in bases:
				for link in links:
					copy_row = dict(base)
					copy_row["link_doctype"] = link.get("link_doctype")
					copy_row["link_name"] = link.get("link_name")
					expanded.append(copy_row)
		rows = expanded
	return rows


def _project(row, fields):
	if not fields:
		return dict(row)
	projected = {}
	for field in fields:
		if " as " in field.lower():
			alias = field.split()[-1]
			projected[alias] = row.get(alias)
		else:
			projected[field] = row.get(field)
	return projected


def _order(rows, order_by):
	if not order_by:
		return rows
	ordered = list(rows)
	for part in reversed([piece.strip() for piece in order_by.split(",")]):
		bits = part.split()
		key = bits[0]
		descending = len(bits) > 1 and bits[1].lower() == "desc"

		def sort_key(row, field=key):
			value = row.get(field)
			return (value is None, "" if value is None else value)

		ordered = sorted(ordered, key=sort_key, reverse=descending)
	return ordered


def _load(fake):
	previous = sys.modules.get("frappe")
	previous_utils = sys.modules.get("frappe.utils")
	sys.modules["frappe"] = fake
	sys.modules["frappe.utils"] = fake
	sys.modules.pop("vt_internal.vt_internal.api.gmail", None)
	try:
		return importlib.import_module("vt_internal.vt_internal.api.gmail")
	finally:
		if previous is None:
			sys.modules.pop("frappe", None)
		else:
			sys.modules["frappe"] = previous
		if previous_utils is None:
			sys.modules.pop("frappe.utils", None)
		else:
			sys.modules["frappe.utils"] = previous_utils


def _customer(**kwargs):
	row = {
		"name": "CUST-1",
		"customer_name": "Dupont SA",
		"customer_group": "Commercial",
		"territory": "France",
		"email_id": None,
		"mobile_no": "0600000000",
		"disabled": 0,
	}
	row.update(kwargs)
	return row


def _supplier(**kwargs):
	row = {
		"name": "SUP-1",
		"supplier_name": "Verrier du Sud",
		"supplier_group": "Vitrage",
		"email_id": None,
		"mobile_no": None,
		"disabled": 0,
	}
	row.update(kwargs)
	return row


def _contact(**kwargs):
	row = {
		"name": "CONTACT-1",
		"full_name": "Jean Dupont",
		"first_name": "Jean",
		"last_name": "Dupont",
		"email_id": "Jean.Dupont@Exemple.fr",
		"phone": "0490112233",
		"mobile_no": "0611223344",
		"emails": ["Jean.Dupont@Exemple.fr"],
		"links": [{"link_doctype": "Customer", "link_name": "CUST-1"}],
	}
	row.update(kwargs)
	return row


def _doc(**kwargs):
	row = {
		"status": "Open",
		"docstatus": 1,
		"grand_total": 100,
		"currency": "EUR",
		"company": "Miroiterie Avignonnaise",
	}
	row.update(kwargs)
	return row


def _uses_like(calls):
	return '"like"' in json.dumps(calls)


class TestGmailLookup(unittest.TestCase):
	def setUp(self):
		self.fake = FakeFrappe()
		self.mod = _load(self.fake)

	def test_normalize_and_generic_domains(self):
		mod = self.mod
		self.assertEqual(
			mod.normalize_email("Jean Dupont <Jean.Dupont@Exemple.fr>"), "jean.dupont@exemple.fr"
		)
		self.assertEqual(mod.normalize_email("mailto:A@B.fr"), "a@b.fr")
		self.assertEqual(mod.normalize_email(None), "")
		self.assertEqual(mod.normalize_email("pas une adresse"), "")
		self.assertEqual(mod.normalize_email(["Jean <jean@exemple.fr>"]), "jean@exemple.fr")
		for domain in (
			"gmail.com",
			"googlemail.com",
			"hotmail.fr",
			"orange.fr",
			"yahoo.fr",
			"yahoo.co.uk",
			"outlook.com",
			"live.fr",
			"icloud.com",
			"laposte.net",
			"sfr.fr",
			"wanadoo.fr",
			"free.fr",
			"neuf.fr",
			"bbox.fr",
			"aol.com",
			"msn.com",
			"proton.me",
		):
			self.assertTrue(mod.is_generic_domain(domain), domain)
		self.assertFalse(mod.is_generic_domain("exemple.fr"))
		self.assertFalse(mod.is_generic_domain("notoutlook.com"))

	def test_invalid_email_is_empty_and_does_not_query(self):
		result = self.mod.lookup_by_email("pas une adresse")
		self.assertIsNone(result["match_type"])
		self.assertIsNone(result["normalized_email"])
		self.assertIsNone(result["create"])
		self.assertEqual(result["customers"], [])
		self.assertEqual(result["suppliers"], [])
		self.assertEqual(self.fake.calls, [])

	def test_exact_contact_returns_customer_documents_and_aggregates(self):
		fake = self.fake
		fake.tables["Contact"].append(_contact())
		fake.tables["Customer"].append(_customer(email_id="jean.dupont@exemple.fr"))
		fake.tables["Quotation"] = [
			_doc(
				name="QTN-01",
				party_name="CUST-1",
				quotation_to="Customer",
				transaction_date="2026-01-01",
				status="Open",
			),
			_doc(name="QTN-02", party_name="CUST-1", quotation_to="Customer", transaction_date="2026-02-01"),
			_doc(name="QTN-03", party_name="CUST-1", quotation_to="Customer", transaction_date="2026-03-01"),
			_doc(name="QTN-04", party_name="CUST-1", quotation_to="Customer", transaction_date="2026-04-01"),
			_doc(name="QTN-05", party_name="CUST-1", quotation_to="Customer", transaction_date="2026-05-01"),
			_doc(name="QTN-06", party_name="CUST-1", quotation_to="Customer", transaction_date="2026-06-01"),
			_doc(
				name="QTN-DRAFT",
				party_name="CUST-1",
				quotation_to="Customer",
				transaction_date="2026-06-15",
				docstatus=0,
				status="Draft",
				grand_total=15,
			),
			_doc(
				name="QTN-CANC",
				party_name="CUST-1",
				quotation_to="Customer",
				transaction_date="2026-07-01",
				docstatus=2,
				status="Cancelled",
			),
			_doc(
				name="QTN-OTHER", party_name="CUST-9", quotation_to="Customer", transaction_date="2026-08-01"
			),
			_doc(name="QTN-LEAD", party_name="CUST-1", quotation_to="Lead", transaction_date="2026-06-20"),
		]
		fake.tables["Sales Order"] = [
			_doc(
				name="SO-OPEN",
				customer="CUST-1",
				transaction_date="2026-05-01",
				status="To Deliver and Bill",
				grand_total=1000,
			),
			_doc(
				name="SO-DONE",
				customer="CUST-1",
				transaction_date="2026-04-01",
				status="Completed",
				grand_total=50,
			),
			_doc(
				name="SO-DRAFT",
				customer="CUST-1",
				transaction_date="2026-03-01",
				status="Draft",
				docstatus=0,
				grand_total=9,
			),
			_doc(
				name="SO-OTHER",
				customer="CUST-9",
				transaction_date="2026-08-01",
				status="To Deliver and Bill",
				grand_total=5,
			),
		]
		fake.tables["Sales Invoice"] = [
			_doc(
				name="SINV-1",
				customer="CUST-1",
				posting_date="2026-05-01",
				status="Unpaid",
				outstanding_amount=100,
				grand_total=100,
			),
			_doc(
				name="SINV-2",
				customer="CUST-1",
				posting_date="2026-04-01",
				status="Partly Paid",
				outstanding_amount=50,
				grand_total=80,
			),
			_doc(
				name="SINV-PAID",
				customer="CUST-1",
				posting_date="2026-03-01",
				status="Paid",
				outstanding_amount=0,
				grand_total=20,
			),
			_doc(
				name="SINV-DRAFT",
				customer="CUST-1",
				posting_date="2026-06-01",
				status="Draft",
				docstatus=0,
				outstanding_amount=30,
				grand_total=30,
			),
			_doc(
				name="SINV-CANC",
				customer="CUST-1",
				posting_date="2026-07-01",
				status="Cancelled",
				docstatus=2,
				outstanding_amount=999,
				grand_total=999,
			),
		]

		result = self.mod.lookup_by_email("  JEAN.DUPONT@exemple.fr ")

		self.assertEqual(result["match_type"], "exact")
		self.assertEqual(result["normalized_email"], "jean.dupont@exemple.fr")
		self.assertFalse(result["generic_domain"])
		self.assertEqual(result["suppliers"], [])
		self.assertEqual(len(result["customers"]), 1)
		customer = result["customers"][0]
		self.assertEqual(
			set(customer),
			{
				"doctype",
				"name",
				"customer_name",
				"customer_group",
				"territory",
				"phone",
				"mobile",
				"email",
				"disabled",
				"url",
				"match_sources",
				"contacts",
				"quotations",
				"sales_orders",
				"sales_invoices",
				"aggregates",
			},
		)
		self.assertEqual(customer["name"], "CUST-1")
		self.assertEqual(customer["customer_name"], "Dupont SA")
		self.assertEqual(customer["customer_group"], "Commercial")
		self.assertEqual(customer["territory"], "France")
		self.assertEqual(customer["phone"], "0490112233")
		self.assertEqual(customer["mobile"], "0611223344")
		self.assertIs(customer["disabled"], False)
		self.assertEqual(customer["url"], f"{SITE}/app/customer/CUST-1")
		self.assertEqual(customer["match_sources"], ["contact", "customer_email"])
		self.assertEqual(customer["contacts"][0]["full_name"], "Jean Dupont")
		self.assertEqual(customer["contacts"][0]["email"], "Jean.Dupont@Exemple.fr")
		self.assertEqual(customer["contacts"][0]["url"], f"{SITE}/app/contact/CONTACT-1")
		self.assertEqual(
			[row["name"] for row in customer["quotations"]],
			["QTN-DRAFT", "QTN-06", "QTN-05", "QTN-04", "QTN-03"],
		)
		self.assertEqual(customer["quotations"][0]["docstatus"], 0)
		self.assertEqual(customer["quotations"][0]["date"], "2026-06-15")
		self.assertEqual(customer["quotations"][0]["grand_total"], 15)
		self.assertNotIn("bill_no", customer["quotations"][0])
		self.assertEqual(customer["quotations"][1]["url"], f"{SITE}/app/quotation/QTN-06")
		self.assertEqual(
			[row["name"] for row in customer["sales_invoices"]],
			["SINV-DRAFT", "SINV-1", "SINV-2", "SINV-PAID"],
		)
		self.assertEqual(
			customer["aggregates"],
			{
				"outstanding_amount": 150.0,
				"unpaid_invoice_count": 2,
				"open_order_count": 1,
				"open_order_total": 1000.0,
			},
		)
		self.assertIn("SO-DRAFT", [row["name"] for row in customer["sales_orders"]])
		self.assertNotIn("SO-OTHER", [row["name"] for row in customer["sales_orders"]])

	def test_customer_email_without_contact(self):
		self.fake.tables["Customer"].append(_customer(email_id="facture@exemple.fr", mobile_no="0601020304"))
		result = self.mod.lookup_by_email("Facture@Exemple.fr")
		self.assertEqual(result["match_type"], "exact")
		customer = result["customers"][0]
		self.assertEqual(customer["match_sources"], ["customer_email"])
		self.assertEqual(customer["contacts"], [])
		self.assertEqual(customer["mobile"], "0601020304")
		self.assertEqual(customer["phone"], None)

	def test_parent_contact_email_without_child_row(self):
		self.fake.tables["Contact"].append(
			_contact(
				email_id="parent@exemple.fr",
				emails=[],
				links=[{"link_doctype": "Customer", "link_name": "CUST-P"}],
			)
		)
		self.fake.tables["Customer"].append(_customer(name="CUST-P", customer_name="Parent", email_id=None))
		result = self.mod.lookup_by_email("parent@exemple.fr")
		self.assertEqual(result["customers"][0]["name"], "CUST-P")
		self.assertEqual(result["customers"][0]["contacts"][0]["email"], "parent@exemple.fr")

	def test_address_email_links_supplier(self):
		self.fake.tables["Address"].append(
			{
				"name": "ADDR-1",
				"email_id": "arc@saint-gobain.example",
				"phone": "0140000000",
				"address_title": "Saint-Gobain",
				"links": [{"link_doctype": "Supplier", "link_name": "SUP-SG"}],
			}
		)
		self.fake.tables["Supplier"].append(_supplier(name="SUP-SG", supplier_name="Saint-Gobain"))
		result = self.mod.lookup_by_email("ARC@saint-gobain.example")
		self.assertEqual(result["customers"], [])
		supplier = result["suppliers"][0]
		self.assertEqual(supplier["name"], "SUP-SG")
		self.assertEqual(supplier["match_sources"], ["address"])
		self.assertEqual(supplier["phone"], "0140000000")
		self.assertEqual(supplier["contacts"], [])
		self.assertEqual(supplier["url"], f"{SITE}/app/supplier/SUP-SG")

	def test_same_email_returns_customer_and_supplier(self):
		self.fake.tables["Contact"].append(
			_contact(
				emails=["compta@exemple.fr"],
				email_id="compta@exemple.fr",
				links=[
					{"link_doctype": "Customer", "link_name": "CUST-1"},
					{"link_doctype": "Supplier", "link_name": "SUP-1"},
				],
			)
		)
		self.fake.tables["Customer"].append(_customer())
		self.fake.tables["Supplier"].append(_supplier())
		result = self.mod.lookup_by_email("compta@exemple.fr")
		self.assertEqual(result["match_type"], "exact")
		self.assertEqual(result["customers"][0]["doctype"], "Customer")
		self.assertEqual(result["suppliers"][0]["doctype"], "Supplier")
		self.assertEqual(result["suppliers"][0]["supplier_name"], "Verrier du Sud")
		self.assertEqual(result["suppliers"][0]["supplier_group"], "Vitrage")

	def test_multiple_customers_keep_their_own_documents(self):
		self.fake.tables["Contact"].append(
			_contact(
				links=[
					{"link_doctype": "Customer", "link_name": "CUST-Z"},
					{"link_doctype": "Customer", "link_name": "CUST-A"},
				]
			)
		)
		self.fake.tables["Customer"] = [
			_customer(name="CUST-Z", customer_name="Zed"),
			_customer(name="CUST-A", customer_name="Alpha"),
		]
		self.fake.tables["Quotation"] = [
			_doc(name="QTN-Z", party_name="CUST-Z", quotation_to="Customer", transaction_date="2026-01-01"),
			_doc(name="QTN-A", party_name="CUST-A", quotation_to="Customer", transaction_date="2026-02-01"),
		]
		result = self.mod.lookup_by_email("jean.dupont@exemple.fr")
		self.assertEqual([row["name"] for row in result["customers"]], ["CUST-A", "CUST-Z"])
		self.assertEqual(result["customers"][0]["quotations"][0]["name"], "QTN-A")
		self.assertEqual(result["customers"][1]["quotations"][0]["name"], "QTN-Z")

	def test_supplier_documents_include_drafts_and_amounts_to_receive(self):
		self.fake.tables["Supplier"].append(_supplier(email_id="achats@verrier.example"))
		self.fake.tables["Supplier Quotation"].append(
			_doc(
				name="SQ-1",
				supplier="SUP-1",
				transaction_date="2026-05-01",
				status="Submitted",
				grand_total=300,
			)
		)
		self.fake.tables["Purchase Order"] = [
			_doc(
				name="PO-RECV",
				supplier="SUP-1",
				transaction_date="2026-07-01",
				status="To Receive and Bill",
				per_received=25,
				grand_total=80,
			),
			_doc(
				name="PO-BILL",
				supplier="SUP-1",
				transaction_date="2026-08-01",
				status="To Bill",
				per_received=100,
				grand_total=40,
			),
			_doc(
				name="PO-HOLD",
				supplier="SUP-1",
				transaction_date="2026-09-01",
				status="On Hold",
				per_received=0,
				grand_total=10,
			),
			_doc(
				name="PO-DONE",
				supplier="SUP-1",
				transaction_date="2026-10-01",
				status="Completed",
				per_received=100,
				grand_total=999,
			),
			_doc(
				name="PO-DRAFT",
				supplier="SUP-1",
				transaction_date="2026-11-01",
				status="Draft",
				docstatus=0,
				per_received=0,
				grand_total=5,
			),
			_doc(
				name="PO-CANC",
				supplier="SUP-1",
				transaction_date="2026-12-01",
				status="Cancelled",
				docstatus=2,
				grand_total=8,
			),
			_doc(
				name="PO-OLD",
				supplier="SUP-1",
				transaction_date="2026-01-01",
				status="To Receive",
				per_received=0,
				grand_total=1,
			),
		]
		self.fake.tables["Purchase Invoice"] = [
			_doc(
				name="PINV-1",
				supplier="SUP-1",
				posting_date="2026-06-01",
				status="Unpaid",
				outstanding_amount=12,
				grand_total=12,
				bill_no="FAC-99",
			),
			_doc(
				name="PINV-2",
				supplier="SUP-1",
				posting_date="2026-05-01",
				status="Partly Paid",
				outstanding_amount=8,
				grand_total=20,
				bill_no="FAC-98",
			),
			_doc(
				name="PINV-PAID",
				supplier="SUP-1",
				posting_date="2026-04-01",
				status="Paid",
				outstanding_amount=0,
				grand_total=4,
				bill_no="FAC-1",
			),
			_doc(
				name="PINV-CANC",
				supplier="SUP-1",
				posting_date="2026-07-01",
				status="Cancelled",
				docstatus=2,
				outstanding_amount=100,
				grand_total=100,
				bill_no="FAC-X",
			),
		]
		result = self.mod.lookup_by_email("achats@verrier.example")
		supplier = result["suppliers"][0]
		self.assertEqual(
			set(supplier),
			{
				"doctype",
				"name",
				"supplier_name",
				"supplier_group",
				"phone",
				"mobile",
				"email",
				"disabled",
				"url",
				"match_sources",
				"contacts",
				"supplier_quotations",
				"purchase_orders",
				"purchase_invoices",
				"aggregates",
			},
		)
		self.assertEqual(supplier["supplier_quotations"][0]["name"], "SQ-1")
		names = [row["name"] for row in supplier["purchase_orders"]]
		self.assertEqual(names[0], "PO-DRAFT")
		self.assertEqual(supplier["purchase_orders"][0]["docstatus"], 0)
		self.assertNotIn("PO-CANC", names)
		self.assertNotIn("PO-OLD", names)
		self.assertIn("PO-DONE", names)
		invoice = supplier["purchase_invoices"][0]
		self.assertEqual(invoice["bill_no"], "FAC-99")
		self.assertNotIn("PINV-CANC", [row["name"] for row in supplier["purchase_invoices"]])
		self.assertEqual(
			supplier["aggregates"],
			{
				"open_purchase_order_count": 4,
				"open_purchase_order_total": 131.0,
				"amount_to_receive": 71.0,
				"unpaid_invoice_count": 2,
				"outstanding_amount": 20.0,
			},
		)

	def test_no_match_is_empty_with_create_links(self):
		result = self.mod.lookup_by_email("inconnu@exemple.fr")
		self.assertIsNone(result["match_type"])
		self.assertEqual(result["customers"], [])
		self.assertEqual(result["suppliers"], [])
		self.assertEqual(result["leads"], [])
		self.assertEqual(result["unlinked_contacts"], [])
		self.assertFalse(result["generic_domain"])
		self.assertEqual(
			result["create"]["contact"],
			f"{SITE}/app/contact/new?email_id=inconnu%40exemple.fr",
		)
		self.assertEqual(result["create"]["customer"], f"{SITE}/app/customer/new")
		self.assertEqual(
			result["create"]["supplier"],
			f"{SITE}/app/supplier/new?email_id=inconnu%40exemple.fr",
		)

	def test_generic_domain_does_not_fall_back(self):
		self.fake.tables["Contact"].append(
			_contact(
				emails=["other@gmail.com"],
				email_id="other@gmail.com",
				links=[{"link_doctype": "Customer", "link_name": "CUST-G"}],
			)
		)
		self.fake.tables["Customer"].append(_customer(name="CUST-G", email_id="other@gmail.com"))
		result = self.mod.lookup_by_email("stranger@gmail.com")
		self.assertIsNone(result["match_type"])
		self.assertTrue(result["generic_domain"])
		self.assertEqual(result["customers"], [])
		self.assertFalse(_uses_like(self.fake.calls))

	def test_domain_fallback_is_flagged_and_exact(self):
		self.fake.tables["Contact"].append(
			_contact(
				name="CONTACT-A",
				emails=["a@exemple.fr"],
				email_id="a@exemple.fr",
				links=[{"link_doctype": "Customer", "link_name": "CUST-A"}],
			)
		)
		self.fake.tables["Contact"].append(
			_contact(
				name="CONTACT-G",
				emails=["b@gmail.com"],
				email_id="b@gmail.com",
				links=[{"link_doctype": "Customer", "link_name": "CUST-G"}],
			)
		)
		self.fake.tables["Customer"] = [
			_customer(name="CUST-A", customer_name="Alpha", email_id="a@exemple.fr"),
			_customer(name="CUST-G", customer_name="Gmail", email_id="b@gmail.com"),
			_customer(name="CUST-D", customer_name="Direct", email_id="d@exemple.fr"),
			_customer(name="CUST-N", customer_name="Voisin", email_id="d@notexemple.fr"),
		]
		result = self.mod.lookup_by_email("inconnu@exemple.fr")
		self.assertEqual(result["match_type"], "domain")
		self.assertFalse(result["generic_domain"])
		self.assertEqual([row["name"] for row in result["customers"]], ["CUST-A", "CUST-D"])

	def test_domain_underscore_does_not_match_a_neighbor(self):
		self.fake.tables["Customer"] = [
			_customer(name="CUST-BAD", customer_name="Mauvais", email_id="bad@exemple.fr"),
			_customer(name="CUST-GOOD", customer_name="Bon", email_id="good@ex_mple.fr"),
		]
		result = self.mod.lookup_by_email("personne@ex_mple.fr")
		self.assertEqual(result["match_type"], "domain")
		self.assertEqual([row["name"] for row in result["customers"]], ["CUST-GOOD"])

	def test_domain_result_is_capped(self):
		for letter in "ABCDEF":
			self.fake.tables["Customer"].append(
				_customer(
					name=f"CUST-{letter}",
					customer_name=f"Client {letter}",
					email_id=f"{letter.lower()}@big.example",
				)
			)
		result = self.mod.lookup_by_email("nouveau@big.example")
		self.assertTrue(result["truncated"])
		self.assertEqual(
			[row["name"] for row in result["customers"]], ["CUST-A", "CUST-B", "CUST-C", "CUST-D", "CUST-E"]
		)

	def test_unlinked_contact_and_lead(self):
		self.fake.tables["Contact"].append(
			_contact(emails=["seul@exemple.fr"], email_id="seul@exemple.fr", links=[])
		)
		self.fake.tables["Lead"].append(
			{
				"name": "CRM-LEAD-1",
				"lead_name": "Piste Seule",
				"company_name": "Future SAS",
				"status": "Open",
				"email_id": "seul@exemple.fr",
				"phone": "0102030405",
				"mobile_no": None,
			}
		)
		result = self.mod.lookup_by_email("seul@exemple.fr")
		self.assertEqual(result["customers"], [])
		self.assertEqual(result["unlinked_contacts"][0]["name"], "CONTACT-1")
		self.assertEqual(result["leads"][0]["lead_name"], "Piste Seule")
		self.assertEqual(result["leads"][0]["status"], "Open")
		self.assertEqual(result["leads"][0]["phone"], "0102030405")
		self.assertEqual(result["leads"][0]["url"], f"{SITE}/app/lead/CRM-LEAD-1")

	def test_supplier_hidden_without_permission(self):
		self.fake.permissions["Supplier"] = False
		self.fake.tables["Contact"].append(
			_contact(
				links=[
					{"link_doctype": "Customer", "link_name": "CUST-1"},
					{"link_doctype": "Supplier", "link_name": "SUP-1"},
				]
			)
		)
		self.fake.tables["Customer"].append(_customer())
		self.fake.tables["Supplier"].append(_supplier(email_id="jean.dupont@exemple.fr"))
		result = self.mod.lookup_by_email("jean.dupont@exemple.fr")
		self.assertEqual(result["customers"][0]["name"], "CUST-1")
		self.assertEqual(result["suppliers"], [])
		self.assertFalse(any(call["doctype"] == "Supplier" for call in self.fake.calls))
		self.assertFalse(any(call["doctype"] == "Purchase Order" for call in self.fake.calls))

	def test_permission_error_on_supplier_keeps_the_customer(self):
		self.fake.raise_permission.add("Supplier")
		self.fake.tables["Contact"].append(
			_contact(
				links=[
					{"link_doctype": "Customer", "link_name": "CUST-1"},
					{"link_doctype": "Supplier", "link_name": "SUP-1"},
				]
			)
		)
		self.fake.tables["Customer"].append(_customer())
		self.fake.tables["Supplier"].append(_supplier(email_id="jean.dupont@exemple.fr"))
		result = self.mod.lookup_by_email("jean.dupont@exemple.fr")
		self.assertEqual(result["customers"][0]["name"], "CUST-1")
		self.assertEqual(result["suppliers"], [])

	def test_select_permission_is_enough_to_read(self):
		self.fake.permissions["Supplier"] = {"select"}
		self.fake.tables["Supplier"].append(_supplier(email_id="arc@verrier.example"))
		result = self.mod.lookup_by_email("arc@verrier.example")
		self.assertEqual(result["suppliers"][0]["name"], "SUP-1")


if __name__ == "__main__":
	unittest.main()


class TestGmailInternal(unittest.TestCase):
	def setUp(self):
		self.fake = FakeFrappe()
		self.fake.users = ["Paul@VerreTransparence.fr", "admin@gmail.com", None]
		self.mod = _load(self.fake)
		self.fake.tables["Customer"] = [
			_customer(name="CUST-I", customer_name="Interne", email_id="chantier@verretransparence.fr"),
		]

	def test_user_email_returns_nothing(self):
		self.fake.tables["Customer"].append(
			_customer(name="CUST-P", customer_name="Paul", email_id="paul@verretransparence.fr")
		)
		result = self.mod.lookup_by_email("Paul <paul@verretransparence.fr>")
		self.assertTrue(result["internal"])
		self.assertIsNone(result["match_type"])
		self.assertEqual(result["customers"], [])
		self.assertEqual(self.fake.calls, [])

	def test_user_domain_does_not_fall_back(self):
		result = self.mod.lookup_by_email("inconnu@verretransparence.fr")
		self.assertTrue(result["internal"])
		self.assertEqual(result["customers"], [])
		self.assertFalse(_uses_like(self.fake.calls))

	def test_exact_match_on_user_domain_still_works(self):
		result = self.mod.lookup_by_email("chantier@verretransparence.fr")
		self.assertFalse(result["internal"])
		self.assertEqual(result["match_type"], "exact")
		self.assertEqual([row["name"] for row in result["customers"]], ["CUST-I"])

	def test_user_on_webmail_does_not_block_other_webmail_senders(self):
		self.fake.tables["Customer"].append(
			_customer(name="CUST-G", customer_name="Gmail", email_id="client@gmail.com")
		)
		result = self.mod.lookup_by_email("client@gmail.com")
		self.assertFalse(result["internal"])
		self.assertEqual([row["name"] for row in result["customers"]], ["CUST-G"])

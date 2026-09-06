# Copyright (c) 2026, Verre & Transparence and contributors
# For license information, please see license.txt

"""Unit tests for Order book helpers (designation + linked purchase orders)."""

from __future__ import annotations

import sys
from datetime import date
from unittest.mock import MagicMock

if "frappe" not in sys.modules:
	frappe = MagicMock()

	def _escape_html(value):
		return (
			str(value)
			.replace("&", "&amp;")
			.replace("<", "&lt;")
			.replace(">", "&gt;")
			.replace('"', "&quot;")
		)

	def _format_date(value, fmt="dd/MM/yyyy"):
		if not value:
			return ""
		if hasattr(value, "strftime") and fmt == "dd/MM/yyyy":
			return value.strftime("%d/%m/%Y")
		return str(value)

	def _get_url_to_form(doctype, name):
		return f"/app/{doctype.lower().replace(' ', '-')}/{name}"

	frappe.utils.escape_html = _escape_html
	frappe.utils.format_date = _format_date
	frappe.utils.get_url_to_form = _get_url_to_form
	frappe.utils.getdate = lambda d: d
	frappe.utils.nowdate = lambda: "2026-08-31"
	frappe._ = lambda text: text
	sys.modules["frappe"] = frappe
	sys.modules["frappe.utils"] = frappe.utils

from vt_internal.vt_internal.report.order_book.order_book import (  # noqa: E402
	format_purchase_orders_html,
	get_columns,
	get_customer_designations,
	get_data,
	index_purchase_orders,
)


def test_client_column_uses_customer_name_not_customer_id():
	client_col = next(c for c in get_columns() if c["label"] == "Client" or c["fieldname"] == "customer_name")
	assert client_col["fieldname"] == "customer_name"
	assert client_col["fieldtype"] == "Data"
	po_col = next(c for c in get_columns() if c["fieldname"] == "purchase_orders")
	assert po_col["fieldtype"] == "HTML"


def test_index_purchase_orders_links_via_sales_order_and_project():
	rows = [
		{
			"sales_order": "SO-1",
			"project": "PROJ-A",
			"purchase_order": "PO-SG",
			"supplier_name": "Saint-Gobain",
			"supplier": "SAINTGOBAIN2601",
			"schedule_date": date(2026, 9, 15),
			"item_schedule_date": date(2026, 9, 10),
		},
		{
			"sales_order": "",
			"project": "PROJ-A",
			"purchase_order": "PO-AGC",
			"supplier_name": "AGC Glass",
			"supplier": "AGCGLASS2602",
			"schedule_date": None,
			"item_schedule_date": date(2026, 9, 22),
		},
		{
			"sales_order": "SO-OTHER",
			"project": "PROJ-B",
			"purchase_order": "PO-OTHER",
			"supplier_name": "Other",
			"supplier": "OTHER",
			"schedule_date": date(2026, 8, 1),
			"item_schedule_date": None,
		},
	]
	indexed = index_purchase_orders(
		rows,
		so_names=["SO-1", "SO-2"],
		project_to_sos={"PROJ-A": ["SO-1", "SO-2"]},
	)

	assert [po["name"] for po in indexed["SO-1"]] == ["PO-SG", "PO-AGC"]
	assert indexed["SO-1"][0]["supplier_name"] == "Saint-Gobain"
	assert indexed["SO-1"][0]["schedule_date"] == date(2026, 9, 15)
	# Header date missing → fall back to item schedule_date
	assert indexed["SO-1"][1]["schedule_date"] == date(2026, 9, 22)
	# Project-only PO is attached to every SO of that chantier
	assert [po["name"] for po in indexed["SO-2"]] == ["PO-AGC"]
	assert indexed["SO-2"][0]["supplier_name"] == "AGC Glass"


def test_index_purchase_orders_dedupes_same_po_on_one_row():
	rows = [
		{
			"sales_order": "SO-1",
			"project": "PROJ-A",
			"purchase_order": "PO-1",
			"supplier_name": "Saint-Gobain",
			"supplier": "SG",
			"schedule_date": date(2026, 9, 15),
			"item_schedule_date": date(2026, 9, 15),
		},
		{
			"sales_order": "SO-1",
			"project": "PROJ-A",
			"purchase_order": "PO-1",
			"supplier_name": "Saint-Gobain",
			"supplier": "SG",
			"schedule_date": date(2026, 9, 15),
			"item_schedule_date": date(2026, 9, 20),
		},
	]
	indexed = index_purchase_orders(rows, ["SO-1"], {"PROJ-A": ["SO-1"]})
	assert len(indexed["SO-1"]) == 1


def test_format_html_shows_supplier_and_date_click_opens_po():
	html = format_purchase_orders_html([
		{"name": "ACH-00012", "supplier_name": "Saint-Gobain", "schedule_date": date(2026, 9, 15)},
		{"name": "ACH-00013", "supplier_name": "AGC Glass", "schedule_date": date(2026, 9, 22)},
	])

	assert ">Saint-Gobain</a>" in html
	assert ">AGC Glass</a>" in html
	assert ">ACH-00012</a>" not in html
	assert ">ACH-00013</a>" not in html
	assert "15/09/2026" in html
	assert "22/09/2026" in html
	assert "frappe.set_route('Form', 'Purchase Order', \"ACH-00012\")" in html
	assert "frappe.set_route('Form', 'Purchase Order', \"ACH-00013\")" in html
	assert 'href="/app/purchase-order/ACH-00012"' in html
	assert 'title="ACH-00012"' in html


def test_format_purchase_orders_html_empty():
	assert format_purchase_orders_html([]) == ""
	assert format_purchase_orders_html(None) == ""


def test_get_data_uses_customer_designation_not_customer_id():
	sales_orders = [
		{
			"name": "SO-1",
			"customer": "MIROITERIEAVIGNON2608",
			"customer_name": "Miroiterie Avignon SAS",
			"status": "To Deliver and Bill",
			"transaction_date": date(2026, 8, 1),
			"delivery_date": date(2026, 9, 1),
			"reference_piece": "REF-1",
			"custom_responsable_du_devis": None,
			"custom_labour_hours": 4,
			"total": 1000,
			"per_billed": 0,
			"custom_construction_status": "",
			"per_delivered": 0,
			"skip_delivery_note": 0,
			"grand_total": 1200,
			"custom_statut_fiche_de_travail": "",
			"custom_per_received": 0,
			"custom_payment_request_status": "",
			"project": "PROJ-1",
		}
	]
	customers = [{"name": "MIROITERIEAVIGNON2608", "customer_name": "Miroiterie Avignon *"}]

	import vt_internal.vt_internal.report.order_book.order_book as mod

	orig_get_list = mod.frappe.get_list
	orig_sql = mod.frappe.db.sql
	orig_nowdate = mod.nowdate
	orig_getdate = mod.getdate

	def fake_get_list(doctype, *args, **kwargs):
		if doctype == "Sales Order":
			return sales_orders
		if doctype == "Customer":
			return customers
		if doctype == "Event":
			return []
		return []

	mod.frappe.get_list = fake_get_list
	mod.frappe.db.sql = lambda *args, **kwargs: []
	mod.nowdate = lambda: date(2026, 8, 31)
	mod.getdate = lambda d: d if isinstance(d, date) else date.fromisoformat(str(d))
	try:
		rows = get_data({})
	finally:
		mod.frappe.get_list = orig_get_list
		mod.frappe.db.sql = orig_sql
		mod.nowdate = orig_nowdate
		mod.getdate = orig_getdate

	assert len(rows) == 1
	# Live Customer.customer_name (désignation), not the generated Customer.name
	assert rows[0]["customer_name"] == "Miroiterie Avignon *"
	assert rows[0]["customer_name"] != "MIROITERIEAVIGNON2608"
	assert rows[0]["remaining_amount"] == 1000
	assert rows[0]["custom_labour_hours"] == 4


def test_get_customer_designations_maps_id_to_display_name():
	import vt_internal.vt_internal.report.order_book.order_book as mod

	orig = mod.frappe.get_list
	mod.frappe.get_list = lambda *args, **kwargs: [
		{"name": "DUPONTJEAN2608", "customer_name": "Jean Dupont"},
	]
	try:
		assert get_customer_designations(["DUPONTJEAN2608"]) == {"DUPONTJEAN2608": "Jean Dupont"}
		assert get_customer_designations([]) == {}
	finally:
		mod.frappe.get_list = orig

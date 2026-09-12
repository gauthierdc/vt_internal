# Copyright (c) 2026, Verre & Transparence and contributors
# For license information, please see license.txt

"""Unit tests for the planning-oriented Order book (Carnet de commande)."""

from __future__ import annotations

import sys
import unittest
from datetime import date, datetime
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
		if hasattr(value, "strftime"):
			if fmt == "dd/MM/yyyy":
				return value.strftime("%d/%m/%Y")
			if fmt == "dd/MM":
				return value.strftime("%d/%m")
		return str(value)

	def _getdate(value):
		if value is None:
			return None
		if isinstance(value, datetime):
			return value.date()
		if isinstance(value, date):
			return value
		return date.fromisoformat(str(value)[:10])

	frappe.utils.escape_html = _escape_html
	frappe.utils.format_date = _format_date
	frappe.utils.getdate = _getdate
	frappe.utils.nowdate = lambda: "2026-09-09"
	frappe._ = lambda text: text
	sys.modules["frappe"] = frappe
	sys.modules["frappe.utils"] = frappe.utils

from vt_internal.vt_internal.report.order_book.order_book import (  # noqa: E402
	as_list,
	build_summary,
	event_kind,
	format_events_badges,
	format_pending_arcs_html,
	get_columns,
	get_customer_designations,
	get_data,
	index_pending_arcs,
	is_arc_pending,
	looks_like_accounting_code,
	order_matches_managers,
	parse_manager_filter,
	resolve_customer_display_name,
)

VISIBLE_FIELDNAMES = [
	"name",
	"customer_name",
	"status",
	"custom_construction_status",
	"pending_arcs",
	"evenements",
	"reference_piece",
	"remaining_amount",
	"total",
	"delivery_date",
	"hours_total",
	"hours_solde",
	"age",
	"construction_manager",
]


def test_column_order_matches_etienne_layout():
	cols = [c["fieldname"] for c in get_columns() if not c.get("hidden")]
	assert cols == VISIBLE_FIELDNAMES
	labels = {c["fieldname"]: c["label"] for c in get_columns() if not c.get("hidden")}
	assert labels["pending_arcs"] == "ARC en cours et date de réception"
	assert labels["hours_total"] == "Nombre d'h total"
	assert labels["hours_solde"] == "Nombre d'h solde"
	assert labels["construction_manager"] == "Responsable du chantier"
	# Events sit left of référence / money columns.
	assert cols.index("evenements") < cols.index("reference_piece")
	assert cols.index("pending_arcs") < cols.index("evenements")
	assert cols.index("evenements") < cols.index("age")


def test_client_column_is_data_not_customer_link():
	client_col = next(c for c in get_columns() if c["fieldname"] == "customer_name")
	assert client_col["fieldtype"] == "Data"
	assert client_col["label"] == "Client"


def test_looks_like_accounting_code():
	assert looks_like_accounting_code("41100012")
	assert looks_like_accounting_code("04-DUPONT")
	assert looks_like_accounting_code("123 Client")
	assert not looks_like_accounting_code("Miroiterie Avignon")
	assert not looks_like_accounting_code("MIROITERIEAVIGNON2608")
	assert not looks_like_accounting_code("")
	assert not looks_like_accounting_code(None)


def test_resolve_customer_display_name_prefers_live_designation():
	designations = {"41100012": "Miroiterie Avignon *", "MIROITERIEAVIGNON2608": "Jean Dupont"}
	assert (
		resolve_customer_display_name("41100012", "41100012", designations) == "Miroiterie Avignon *"
	)
	assert (
		resolve_customer_display_name("MIROITERIEAVIGNON2608", "Miroiterie Avignon SAS", designations)
		== "Jean Dupont"
	)
	# No live fiche: use SO.customer_name if it is not an accounting code.
	assert resolve_customer_display_name("41100012", "Patrick Autran", {}) == "Patrick Autran"
	# Last resort: accounting-looking id only if nothing else exists.
	assert resolve_customer_display_name("41100012", None, {}) == "41100012"


def test_as_list_and_parse_manager_filter():
	assert as_list(None) == []
	assert as_list("alice@example.com") == ["alice@example.com"]
	assert as_list("alice@example.com,bob@example.com") == ["alice@example.com", "bob@example.com"]
	assert as_list('["alice@example.com","bob@example.com"]') == [
		"alice@example.com",
		"bob@example.com",
	]
	assert as_list(["alice@example.com", "", "bob@example.com"]) == [
		"alice@example.com",
		"bob@example.com",
	]

	filters = {
		"construction_managers": ["alice@example.com", "bob@example.com"],
		"custom_construction_manager": "legacy@example.com",
		"company": "MAV",
	}
	assert parse_manager_filter(filters) == ["alice@example.com", "bob@example.com"]
	assert "construction_managers" not in filters
	assert "custom_construction_manager" not in filters
	assert filters["company"] == "MAV"

	legacy = {"custom_construction_manager": "alice@example.com"}
	assert parse_manager_filter(legacy) == ["alice@example.com"]


def test_order_matches_managers_prefers_project_cm():
	order = {"project": "PROJ-A", "custom_construction_manager": "so@example.com"}
	project_managers = {"PROJ-A": "alice@example.com"}
	assert order_matches_managers(order, project_managers, ["alice@example.com"])
	assert not order_matches_managers(order, project_managers, ["bob@example.com"])
	# Project CM wins over the Sales Order field.
	assert not order_matches_managers(order, project_managers, ["so@example.com"])
	# SO-level fallback when project has no CM.
	assert order_matches_managers(order, {}, ["so@example.com"])
	assert order_matches_managers(order, project_managers, [])


def test_is_arc_pending():
	assert is_arc_pending({"qty": 10, "received_qty": 2, "per_received": 20, "status": "To Receive"})
	assert not is_arc_pending({"qty": 10, "received_qty": 10, "per_received": 90, "status": "To Receive"})
	assert not is_arc_pending({"qty": 10, "received_qty": 0, "per_received": 100, "status": "To Receive"})
	assert not is_arc_pending({"qty": 10, "received_qty": 0, "per_received": 0, "status": "Closed"})


def test_index_pending_arcs_links_via_sales_order_and_project():
	rows = [
		{
			"sales_order": "SO-1",
			"project": "PROJ-A",
			"purchase_order": "PO-SG",
			"supplier_name": "Saint-Gobain",
			"supplier": "SAINTGOBAIN2601",
			"schedule_date": date(2026, 9, 15),
			"item_schedule_date": date(2026, 9, 10),
			"per_received": 0,
			"status": "To Receive",
			"ar_valide": 0,
			"qty": 4,
			"received_qty": 0,
		},
		{
			"sales_order": "",
			"project": "PROJ-A",
			"purchase_order": "PO-AGC",
			"supplier_name": "AGC Glass",
			"supplier": "AGCGLASS2602",
			"schedule_date": None,
			"item_schedule_date": date(2026, 9, 22),
			"per_received": 40,
			"status": "To Receive",
			"ar_valide": 1,
			"qty": 2,
			"received_qty": 1,
		},
		{
			"sales_order": "SO-1",
			"project": "PROJ-A",
			"purchase_order": "PO-DONE",
			"supplier_name": "Done",
			"supplier": "DONE",
			"schedule_date": date(2026, 8, 1),
			"item_schedule_date": None,
			"per_received": 100,
			"status": "Completed",
			"ar_valide": 1,
			"qty": 1,
			"received_qty": 1,
		},
		{
			"sales_order": "SO-OTHER",
			"project": "PROJ-B",
			"purchase_order": "PO-OTHER",
			"supplier_name": "Other",
			"supplier": "OTHER",
			"schedule_date": date(2026, 8, 1),
			"item_schedule_date": None,
			"per_received": 0,
			"status": "To Receive",
			"ar_valide": 1,
			"qty": 1,
			"received_qty": 0,
		},
	]
	indexed = index_pending_arcs(
		rows,
		so_names=["SO-1", "SO-2"],
		project_to_sos={"PROJ-A": ["SO-1", "SO-2"]},
	)

	assert [po["name"] for po in indexed["SO-1"]] == ["PO-SG", "PO-AGC"]
	assert indexed["SO-1"][0]["supplier_name"] == "Saint-Gobain"
	assert indexed["SO-1"][0]["schedule_date"] == date(2026, 9, 15)
	assert indexed["SO-1"][1]["schedule_date"] == date(2026, 9, 22)
	assert [po["name"] for po in indexed["SO-2"]] == ["PO-AGC"]
	assert "PO-DONE" not in [po["name"] for po in indexed["SO-1"]]
	assert indexed.get("SO-OTHER") is None


def test_format_pending_arcs_html_supplier_date_and_overdue():
	html = format_pending_arcs_html(
		[
			{"name": "ACH-00012", "supplier_name": "Saint-Gobain", "schedule_date": date(2026, 9, 15), "ar_valide": 1},
			{"name": "ACH-00013", "supplier_name": "AGC Glass", "schedule_date": date(2026, 9, 1), "ar_valide": 0},
		],
		today=date(2026, 9, 9),
	)
	assert ">Saint-Gobain</a>" in html
	assert ">AGC Glass</a>" in html
	assert ">ACH-00012</a>" not in html
	assert "15/09/2026" in html
	assert "01/09/2026" in html
	assert "#c62828" in html  # overdue AGC
	assert "AR à valider" in html
	assert "frappe.set_route('Form', 'Purchase Order', \"ACH-00012\")" in html
	assert 'href="/app/purchase-order/ACH-00012"' in html
	assert format_pending_arcs_html([]) == ""
	assert format_pending_arcs_html(None) == ""


def test_event_kind_and_badges_distinguish_vt_vs_pose():
	assert event_kind({"custom_visite_technique": "VT-1"}) == "vt"
	assert event_kind({"custom_fiche_de_travail": "FT-1"}) == "ft"
	assert event_kind({"vt": "VT-1"}) == "vt"
	assert event_kind({}) == "event"

	html = format_events_badges(
		[
			{
				"name": "EV-VT",
				"starts_on": datetime(2026, 9, 12, 9, 0),
				"subject": "Visite Royon",
				"custom_visite_technique": "VT-1",
			},
			{
				"name": "EV-POSE",
				"starts_on": datetime(2026, 9, 14, 14, 0),
				"subject": "Pose garde-corps",
				"custom_fiche_de_travail": "FT-1",
			},
			{
				"name": "EV-OTHER",
				"starts_on": datetime(2026, 9, 1, 8, 0),
				"subject": "Point chantier",
			},
		],
		today=date(2026, 9, 9),
	)
	assert "🔍" in html and "VT" in html
	assert "📋" in html and "Pose" in html
	assert "📅" in html
	assert "order-book-event-vt" in html
	assert "order-book-event-ft" in html
	assert "#00838f" in html
	assert "#4f5bd5" in html
	assert "frappe.set_route('Form', 'Event', \"EV-VT\")" in html
	assert "opacity:0.55" in html  # past generic event
	assert format_events_badges([]) == ""


def _sample_order(**overrides):
	row = {
		"name": "SO-1",
		"customer": "41100012",
		"customer_name": "41100012",
		"status": "To Deliver and Bill",
		"transaction_date": date(2026, 8, 1),
		"delivery_date": date(2026, 9, 20),
		"reference_piece": "REF-1",
		"custom_responsable_du_devis": "devis@example.com",
		"custom_construction_manager": "so@example.com",
		"custom_labour_hours": 10,
		"total": 1000,
		"per_billed": 20,
		"custom_construction_status": "Attente verre",
		"per_delivered": 0,
		"skip_delivery_note": 0,
		"grand_total": 1200,
		"custom_statut_fiche_de_travail": "À planifier",
		"custom_per_received": 0,
		"custom_payment_request_status": "",
		"project": "PROJ-1",
	}
	row.update(overrides)
	return row


def test_get_data_uses_customer_designation_project_manager_and_hours():
	sales_orders = [_sample_order()]
	customers = [{"name": "41100012", "customer_name": "Miroiterie Avignon *"}]
	projects = [{"name": "PROJ-1", "custom_construction_manager": "alice@example.com"}]
	events = [
		{
			"name": "EV-1",
			"project": "PROJ-1",
			"starts_on": datetime(2026, 9, 12, 9, 0),
			"ends_on": datetime(2026, 9, 12, 11, 0),
			"color": None,
			"subject": "VT",
			"custom_visite_technique": "VT-1",
			"custom_fiche_de_travail": None,
		}
	]

	import vt_internal.vt_internal.report.order_book.order_book as mod

	orig_get_list = mod.frappe.get_list
	orig_get_all = mod.frappe.get_all
	orig_sql = mod.frappe.db.sql
	orig_nowdate = mod.nowdate
	orig_getdate = mod.getdate

	def fake_get_list(doctype, *args, **kwargs):
		if doctype == "Sales Order":
			return sales_orders
		if doctype == "Customer":
			return customers
		if doctype == "Event":
			return events
		return []

	def fake_get_all(doctype, *args, **kwargs):
		if doctype == "Project":
			if kwargs.get("pluck") == "name":
				return ["PROJ-1"]
			return projects
		return []

	def fake_sql(query, *args, **kwargs):
		if "tabTimesheet" in query:
			return [{"project": "PROJ-1", "hours": 3}]
		if "tabSales Order" in query and "custom_labour_hours" in query:
			return [{"project": "PROJ-1", "hours": 10}]
		return []

	mod.frappe.get_list = fake_get_list
	mod.frappe.get_all = fake_get_all
	mod.frappe.db.sql = fake_sql
	mod.nowdate = lambda: date(2026, 9, 9)
	mod.getdate = lambda d: d if isinstance(d, date) and not isinstance(d, datetime) else (
		d.date() if isinstance(d, datetime) else date.fromisoformat(str(d)[:10])
	)
	try:
		rows = get_data({})
	finally:
		mod.frappe.get_list = orig_get_list
		mod.frappe.get_all = orig_get_all
		mod.frappe.db.sql = orig_sql
		mod.nowdate = orig_nowdate
		mod.getdate = orig_getdate

	assert len(rows) == 1
	row = rows[0]
	assert row["customer_name"] == "Miroiterie Avignon *"
	assert row["customer_name"] != "41100012"
	assert row["remaining_amount"] == 800
	assert row["hours_total"] == 10
	assert row["hours_solde"] == 7
	assert row["construction_manager"] == "alice@example.com"
	assert row["construction_manager"] != "devis@example.com"
	assert "🔍" in row["evenements"]
	assert "order-book-event-vt" in row["evenements"]
	assert row["age"] == 39


def test_get_data_filters_multiple_construction_managers():
	sales_orders = [
		_sample_order(name="SO-ALICE", project="PROJ-A", custom_construction_manager="other@example.com"),
		_sample_order(name="SO-BOB", project="PROJ-B", custom_construction_manager="bob@example.com"),
		_sample_order(name="SO-NONE", project="PROJ-C", custom_construction_manager="nobody@example.com"),
	]

	import vt_internal.vt_internal.report.order_book.order_book as mod

	orig_get_list = mod.frappe.get_list
	orig_get_all = mod.frappe.get_all
	orig_sql = mod.frappe.db.sql

	def fake_get_list(doctype, *args, **kwargs):
		if doctype == "Sales Order":
			return sales_orders
		return []

	def fake_get_all(doctype, *args, **kwargs):
		if doctype == "Project":
			if kwargs.get("pluck") == "name":
				return ["PROJ-A"]
			return [
				{"name": "PROJ-A", "custom_construction_manager": "alice@example.com"},
				{"name": "PROJ-B", "custom_construction_manager": "bob@example.com"},
				{"name": "PROJ-C", "custom_construction_manager": "carol@example.com"},
			]
		return []

	mod.frappe.get_list = fake_get_list
	mod.frappe.get_all = fake_get_all
	mod.frappe.db.sql = lambda *args, **kwargs: []
	try:
		rows = get_data({"construction_managers": ["alice@example.com", "bob@example.com"]})
	finally:
		mod.frappe.get_list = orig_get_list
		mod.frappe.get_all = orig_get_all
		mod.frappe.db.sql = orig_sql

	assert [r["name"] for r in rows] == ["SO-ALICE", "SO-BOB"]
	assert {r["construction_manager"] for r in rows} == {"alice@example.com", "bob@example.com"}


def test_get_customer_designations_maps_id_to_display_name():
	import vt_internal.vt_internal.report.order_book.order_book as mod

	orig = mod.frappe.get_list
	mod.frappe.get_list = lambda *args, **kwargs: [
		{"name": "41100012", "customer_name": "Jean Dupont"},
	]
	try:
		assert get_customer_designations(["41100012"]) == {"41100012": "Jean Dupont"}
		assert get_customer_designations([]) == {}
	finally:
		mod.frappe.get_list = orig


def test_build_summary_cards():
	message, pills = build_summary(
		[
			{
				"remaining_amount": 1500,
				"hours_total": 10,
				"hours_solde": 4,
				"pending_arcs": '<div style="margin:2px 0;">PO</div>',
				"evenements": '<span class="badge order-book-event order-book-event-vt">VT</span>',
			}
		]
	)
	assert "Commandes" in message
	assert "Reste à facturer" in message
	assert "ARC en cours" in message
	assert "1 500" in message or "2 k€" in message or "1500" in message
	assert pills[0]["value"] == 1
	assert pills[1]["value"] == 10
	assert pills[2]["value"] == 1500


class TestOrderBook(unittest.TestCase):
	def test_column_order_matches_etienne_layout(self):
		test_column_order_matches_etienne_layout()

	def test_client_column_is_data_not_customer_link(self):
		test_client_column_is_data_not_customer_link()

	def test_looks_like_accounting_code(self):
		test_looks_like_accounting_code()

	def test_resolve_customer_display_name_prefers_live_designation(self):
		test_resolve_customer_display_name_prefers_live_designation()

	def test_as_list_and_parse_manager_filter(self):
		test_as_list_and_parse_manager_filter()

	def test_order_matches_managers_prefers_project_cm(self):
		test_order_matches_managers_prefers_project_cm()

	def test_is_arc_pending(self):
		test_is_arc_pending()

	def test_index_pending_arcs_links_via_sales_order_and_project(self):
		test_index_pending_arcs_links_via_sales_order_and_project()

	def test_format_pending_arcs_html_supplier_date_and_overdue(self):
		test_format_pending_arcs_html_supplier_date_and_overdue()

	def test_event_kind_and_badges_distinguish_vt_vs_pose(self):
		test_event_kind_and_badges_distinguish_vt_vs_pose()

	def test_get_data_uses_customer_designation_project_manager_and_hours(self):
		test_get_data_uses_customer_designation_project_manager_and_hours()

	def test_get_data_filters_multiple_construction_managers(self):
		test_get_data_filters_multiple_construction_managers()

	def test_get_customer_designations_maps_id_to_display_name(self):
		test_get_customer_designations_maps_id_to_display_name()

	def test_build_summary_cards(self):
		test_build_summary_cards()


if __name__ == "__main__":
	unittest.main()

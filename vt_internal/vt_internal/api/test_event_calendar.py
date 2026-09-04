# Copyright (c) 2026, Verre & Transparence and contributors
# Tests unitaires de l'agrégation sidebar (sans site Frappe).

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

if "frappe" not in sys.modules:
	sys.modules["frappe"] = MagicMock()

_MODULE_PATH = Path(__file__).with_name("event_calendar.py")
_SPEC = importlib.util.spec_from_file_location("vt_event_calendar_api", _MODULE_PATH)
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)

build_employee_rows = _MOD.build_employee_rows
DEFAULT_COLOR = _MOD.DEFAULT_COLOR
UNASSIGNED_COLOR = _MOD.UNASSIGNED_COLOR
UNASSIGNED_LABEL = _MOD.UNASSIGNED_LABEL


class TestBuildEmployeeRows(unittest.TestCase):
	def test_groups_by_employee_and_unassigned(self):
		events = [
			{"custom_employé": "EMP-001", "color": "#111111"},
			{"custom_employé": "EMP-001", "color": "#111111"},
			{"custom_employé": "EMP-002", "color": "#222222"},
			{"custom_employé": "", "color": "#FFEE00"},
			{"custom_employé": None, "color": "#FFEE00"},
		]
		details = {
			"EMP-001": {"employee_name": "Alice Martin", "custom_couleur": "#aabbcc"},
			"EMP-002": {"employee_name": "Bob Durand", "custom_couleur": "#ddeeff"},
		}

		rows = build_employee_rows(events, details)
		by_name = {r["name"]: r for r in rows}

		self.assertEqual(set(by_name), {"EMP-001", "EMP-002", ""})
		self.assertEqual(by_name["EMP-001"]["employee_name"], "Alice Martin")
		self.assertEqual(by_name["EMP-001"]["color"], "#aabbcc")
		self.assertEqual(by_name["EMP-001"]["event_count"], 2)
		self.assertEqual(by_name["EMP-002"]["event_count"], 1)
		self.assertEqual(by_name[""]["employee_name"], UNASSIGNED_LABEL)
		self.assertEqual(by_name[""]["color"], UNASSIGNED_COLOR)
		self.assertEqual(by_name[""]["event_count"], 2)

	def test_falls_back_to_event_color_and_id(self):
		events = [{"custom_employé": "EMP-009", "color": "#010101"}]
		rows = build_employee_rows(events, {})
		self.assertEqual(rows[0]["employee_name"], "EMP-009")
		self.assertEqual(rows[0]["color"], "#010101")

	def test_default_color_when_nothing_known(self):
		events = [{"custom_employé": "EMP-010"}]
		rows = build_employee_rows(events, {})
		self.assertEqual(rows[0]["color"], DEFAULT_COLOR)

	def test_sorts_names_then_unassigned_last(self):
		events = [
			{"custom_employé": "E2"},
			{"custom_employé": ""},
			{"custom_employé": "E1"},
		]
		details = {
			"E1": {"employee_name": "Zoé"},
			"E2": {"employee_name": "Alain"},
		}
		rows = build_employee_rows(events, details)
		self.assertEqual([r["employee_name"] for r in rows], ["Alain", "Zoé", UNASSIGNED_LABEL])

	def test_empty_events(self):
		self.assertEqual(build_employee_rows([], {}), [])
		self.assertEqual(build_employee_rows(None, None), [])


if __name__ == "__main__":
	unittest.main()

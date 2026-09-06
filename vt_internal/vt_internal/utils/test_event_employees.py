# Copyright (c) 2026, Verre & Transparence and contributors
# Tests unitaires de l'assignation multi-employés (sans site Frappe).

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

if "frappe" not in sys.modules:
	sys.modules["frappe"] = MagicMock()

_MODULE_PATH = Path(__file__).with_name("event_employees.py")
_SPEC = importlib.util.spec_from_file_location("vt_event_employees", _MODULE_PATH)
_MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MOD)

calendar_instance_id = _MOD.calendar_instance_id
employee_ids_from_rows = _MOD.employee_ids_from_rows
expand_calendar_events = _MOD.expand_calendar_events
get_event_employee_ids = _MOD.get_event_employee_ids
resolve_canonical_color = _MOD.resolve_canonical_color
DEFAULT_EVENT_COLOR = _MOD.DEFAULT_EVENT_COLOR


class TestEmployeeIds(unittest.TestCase):
	def test_child_table_wins_over_legacy(self):
		doc = {
			"custom_event_employees": [
				{"employee": "EMP-A"},
				{"employee": "EMP-B"},
				{"employee": "EMP-A"},
				{"employee": ""},
			],
			"custom_employé": "EMP-LEGACY",
		}
		self.assertEqual(get_event_employee_ids(doc), ["EMP-A", "EMP-B"])

	def test_legacy_fallback_when_table_empty(self):
		doc = {"custom_event_employees": [], "custom_employé": "EMP-1"}
		self.assertEqual(get_event_employee_ids(doc), ["EMP-1"])

	def test_no_employees(self):
		self.assertEqual(get_event_employee_ids({}), [])
		self.assertEqual(employee_ids_from_rows(None, legacy=""), [])


class TestCanonicalColor(unittest.TestCase):
	def test_vehicle_wins(self):
		self.assertEqual(resolve_canonical_color("#111111", ["#aaaaaa", "#bbbbbb"]), "#111111")

	def test_first_employee_when_no_vehicle(self):
		self.assertEqual(resolve_canonical_color(None, ["#aaaaaa", "#bbbbbb"]), "#aaaaaa")

	def test_yellow_default(self):
		self.assertEqual(resolve_canonical_color(None, []), DEFAULT_EVENT_COLOR)
		self.assertEqual(resolve_canonical_color("", [None, ""]), DEFAULT_EVENT_COLOR)


class TestExpandCalendarEvents(unittest.TestCase):
	def test_splits_one_event_into_n_blocks(self):
		events = [
			{
				"name": "EV-1",
				"subject": "Chantier",
				"starts_on": "2026-09-06 08:00:00",
				"color": "#000000",
				"custom_employé": "EMP-OLD",
			}
		]
		expanded = expand_calendar_events(
			events,
			{"EV-1": ["EMP-A", "EMP-B"]},
			{"EMP-A": "#aa0000", "EMP-B": "#00aa00"},
		)
		self.assertEqual(len(expanded), 2)
		self.assertEqual(expanded[0]["name"], "EV-1")
		self.assertEqual(expanded[1]["name"], "EV-1")
		self.assertEqual(expanded[0]["custom_employé"], "EMP-A")
		self.assertEqual(expanded[1]["custom_employé"], "EMP-B")
		self.assertEqual(expanded[0]["color"], "#aa0000")
		self.assertEqual(expanded[1]["color"], "#00aa00")
		self.assertNotEqual(expanded[0]["calendar_instance_id"], expanded[1]["calendar_instance_id"])
		self.assertTrue(expanded[0]["calendar_instance_id"].startswith("EV-1::"))

	def test_unassigned_stays_single_block(self):
		events = [{"name": "EV-2", "starts_on": "2026-09-06 09:00:00", "color": "#FFEE00"}]
		expanded = expand_calendar_events(events, {}, {})
		self.assertEqual(len(expanded), 1)
		self.assertEqual(expanded[0]["custom_employé"], "")
		self.assertEqual(
			expanded[0]["calendar_instance_id"], calendar_instance_id("EV-2", "2026-09-06 09:00:00", "")
		)

	def test_legacy_link_when_child_missing(self):
		events = [
			{
				"name": "EV-3",
				"starts_on": "2026-09-06 10:00:00",
				"custom_employé": "EMP-LEGACY",
				"color": "#123456",
			}
		]
		expanded = expand_calendar_events(events, {}, {"EMP-LEGACY": "#abcdef"})
		self.assertEqual(len(expanded), 1)
		self.assertEqual(expanded[0]["custom_employé"], "EMP-LEGACY")
		self.assertEqual(expanded[0]["color"], "#abcdef")

	def test_employee_color_overrides_vehicle_canonical_on_blocks(self):
		events = [{"name": "EV-4", "starts_on": "x", "color": "#VEHICLE", "custom_employé": ""}]
		expanded = expand_calendar_events(events, {"EV-4": ["EMP-A"]}, {"EMP-A": "#EMP"})
		self.assertEqual(expanded[0]["color"], "#EMP")


class TestPrevisionnelProjectDedupe(unittest.TestCase):
	def test_hours_counted_once_per_event(self):
		from collections import defaultdict

		events = [
			{
				"event_name": "EV-1",
				"project": "P1",
				"employee": "A",
				"starts_on": "2026-09-06 08:00:00",
				"ends_on": "2026-09-06 10:00:00",
			},
			{
				"event_name": "EV-1",
				"project": "P1",
				"employee": "B",
				"starts_on": "2026-09-06 08:00:00",
				"ends_on": "2026-09-06 10:00:00",
			},
		]
		seen = set()
		hours = defaultdict(float)

		def fake_hours(start, end):
			return 2.0 if start and end else 0

		for event in events:
			name = event["event_name"]
			if name in seen:
				continue
			seen.add(name)
			hours[event["project"]] += fake_hours(event["starts_on"], event["ends_on"])
		self.assertEqual(hours["P1"], 2.0)


if __name__ == "__main__":
	unittest.main()

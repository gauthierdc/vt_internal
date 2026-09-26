# Copyright (c) 2026, Verre & Transparence and contributors
# Tests unitaires du rappel SMS J-1 (sans site Frappe).

import importlib
import sys
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _get_datetime(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    return datetime.strptime(str(value)[:19], "%Y-%m-%d %H:%M:%S")


def _install_frappe_stub():
    if "frappe" in sys.modules and not isinstance(sys.modules["frappe"], MagicMock):
        return
    frappe_mod = MagicMock()
    utils_mod = MagicMock()
    utils_mod.get_datetime = _get_datetime
    frappe_mod.utils = utils_mod
    sys.modules["frappe"] = frappe_mod
    sys.modules["frappe.utils"] = utils_mod
    sys.modules["frappe.core"] = MagicMock()
    sys.modules["frappe.core.doctype"] = MagicMock()
    sys.modules["frappe.core.doctype.sms_settings"] = MagicMock()
    sys.modules["frappe.core.doctype.sms_settings.sms_settings"] = MagicMock()


_install_frappe_stub()

# Recharge si un import partiel a eu lieu avant le stub.
if "vt_internal.vt_internal.tasks.rappel_intervention" in sys.modules:
    rappel = importlib.reload(sys.modules["vt_internal.vt_internal.tasks.rappel_intervention"])
else:
    rappel = importlib.import_module("vt_internal.vt_internal.tasks.rappel_intervention")

build_sms_message = rappel.build_sms_message
default_envoyer_sms_for_company = rappel.default_envoyer_sms_for_company
_context_for_event = rappel._context_for_event
_is_morning_slot = rappel._is_morning_slot
_primary_employee = rappel._primary_employee
_telephone_technicien = rappel._telephone_technicien

MAV = "Miroiterie Avignonnaise"
VS = "Vitrerie Stéphanoise"
DATE = "samedi 26 septembre 2026"


class TestDefaultsAndTemplates(unittest.TestCase):
    def test_company_defaults(self):
        for company in (MAV, VS, "Autre", None, ""):
            self.assertEqual(default_envoyer_sms_for_company(company), 1)

    def test_pose_has_no_technician_phone(self):
        morning = build_sms_message(
            kind="pose", societe=MAV, date_lettres=DATE, is_morning=True, telephone_tech="06 00 00 00 00"
        )
        afternoon = build_sms_message(
            kind="pose", societe=VS, date_lettres=DATE, is_morning=False
        )
        self.assertIn("entre 8h et 12h30", morning)
        self.assertIn("entre 13h et 17h", afternoon)
        self.assertNotIn("joindre", morning)
        self.assertNotIn("06 00 00 00 00", morning)
        self.assertIn(MAV, morning)
        self.assertIn(f"le {DATE}", morning)

    def test_vt_phone_sentence_only_when_present(self):
        with_phone = build_sms_message(
            kind="vt",
            societe="VT Riviera",
            date_lettres=DATE,
            is_morning=True,
            telephone_tech="06 12 34 56 78",
        )
        without = build_sms_message(
            kind="vt",
            societe=VS,
            date_lettres=DATE,
            is_morning=False,
            telephone_tech=None,
        )
        self.assertIn("visite technique", with_phone)
        self.assertIn("06 12 34 56 78", with_phone)
        self.assertNotIn("joindre", without)
        self.assertIn("entre 13h et 17h", without)

    def test_morning_slot_rules(self):
        self.assertTrue(_is_morning_slot({"starts_on": "2026-09-26 12:59:00", "all_day": 0}))
        self.assertFalse(_is_morning_slot({"starts_on": "2026-09-26 13:00:00", "all_day": 0}))
        self.assertTrue(_is_morning_slot({"starts_on": "2026-09-26 15:00:00", "all_day": 1}))
        self.assertTrue(_is_morning_slot({"starts_on": None, "all_day": 0}))


class TestContext(unittest.TestCase):
    def setUp(self):
        self.get_value = patch.object(rappel.frappe.db, "get_value", return_value=None).start()
        self.table_exists = patch.object(rappel.frappe.db, "table_exists", return_value=False).start()
        self.sql = patch.object(rappel.frappe.db, "sql", return_value=[]).start()
        self.addCleanup(patch.stopall)

    def test_riviera_pose_and_landline_fallback(self):
        self.get_value.return_value = (
            "04 90 12 34 56",
            "client@example.com",
            "Agence Riviera",
            MAV,
        )
        event = {
            "name": "EV-1",
            "starts_on": "2026-09-26 09:15:00",
            "all_day": 0,
            "custom_company": MAV,
        }
        ctx = _context_for_event(
            event, "custom_fiche_de_travail", "Fiche de travail", "contact_email", "FT-1", DATE
        )
        self.assertEqual(ctx["societe"], "VT Riviera")
        self.assertFalse(ctx["sms_possible"])
        self.assertTrue(ctx["is_morning"])
        self.assertIsNone(ctx["telephone_tech"])

    def test_landline_without_email_is_skipped(self):
        self.get_value.return_value = ("+33490123456", None, None, VS)
        ctx = _context_for_event(
            {"starts_on": "2026-09-26 08:00:00", "all_day": 0},
            "custom_fiche_de_travail",
            "Fiche de travail",
            "contact_email",
            "FT-2",
            DATE,
        )
        self.assertIsNone(ctx)

    def test_vt_phone_from_child_employee_then_user(self):
        def get_value(doctype, name, fields=None, **kwargs):
            if doctype == "Visite Technique":
                return ("06 11 22 33 44", "a@b.c", "Centre Lyon", VS)
            if doctype == "Employee":
                return ("tech@vt.fr", "")
            if doctype == "User":
                return (None, None)
            if doctype == "Contact":
                return SimpleNamespace(mobile_no="06 99 88 77 66", phone=None)
            raise AssertionError(doctype)

        self.get_value.side_effect = get_value
        event = {
            "name": "EV-VT",
            "starts_on": "2026-09-26 14:00:00",
            "all_day": 0,
            "custom_company": VS,
            "custom_event_employees": [{"employee": "EMP-1"}],
        }
        ctx = _context_for_event(
            event, "custom_visite_technique", "Visite Technique", "email", "VT-1", DATE
        )
        self.assertEqual(ctx["societe"], VS)
        self.assertTrue(ctx["sms_possible"])
        self.assertFalse(ctx["is_morning"])
        self.assertEqual(ctx["telephone_tech"], "06 99 88 77 66")
        msg = build_sms_message(
            kind="vt",
            societe=ctx["societe"],
            date_lettres=DATE,
            is_morning=ctx["is_morning"],
            telephone_tech=ctx["telephone_tech"],
        )
        self.assertIn("06 99 88 77 66", msg)

    def test_primary_employee_falls_back_to_child_table(self):
        self.table_exists.return_value = True
        self.sql.return_value = [("EMP-CHILD",)]
        emp = _primary_employee({"name": "EV-9", "custom_employé": "EMP-LEGACY"})
        self.assertEqual(emp, "EMP-CHILD")

    def test_primary_employee_legacy_when_no_table(self):
        self.table_exists.return_value = False
        emp = _primary_employee({"name": "EV-9", "custom_employé": "EMP-LEGACY"})
        self.assertEqual(emp, "EMP-LEGACY")

    def test_technician_phone_omitted_when_missing(self):
        self.get_value.side_effect = lambda *args, **kwargs: (None, None)
        self.assertIsNone(_telephone_technicien("EMP-1"))


if __name__ == "__main__":
    unittest.main()

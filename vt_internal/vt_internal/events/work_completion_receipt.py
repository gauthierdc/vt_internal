"""Événements du document Work Completion Receipt.

Convertis depuis les Server Scripts ERP (type « DocType Event »).
Source de vérité : ce fichier (versionné). Les records DB ont été supprimés.
"""

import frappe


def before_insert(doc, method=None):
    # --- depuis Server Script « Réception de travaux letter head » (Before Insert) ---
    doc.letter_head = frappe.db.get_value("Company", doc.company, "default_letter_head")


def on_submit(doc, method=None):
    # --- depuis Server Script « Réception de travaux statut fiche de travail » (After Submit) ---
    if doc.accepted:
        fiches = frappe.get_all(
            "Fiche de travail",
            filters={"projet": doc.project},
            pluck="name"
        )

        for name in fiches:
            ft = frappe.get_doc("Fiche de travail", name)
            ft.status = "Fait"
            ft.work_completion_receipt_signed = 1
            ft.save()

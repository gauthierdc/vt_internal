"""Événements du document Purchase Invoice.

Convertis depuis les Server Scripts ERP (type « DocType Event »).
Source de vérité : ce fichier (versionné). Les records DB ont été supprimés.
"""

import frappe


def validate(doc, method=None):
    # --- depuis Server Script « À créditer sauvegarde » (Before Save) ---
    if doc.custom_mode_of_paiement:

        credit_to = frappe.db.get_value(
            "Mode of Payment Account",
            filters={
                "company": doc.company,
                "parent": doc.custom_mode_of_paiement
            },
            fieldname="custom_credit_to"
        )
        if credit_to:
            doc.credit_to = credit_to


def after_insert(doc, method=None):
    # --- depuis Server Script « À créditer » (After Insert) ---
    if doc.custom_mode_of_paiement:

        credit_to = frappe.db.get_value(
            "Mode of Payment Account",
            filters={
                "company": doc.company,
                "parent": doc.custom_mode_of_paiement
            },
            fieldname="custom_credit_to"
        )
        if credit_to:
            doc.credit_to = credit_to

    doc.save()

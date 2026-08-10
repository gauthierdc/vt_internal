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

    # Puisque on arrive pas à récuppérer la date d'échéance on fait ce truc bizarre
    # On l'écrase si elle est égale à la bill_date (ça veut dire qu'on beu)
    if doc.bill_date == doc.due_date and doc.pending_purchase_invoice:
        due_date = frappe.db.get_value('Pending Purchase Invoice', doc.pending_purchase_invoice, "due_date")
        if due_date:
            doc.due_date = due_date


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

    if doc.pending_purchase_invoice:
        due_date = frappe.db.get_value('Pending Purchase Invoice', doc.pending_purchase_invoice, "due_date")
        if due_date:
            doc.due_date = due_date

    doc.save()

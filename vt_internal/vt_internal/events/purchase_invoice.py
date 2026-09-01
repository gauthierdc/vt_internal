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
    _copy_due_date_from_pending(doc, only_if_matches_bill_date=True)


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

    _copy_due_date_from_pending(doc)

    doc.save()


def _copy_due_date_from_pending(doc, only_if_matches_bill_date=False):
    """Copy due_date from the linked Pending Purchase Invoice, if any.

    ``pending_purchase_invoice`` is a custom Link field installed by the OCR
    app (dokos-io/ocr), not by vt_internal. Frappe Documents raise
    AttributeError for fields that are not in meta, so we must not use
    ``doc.pending_purchase_invoice``. ``doc.get`` returns None when the
    field is absent (never installed, renamed, or dropped).
    """
    pending = doc.get("pending_purchase_invoice")
    if not pending:
        return
    if only_if_matches_bill_date and doc.bill_date != doc.due_date:
        return
    due_date = frappe.db.get_value("Pending Purchase Invoice", pending, "due_date")
    if due_date:
        doc.due_date = due_date

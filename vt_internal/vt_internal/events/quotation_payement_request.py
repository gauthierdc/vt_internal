"""Événements du document Quotation Payement Request.

Convertis depuis les Server Scripts ERP (type « DocType Event »).
Source de vérité : ce fichier (versionné). Les records DB ont été supprimés.
"""

import frappe


def on_payment_authorized(doc, method=None):
    # --- depuis Server Script « Paiement devis reçu » (On Payment Authorization) ---
    data = frappe.form_dict
    if data.get("reference_doctype") == "Quotation Payement Request" and data.get("reference_docname"):
        doc = frappe.get_doc(data.get("reference_doctype"), data.get("reference_docname"))
        doc.description = data
        doc.status = "Paid"

    doc.flags.ignore_permissions = True
    doc.submit()

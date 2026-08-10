"""Événements du document Payment Request.

Convertis depuis les Server Scripts ERP (type « DocType Event »).
Source de vérité : ce fichier (versionné). Les records DB ont été supprimés.
"""

import frappe


def on_submit(doc, method=None):
    # --- depuis Server Script « Demande de paiement » (After Submit) ---
    if doc.reference_doctype == "Sales Invoice":
        frappe.db.set_value("Sales Invoice", doc.reference_name, "custom_payment_request_link", doc.payment_url)

    # --- depuis Server Script « Statut de la commande client validation » (After Submit) ---
    if doc.reference_doctype == "Sales Order" and doc.reference_name:
        frappe.db.set_value("Sales Order", doc.reference_name, "custom_payment_request_status", doc.status)


def on_update_after_submit(doc, method=None):
    # --- depuis Server Script « Statut de la commande client » (After Save (Submitted Document)) ---
    if doc.reference_doctype == "Sales Order" and doc.reference_name:
        frappe.db.set_value("Sales Order", doc.reference_name, "custom_payment_request_status", doc.status)


def on_cancel(doc, method=None):
    # --- depuis Server Script « Statut de la commande client annulation » (After Cancel) ---
    if doc.reference_doctype == "Sales Order" and doc.reference_name:
        frappe.db.set_value("Sales Order", doc.reference_name, "custom_payment_request_status", "")

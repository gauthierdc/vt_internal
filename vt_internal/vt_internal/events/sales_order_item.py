"""Événements du document Sales Order Item.

Convertis depuis les Server Scripts ERP (type « DocType Event »).
Source de vérité : ce fichier (versionné). Les records DB ont été supprimés.
"""

import frappe


def on_update(doc, method=None):
    # --- depuis Server Script « Article de la commande client % reçu sauv » (After Save) ---
    sales_order = frappe.get_doc("Sales Order", doc.parent)


    items_status = [el.custom_statut_interne for el in sales_order.items]
    total_ordered = sum([ 1 if el != "" else 0 for el in items_status])
    if total_ordered > 0:
        total_received = sum([ 1 if el == "🟢" else 0 for el in items_status])
        total_started = sum([ 1 if el == "🟠" or el == "⚫️" else 0 for el in items_status])
        if total_received == 0 and total_started > 0:
            custom_per_received = 5
        else:
            custom_per_received = total_received/total_ordered*100
    else:
        custom_per_received = 0

    frappe.db.set_value("Sales Order", sales_order.name, "custom_per_received", custom_per_received)


def on_update_after_submit(doc, method=None):
    # --- depuis Server Script « Article de la commande clien % reçu » (After Save (Submitted Document)) ---
    sales_order = frappe.get_doc("Sales Order", doc.parent)


    items_status = [el.custom_statut_interne for el in sales_order.items]
    total_ordered = sum([ 1 if el != "" else 0 for el in items_status])
    if total_ordered > 0:
        total_received = sum([ 1 if el == "🟢" else 0 for el in items_status])
        total_started = sum([ 1 if el == "🟠" or el == "⚫️" else 0 for el in items_status])
        if total_received == 0 and total_started > 0:
            custom_per_received = 5
        else:
            custom_per_received = total_received/total_ordered*100
    else:
        custom_per_received = 0

    frappe.db.set_value("Sales Order", sales_order.name, "custom_per_received", custom_per_received)

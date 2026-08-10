"""Événements du document Purchase Receipt.

Convertis depuis les Server Scripts ERP (type « DocType Event »).
Source de vérité : ce fichier (versionné). Les records DB ont été supprimés.
"""

import frappe


def on_submit(doc, method=None):
    # --- depuis Server Script « Reçu d'achat validation » (After Submit) ---
    for item in doc.items:
        if item.sales_order_item:
            [ordered_qty, received_qty] = frappe.db.get_value("Purchase Order Item", item.purchase_order_item, ["qty", "received_qty"])
            if ordered_qty == received_qty:
                frappe.db.set_value('Sales Order Item', item.sales_order_item, "custom_statut_interne", "🟢")

    sales_orders_to_update = list(dict.fromkeys([item.sales_order or "" for item in doc.items]))
    for so in sales_orders_to_update:
        if so:
            run_script("Mise à jour des statuts de fabrication dans la commande", doc=frappe.get_doc("Sales Order", so))

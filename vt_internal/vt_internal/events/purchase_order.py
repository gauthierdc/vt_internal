"""Événements du document Purchase Order.

Convertis depuis les Server Scripts ERP (type « DocType Event »).
Source de vérité : ce fichier (versionné). Les records DB ont été supprimés.
"""

import frappe


def before_validate(doc, method=None):
    # --- depuis Server Script « Before validate Commande fournisseur » (Before Validate) ---
    doc.flags.ignore_pricing_rule = True


def validate(doc, method=None):
    # --- depuis Server Script « Commande fournisseur enregistrement » (Before Save) ---
    err_message = ""
    for item in doc.items:
        if not item.project:
            item.project = doc.project
        if not item.cost_center:
            item.cost_center = doc.cost_center
        cond = frappe.db.get_value("Item", item.item_code, "custom_conditionnement_à_lachat")
        if cond:
            err_message = err_message + f"- L'article {item.item_code} est conditionné à l'achat par <b>{cond}</b><br/>"
    if err_message:
        frappe.msgprint(
            msg=err_message,
            title='Attention',
        )
    doc.custom_label_reference = (frappe.db.get_value("Project Type", doc.custom_type_de_projet, "custom_id") or "") + doc.name.split("ACH")[1].replace("-", "") + (doc.reference_piece or "").upper().replace(" ", "")


def after_insert(doc, method=None):
    # --- depuis Server Script « Purchase Order automation » (After Insert) ---
    if doc.custom_auto_notify_purchase_order:
        doc.submit()


def on_submit(doc, method=None):
    # --- depuis Server Script « Commande fournisseur validation » (After Submit) ---
    for item in doc.items:
        if item.sales_order_item:
            frappe.db.set_value('Sales Order Item', item.sales_order_item, "custom_statut_interne", "🟠")

    sales_orders_to_update = list(dict.fromkeys([item.sales_order or "" for item in doc.items]))
    for so in sales_orders_to_update:
        if so:
            run_script("Mise à jour des statuts de fabrication dans la commande", doc=frappe.get_doc("Sales Order", so))


def before_update_after_submit(doc, method=None):
    # --- depuis Server Script « Commande fournisseur enregistrement validé » (Before Save (Submitted Document)) ---
    doc.custom_label_reference = (frappe.db.get_value("Project Type", doc.custom_type_de_projet, "custom_id") or "") + doc.name.split("ACH")[1].replace("-", "") + (doc.reference_piece or "").upper().replace(" ", "")

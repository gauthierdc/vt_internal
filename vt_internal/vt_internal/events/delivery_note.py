"""Événements du document Delivery Note.

Convertis depuis les Server Scripts ERP (type « DocType Event ») :
- « Date de livraison »            -> before_insert
- « Validation valide la fabrication » -> on_submit  (After Submit)
- « BL avant impression »          -> before_print (vide en prod, conservé pour mémoire)

Source de vérité : ce fichier (versionné). Les records DB ont été supprimés.
"""

import frappe


def before_insert(doc, method=None):
    for item in doc.items:
        if item.against_sales_order:
            doc.delivery_date = frappe.db.get_value(
                "Sales Order", item.against_sales_order, "delivery_date"
            )
            break

    doc.custom_follow_up_automatically = doc.custom_type_de_projet == "Enlèvement"
    if doc.custom_type_de_projet in (
        "Dépannage",
        "Chantier courant",
        "Chantier stratégique",
    ):
        doc.custom_livré = True


def on_submit(doc, method=None):
    sales_orders_to_update = list(
        dict.fromkeys([item.against_sales_order or "" for item in doc.items])
    )
    for sales_order in sales_orders_to_update:
        cartes_de_travail = frappe.db.get_list(
            "Carte de travail VT",
            {"customer_order": sales_order},
            ["name", "status"],
        )
        for c in cartes_de_travail:
            if c.status != "Fait":
                d = frappe.get_doc("Carte de travail VT", c.name)
                d.date_de_fin = frappe.utils.getdate()
                d.save()


def before_print(doc, method=None, **kwargs):
    # Le Server Script d'origine était entièrement commenté (aucun effet en prod) :
    #   sales_orders = list(dict.fromkeys(
    #       [item.against_sales_order for item in doc.items if item.against_sales_order]))
    #   for so in sales_orders:
    #       doc.delivery_date_from_sales_order = frappe.db.get_value(
    #           "Sales Order", so, "delivery_date")
    #       break
    # Conservé ici pour mémoire ; non enregistré dans doc_events (voir hooks.py).
    pass

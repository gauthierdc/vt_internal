"""Événements du document Glass manufacturing costs.

Convertis depuis les Server Scripts ERP (type « DocType Event »).
Source de vérité : ce fichier (versionné). Les records DB ont été supprimés.
"""

import frappe


def validate(doc, method=None):
    # --- depuis Server Script « Coûts de fabrication du verre » (Before Save) ---
    fbs = frappe.db.get_list("Fabrication VT", filters={
            "creation": ["between", [doc.starts_on, doc.ends_on]]
        },
        fields=["name", "largeur", "longueur", "quantity", "article"])
    qty_article = {}
    for f in fbs:
        if f.article not in qty_article:
            price = frappe.db.get_value("Item Price", {
                "item_code": f.article,
                "price_list": "Achat Standard",
                "supplier": "INTERNE"
            }, "price_list_rate") or 0
            qty_article[f.article] = {
                "surface": 0,
                "qty": 0,
                "price": price
            }
        qty_article[f.article]["surface"] = qty_article[f.article]["surface"] + int(f.largeur)/1000*int(f.longueur)/1000
        qty_article[f.article]["qty"] = qty_article[f.article]["qty"] + int(f.quantity)

    qty_article = dict(sorted(qty_article.items(), key=lambda item: item[1]["surface"], reverse = True))

    doc.total_quantity = sum([i["qty"] for i in qty_article.values()])
    doc.total_surface = sum([i["surface"] for i in qty_article.values()])
    doc.items = []
    doc.raw_material_total_price = 0
    for key, value in qty_article.items():
        doc.append('items', {
            "item": key,
            "qty": value["qty"],
            "surface": value["surface"],
            "price_per_m2": value["price"],
            "total_price": value["price"]*value["surface"]*(1+int(doc.loss_percentage)/100)
        })
        doc.raw_material_total_price = doc.raw_material_total_price + value["price"]*value["surface"]*1.2

    if doc.overhead_costs > 0:
        doc.per_glass = doc.overhead_costs/doc.total_quantity
        doc.per_surface = doc.overhead_costs/doc.total_surface

    doc.price_per_unit = (doc.overhead_costs + doc.raw_material_total_price)/doc.total_quantity
    doc.price_per_surface = (doc.overhead_costs + doc.raw_material_total_price)/doc.total_surface


def on_submit(doc, method=None):
    # --- depuis Server Script « Coûts de fabrication du verre validation » (After Submit) ---
    fbs = frappe.db.get_list("Fabrication VT", filters={
            "creation": ["between", [doc.starts_on, doc.ends_on]]
        },
        fields=["name", "quantity", "largeur", "longueur", "article"])
    for f in fbs:
        price_per_surface = (frappe.db.get_value("Item Price", {
                "item_code": f.article,
                "price_list": "Achat Standard",
                "supplier": "INTERNE"
            }, "price_list_rate") or 0)*(1+doc.loss_percentage/100)
        frappe.db.set_value("Fabrication VT", f.name, "manufacturing_costs", round(doc.per_glass*int(f.quantity) + price_per_surface*int(f.largeur)/1000*int(f.longueur)/1000,1), update_modified=False)

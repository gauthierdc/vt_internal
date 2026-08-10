"""Événements du document Production statement.

Convertis depuis les Server Scripts ERP (type « DocType Event »).
Source de vérité : ce fichier (versionné). Les records DB ont été supprimés.
"""

import frappe


def on_update(doc, method=None):
    # --- depuis Server Script « Déclaration de production » (After Save) ---
    cts = doc.values.splitlines()
    for c in cts:
        try:
            d = frappe.get_doc("Carte de travail VT", c)
        except:
            frappe.throw(f"Carte de travail introuvable {c}")
        d.date_de_fin = frappe.utils.getdate()
        d.save()

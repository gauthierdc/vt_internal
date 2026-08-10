"""Événements du document Fabrication VT.

Convertis depuis les Server Scripts ERP (type « DocType Event »).
Source de vérité : ce fichier (versionné). Les records DB ont été supprimés.
"""

import frappe


def on_update(doc, method=None):
    # --- depuis Server Script « Fabrication VT » (After Save) ---
    run_script('Mise à jour des statuts de fabrication', fabrication=doc)


def on_trash(doc, method=None):
    # --- depuis Server Script « Suppression » (Before Delete) ---
    cts = frappe.get_all('Carte de travail VT', filters={'fabrication_vt': doc.name}, fields=['name'])

    for c in cts:
        frappe.delete_doc("Carte de travail VT", c.name)

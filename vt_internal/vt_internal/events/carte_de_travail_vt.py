"""Événements du document Carte de travail VT.

Convertis depuis les Server Scripts ERP (type « DocType Event »).
Source de vérité : ce fichier (versionné). Les records DB ont été supprimés.
"""

import frappe


def validate(doc, method=None):
    # --- depuis Server Script « Carte de travail Code bar » (Before Save) ---
    doc.barcode = doc.name

    # --- depuis Server Script « Carte de travail VT » (Before Save) ---
    run_script('Mise à jour des statuts de fabrication', carte_travail=doc)

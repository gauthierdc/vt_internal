"""Événements du document Carte de travail VT.

Convertis depuis les Server Scripts ERP (type « DocType Event »).
Source de vérité : ce fichier (versionné). Les records DB ont été supprimés.
"""

import frappe

from vt_internal.vt_internal.api.fabrication import update_manufacturing_status


def validate(doc, method=None):
    # --- depuis Server Script « Carte de travail Code bar » (Before Save) ---
    doc.barcode = doc.name

    # --- depuis Server Script « Carte de travail VT » (Before Save) ---
    update_manufacturing_status(carte_travail=doc)

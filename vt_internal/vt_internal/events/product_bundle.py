"""Événements du document Product Bundle.

Convertis depuis les Server Scripts ERP (type « DocType Event »).
Source de vérité : ce fichier (versionné). Les records DB ont été supprimés.
"""

import frappe


def validate(doc, method=None):
    # --- depuis Server Script « Ouvrage avant la création » (Before Save) ---
    if not doc.custom_name:
        doc.custom_name = doc.name

"""Événements du document Payment Order.

Convertis depuis les Server Scripts ERP (type « DocType Event »).
Source de vérité : ce fichier (versionné). Les records DB ont été supprimés.
"""

import frappe


def validate(doc, method=None):
    # --- depuis Server Script « Ordre de paiement » (Before Save) ---
    doc.total_amount = sum([r.amount for r in doc.references])

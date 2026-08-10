"""Événements du document Employee.

Convertis depuis les Server Scripts ERP (type « DocType Event »).
Source de vérité : ce fichier (versionné). Les records DB ont été supprimés.
"""

import frappe


def validate(doc, method=None):
    # --- depuis Server Script « Titre employé » (Before Save) ---
    doc.employee_number = doc.first_name + " " + doc.last_name

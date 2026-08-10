"""Tâche planifiée « Close billed projects » (fréquence : Hourly).

Convertie depuis le Server Script ERP (type « Scheduler Event »).
Câblage de la fréquence dans hooks.py (scheduler_events).
Source de vérité : ce fichier (versionné). Le record DB a été supprimé.
"""

import frappe


def close_billed_projects():
    """
    Script pour fermer les projets ouverts sans commandes actives, mais seulement s'il existe au moins une commande liée (active ou non).
    - Utilise une requête SQL unique avec des sous-requêtes EXISTS/NOT EXISTS pour identifier les projets à fermer, afin de minimiser les appels DB.
    - Critères :
      - Projet status = 'Open'
      - Au moins une Sales Order liée (docstatus=1)
      - Aucune Sales Order active (per_billed < 90, status != 'Closed', docstatus=1)
    - Met à jour les projets identifiés en status = 'Completed' et expected_end_date = date actuelle.
    """

    # Requête SQL pour récupérer les noms des projets à fermer
    projects_to_close = frappe.db.sql("""
        SELECT p.name
        FROM `tabProject` p
        WHERE p.status = 'Open'
        AND EXISTS (
            SELECT 1
            FROM `tabSales Order` so
            WHERE so.project = p.name
            AND so.docstatus = 1
        )
        AND NOT EXISTS (
            SELECT 1
            FROM `tabSales Order` so
            WHERE so.project = p.name
            AND so.docstatus = 1
            AND so.per_billed < 90
            AND so.status != 'Closed'
        )
    """, as_dict=True)

    # Boucle sur les projets à fermer et mise à jour
    for proj in projects_to_close:
        project_name = proj.name
        frappe.db.set_value(
            "Project",
            project_name,
            {
                "status": "Completed",
                "expected_end_date": frappe.utils.nowdate()
            }
        )
        print(f"Projet fermé : {project_name}")

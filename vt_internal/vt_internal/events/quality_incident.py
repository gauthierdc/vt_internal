"""Événements du document Quality Incident.

Convertis depuis les Server Scripts ERP (type « DocType Event »).
Source de vérité : ce fichier (versionné). Les records DB ont été supprimés.
"""

import frappe


def validate(doc, method=None):
    # --- depuis Server Script « Incident qualité sauvegarde » (Before Save) ---

    if doc.sav:
        if not doc.object.startswith('SAV - '):
            doc.object = 'SAV - ' + doc.object
    else:
        if doc.object.startswith('SAV - '):
            doc.object = doc.object.replace('SAV - ', '', 1)


    # Coût main d'oeuvre par société
    LABOR_COST_VO = 40
    LABOR_COST = 30
    KM_COST = 0.5

    labor_cost_per_company = LABOR_COST_VO if doc.company == "Vision d'O" else LABOR_COST
    doc.labor_cost = (doc.heures_pose or 0) * labor_cost_per_company
    doc.cost_atelier = (doc.hours_atelier or 0) * LABOR_COST

    doc.costs_km = (doc.km or 0) * KM_COST

    # Coût total
    doc.total_costs = (doc.labor_cost or 0) + (doc.cost_atelier or 0) + (doc.costs_km or 0) + (doc.other_costs or 0) + (doc.cost_raw_material or 0)

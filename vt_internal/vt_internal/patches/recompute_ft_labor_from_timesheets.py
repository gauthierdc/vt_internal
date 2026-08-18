"""Recalcule time_spent / labor_costs des Fiches de travail.

Corrige les valeurs faussées par le bug d'accumulation de
`events/timesheet.py` (la clé du dict était remise à 0 à chaque ligne → seule
la dernière ligne d'une même fiche était comptée). On repart des feuilles de
temps validées (docstatus=1) et on recompose les totaux corrects en une passe.
"""

from collections import defaultdict

import frappe


def execute():
    time_spent = defaultdict(float)
    labor_costs = defaultdict(float)

    # Heures par (feuille de temps, fiche) pour les feuilles validées.
    rows = frappe.db.sql(
        """
        SELECT ts.name AS ts, ts.total_hours AS total_hours,
               ts.total_costing_amount AS total_costing_amount,
               tsd.custom_fiche_de_travail AS ft, SUM(tsd.hours) AS hours
        FROM `tabTimesheet Detail` tsd
        INNER JOIN `tabTimesheet` ts ON ts.name = tsd.parent
        WHERE ts.docstatus = 1 AND tsd.custom_fiche_de_travail IS NOT NULL
        GROUP BY ts.name, tsd.custom_fiche_de_travail
        """,
        as_dict=True,
    )

    for r in rows:
        if not r.total_hours:
            continue
        hours = frappe.utils.flt(r.hours)
        time_spent[r.ft] += hours
        labor_costs[r.ft] += (hours / r.total_hours) * frappe.utils.flt(r.total_costing_amount)

    for ft in set(time_spent) | set(labor_costs):
        frappe.db.set_value(
            "Fiche de travail", ft,
            {
                "time_spent": round(time_spent[ft], 2),
                "labor_costs": round(labor_costs[ft], 2),
            },
            update_modified=False,
        )

    frappe.db.commit()

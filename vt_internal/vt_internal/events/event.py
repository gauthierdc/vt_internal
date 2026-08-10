"""Événements du document Event.

Convertis depuis les Server Scripts ERP (type « DocType Event »).
Source de vérité : ce fichier (versionné). Les records DB ont été supprimés.
"""

import frappe


def validate(doc, method=None):
    # --- depuis Server Script « Événement avant la sauvegarde » (Before Save) ---
    color = None
    if doc.custom_vehicle:
        color = frappe.db.get_value("Vehicle", doc.custom_vehicle, "custom_couleur")
    elif doc.custom_employé:
        color = frappe.db.get_value("Employee", doc.custom_employé, "custom_couleur")
    else:
        color = "#FFEE00"
    doc.color = color


def on_update(doc, method=None):
    # --- depuis Server Script « Evénement après la sauvegarde » (After Save) ---
    fiche = doc.custom_fiche_de_travail
    project = doc.project

    fiche_name = doc.custom_fiche_de_travail
    project = doc.project

    if fiche_name:
        # Récupération de la fiche de travail et du projet associé
        fiche = frappe.get_doc(
            "Fiche de travail",
            fiche_name,
        )

        # Calcul des heures planifiées depuis tous les events liés au projet
        events = frappe.get_all(
            "Event",
            filters={"project": project},
            fields=["starts_on", "ends_on"]
        )

        total_hours = 0
        for e in events:
            if e.starts_on and e.ends_on:
                diff = frappe.utils.time_diff_in_hours(e.ends_on, e.starts_on)
                total_hours = total_hours + diff

        # Mise à jour des heures planifiées sur le projet
        if project:
            frappe.db.set_value(
                "Project",
                project,
                "custom_planned_hours",
                total_hours
            )

            # Récupération de l'estimation
            estimated = frappe.db.get_value(
                "Project",
                project,
                "custom_estimated_labor_hours"
            ) or 0

            # Arrondi des heures pour affichage
            total_rounded = round(total_hours, 1)
            estimated_rounded = round(estimated, 1)

            # Message d'alerte ou d'information
            if total_hours > estimated:
                frappe.msgprint(
                    "⚠️ Heures planifiées (" + str(total_rounded) + "h) dépassent l'estimation projet (" + str(estimated_rounded) + "h)",
                    indicator="orange",
                    alert=True
                )
            else:
                remaining = round(estimated - total_hours, 1)
                frappe.msgprint(
                    "Heures planifiées : " + str(total_rounded) + "h. Il reste " + str(remaining) + "h par rapport à l'estimation projet (" + str(estimated_rounded) + "h).",
                    indicator="green",
                    alert=True
                )
        # Passage du statut de la fiche de travail à "À faire" si nécessaire
        if fiche.status in ("En attente de fabrication", "À planifier"):
            fiche.status = "À faire"
            fiche.save()

    # --- depuis Server Script « Évènement sync » (After Save) ---
    if doc.custom_visite_technique:
        vt = frappe.db.get_value(
        	"Visite Technique", doc.custom_visite_technique, ["starts_on", "ends_on"]
        )
        if vt[0] != doc.starts_on:
        	frappe.db.set_value("Visite Technique", doc.custom_visite_technique, "starts_on", doc.starts_on)

        if vt[1] != doc.ends_on:
        	frappe.db.set_value("Visite Technique", doc.custom_visite_technique, "ends_on", doc.ends_on)


def after_delete(doc, method=None):
    # --- depuis Server Script « Evénement après la suppression » (After Delete) ---
    # Server Script - DocType Event, Before Save

    project = doc.project

    if project:
        events = frappe.get_all(
            "Event",
            filters={"project": project},
            fields=["starts_on", "ends_on"]
        )

        # Calculer la somme des heures existantes
        total_hours = 0
        for e in events:
            if e.starts_on and e.ends_on:
                total_hours = total_hours + frappe.utils.time_diff_in_hours(e.ends_on, e.starts_on)

        # Mettre à jour le projet
        frappe.db.set_value("Project", project, "custom_planned_hours", total_hours)

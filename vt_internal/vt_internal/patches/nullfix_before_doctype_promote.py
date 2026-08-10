"""Nettoie les NULL avant la promotion des DocTypes custom -> app (pre_model_sync).

En devenant DocTypes d'app, les champs Check/numériques passent en
`NOT NULL DEFAULT 0`. Si la colonne existe déjà en base (doctype custom) avec des
valeurs NULL, l'`ALTER ... MODIFY ... NOT NULL` échoue :
    MySQLdb.DataError (1265): Data truncated for column 'sav' at row 1

Ce patch tourne AVANT la synchro de schéma (`pre_model_sync`) et met à 0 toutes
les valeurs NULL des colonnes Check/numériques des 11 doctypes concernés, pour
que l'ALTER passe sans perte (0 = valeur par défaut de ces champs).

Idempotent (UPDATE ... WHERE <col> IS NULL). Sans effet si déjà migré.
"""

import json
import os

import frappe

DOCTYPES = [
    "fiche_de_travail",
    "carte_de_travail_vt",
    "quality_incident",
    "fabrication_vt",
    "bmv_settings",
    "consolidated_invoice",
    "order_satisfaction",
    "production_statement",
    "vt_objective",
    "work_completion_receipt",
    "quotation_approval",
]

# fieldtypes rendus NOT NULL DEFAULT 0 par Frappe
NON_NULLABLE_TYPES = {"Check", "Int", "Float", "Currency", "Percent", "Rating"}


def execute():
    base = frappe.get_app_path("vt_internal", "vt_internal", "doctype")
    fixed = 0

    for scrub in DOCTYPES:
        path = os.path.join(base, scrub, f"{scrub}.json")
        if not os.path.exists(path):
            continue

        with open(path, encoding="utf-8") as f:
            meta = json.load(f)

        doctype = meta.get("name")
        # NB: table_exists / get_table_columns attendent le NOM DU DOCTYPE
        # (ils préfixent "tab" en interne), pas le nom de table.
        if not frappe.db.table_exists(doctype):
            continue

        table = f"tab{doctype}"
        existing_cols = set(frappe.db.get_table_columns(doctype))

        for field in meta.get("fields", []):
            if field.get("fieldtype") not in NON_NULLABLE_TYPES:
                continue
            col = field.get("fieldname")
            if not col or col not in existing_cols:
                continue

            frappe.db.sql(
                f"UPDATE `{table}` SET `{col}` = 0 WHERE `{col}` IS NULL"
            )
            fixed += 1

    frappe.db.commit()
    frappe.logger().info(
        f"nullfix_before_doctype_promote: {fixed} colonnes nettoyées"
    )

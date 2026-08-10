"""Événements du document Customer.

Convertis depuis les Server Scripts ERP (type « DocType Event »).
Source de vérité : ce fichier (versionné). Les records DB ont été supprimés.
"""

import frappe


def before_insert(doc, method=None):
    # --- depuis Server Script « Nommage des clients » (Before Insert) ---
    excluded_characters = "!@#$%^&*()[]{};:,./<>?\|`~-=_+'"

    characters_to_replace = {
        "é": "e",
        "è": "e",
        "à": "a",
        "â": "a"
    }

    excluded_words = ["l", "le", "la", "sas", "sarl", "sasu"]

    excluded_characters_list = []
    excluded_characters_list[:0] = excluded_characters

    keys = frappe.utils.strip(doc.customer_name).replace("'", " ").split(" ")

    new_name = ""
    for key in keys:
        if key.lower() in excluded_words:
           continue

        new_name = new_name + key

    for e in excluded_characters_list:
        new_name = new_name.lower().replace(e, "")

    for char in characters_to_replace:
        new_name = new_name.lower().replace(char, characters_to_replace[char])
    new_name = new_name + frappe.utils.format_date(frappe.utils.now(), "YYMM")
    doc.name = new_name.upper()

    doc.flags.name_set = True


def validate(doc, method=None):
    # --- depuis Server Script « Client sauvegarde » (Before Save) ---
    if doc.custom_internal_status == "En compte":
        doc.vt_client_compte = 1
    else:
        doc.vt_client_compte = 0
    if doc.custom_internal_status == "En compte" and ("*" not in doc.customer_name):
        frappe.msgprint("⚠️ Un client en compte doit avoir une étoile dans son nom", title="Validation")
    if doc.custom_internal_status != "En compte" and ("*" in doc.customer_name):
        frappe.msgprint(f"⚠️ Un client {doc.custom_internal_status} ne peut pas avoir une étoile dans son nom", title="Validation")

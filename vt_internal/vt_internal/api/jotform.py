"""Endpoints webhooks formulaires externes (Jotform / Vision d'O).

Convertis depuis les Server Scripts ERP (type « API »).
URLs courtes historiques préservées via override_whitelisted_methods (hooks.py).
Source de vérité : ces fichiers (versionnés). Les records DB ont été supprimés.
"""

import frappe
import json

@frappe.whitelist()
def jotform_create_client():
    # Converti depuis le Server Script API « Jotform create client » (/api/method/jotform-create-client).
    client_doc = frappe.get_doc({
        'doctype': 'Customer',
        'customer_name': 'Miroiterie Avignon',
        'customer_type': 'Company',
    })

    client_doc.insert(ignore_if_duplicate=True)


    address_doc = frappe.get_doc({
        'doctype': 'Address',
        'address_title': '24 rue de la pépinère',
        'address_line1': '24 rue de la pépinère',
        'city': 'Avignon',
        'pincode': "84000",
        'links': [{
            'link_doctype': 'Customer',
            'link_name': client_doc.name
        }]
    })

    address_doc.insert(ignore_if_duplicate=True)


@frappe.whitelist()
def vision_do():
    # Converti depuis le Server Script API « Formulaire Vision d'O Jetform » (/api/method/vision-do).
    body = frappe.form_dict


@frappe.whitelist(allow_guest=True)
def vo_jotform():
    # Converti depuis le Server Script API « Jetform VO » (/api/method/vo-jotform).
    body = frappe.form_dict

    doc = frappe.get_doc({"doctype":"Jotform VO", "body": json.dumps(json.loads(body["rawRequest"]), indent=4)})
    doc.insert(ignore_permissions=True)
    doc.submit()
    frappe.db.commit()

    frappe.response['message'] = "test"

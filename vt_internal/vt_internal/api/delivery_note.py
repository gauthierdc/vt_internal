"""API Delivery Note.

Converti depuis le Server Script ERP (type « API ») « sms_delivery_note ».
L'URL courte historique /api/method/sms_delivery_note est préservée via
`override_whitelisted_methods` dans hooks.py (appelée par les client scripts
Form et List du Bon de livraison).
"""

import frappe
from frappe.core.doctype.sms_settings.sms_settings import send_sms


@frappe.whitelist()
def sms_delivery_note(doc_name=None):
    if not doc_name:
        frappe.throw("Le nom du bon de livraison n’a pas été fourni.")

    doc = frappe.get_doc("Delivery Note", doc_name)

    if not doc.contact_mobile:
        frappe.throw("Aucun numéro de téléphone n’est renseigné pour ce bon de livraison.")

    # Récupération du template SMS depuis la société
    sms_template = frappe.db.get_value("Company", doc.company, "custom_sms_commande_prête")
    if not sms_template:
        frappe.throw(f"Le message SMS n’a pas été défini pour la société {doc.company}.")

    # Construction du message
    try:
        sms = frappe.render_template(sms_template, {"doc": doc})
    except Exception as e:
        frappe.log_error(
            f"Erreur de rendu du template SMS pour {doc.name}: {e}", "Erreur template SMS"
        )
        frappe.throw("Erreur lors du rendu du message SMS. Vérifie que le template est correct.")

    # Envoi du SMS
    try:
        send_sms(receiver_list=[doc.contact_mobile], msg=sms)
    except Exception as e:
        frappe.throw(f"Échec de l’envoi SMS à {doc.contact_mobile} pour {doc.name} : {e}")

    # Commentaire sur le document
    frappe.get_doc(
        {
            "doctype": "Comment",
            "comment_type": "Comment",
            "comment_email": frappe.session.user,
            "reference_doctype": "Delivery Note",
            "reference_name": doc.name,
            "comment_by": frappe.session.user_fullname,
            "content": f"<u><b>SMS envoyé au {doc.contact_mobile}</b></u>: {sms}",
        }
    ).insert(ignore_permissions=True)

    # Mise à jour du champ indicateur
    doc.db_set("custom_sms_sent", 1)

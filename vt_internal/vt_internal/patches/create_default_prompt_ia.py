import frappe


def execute():
    records = [
        {
            "doctype": "Prompt IA",
            "name": "Analyse devis interne",
            "title": "Analyse devis interne",
            "prompt": (
                "Tu es un assistant interne d'une miroiterie professionnelle. "
                "Voici le contenu d'un devis client. Analyse les prestations décrites, "
                "la cohérence des prix, les éventuelles erreurs ou oublis, "
                "et donne des recommandations internes :"
            ),
        },
        {
            "doctype": "Prompt IA",
            "name": "Analyse devis client",
            "title": "Analyse devis client",
            "prompt": (
                "Voici un devis reçu pour des travaux de vitrerie. "
                "Analyse-le et dis-moi si les prestations sont bien décrites, "
                "si le prix te semble cohérent, "
                "et s'il manque des informations importantes :"
            ),
        },
    ]

    for r in records:
        if not frappe.db.exists("Prompt IA", r["name"]):
            frappe.get_doc(r).insert(ignore_permissions=True)

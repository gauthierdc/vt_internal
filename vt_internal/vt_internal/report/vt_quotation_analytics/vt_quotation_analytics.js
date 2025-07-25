frappe.query_reports["VT Quotation Analytics"] = {
    "filters": [
        {
            "fieldname": "grouped_by",
            "label": __("Groupé par"),
            "fieldtype": "Select",
            "options": ["Devis", "Secteur VT", "Assurance", "Centre de cout", "Type de projet", "Responsable du devis", "Statut de suivi"],
            "default": "Secteur VT",
            "reqd": 1
        },
        {
            "fieldname": "metric",
            "label": __("Métrique"),
            "fieldtype": "Select",
            "options": ["Montant", "Quantité de devis", "Pourcentage de relance (valeur)", "Pourcentage de relance (quantité)", "Taux de conversion (valeur)", "Taux de conversion (quantité)", "Montant attendu"],
            "default": "Montant",
            "reqd": 1
        },
        {
            "fieldname": "company",
            "label": __("Société"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company")
        },
        {
            "fieldname": "secteur_vt",
            "label": __("Secteur VT"),
            "fieldtype": "Link",
            "options": "Secteur VT"
        },
        {
            "fieldname": "assurance",
            "label": __("Assurance"),
            "fieldtype": "Link",
            "options": "Customer",
            "filters": {
                "customer_group": "Assurance"
            }
        },
        {
            "fieldname": "responsable_du_devis",
            "label": __("Responsable du devis"),
            "fieldtype": "Link",
            "options": "User"
        },
        {
            "fieldname": "centre_de_cout",
            "label": __("Centre de cout"),
            "fieldtype": "Link",
            "options": "Cost Center"
        },
        {
            "fieldname": "from_date",
            "label": __("Date de début"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": __("Date de fin"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),
            "reqd": 1
        },
        {
            "fieldname": "range",
            "label": __("Plage"),
            "fieldtype": "Select",
            "options": ["Hebdomadaire", "Mensuel", "Trimestriel", "Annuel"],
            "default": "Mensuel"
        },
    ]
};
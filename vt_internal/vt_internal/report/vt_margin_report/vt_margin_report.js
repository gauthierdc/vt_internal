frappe.query_reports["VT Margin Report"] = {
    "filters": [
        {
            "fieldname": "grouped_by",
            "label": __("Groupé par"),
            "fieldtype": "Select",
            "options": ["Project", "Company", "Cost Center", "Assurance", "Type de projet", "Secteur VT"],
            "default": "Project",
            "reqd": 1  // Rendre obligatoire si nécessaire
        },
        {
            "fieldname": "analysis_axis",
            "label": __("Axe d'analyse"),
            "fieldtype": "Select",
            "options": ["Marge globale", "Temps passé", "Achats"],
            "default": "Marge globale",
            "reqd": 1  // Rendre obligatoire si nécessaire
        },
        {
            "fieldname": "company",
            "label": __("Company"),
            "fieldtype": "Link",
            "options": "Company",
            "default": frappe.defaults.get_user_default("Company")  // Valeur par défaut : société de l'utilisateur
        },
        {
            "fieldname": "project",
            "label": __("Project"),
            "fieldtype": "Link",
            "options": "Project"
        },
        {
            "fieldname": "cost_center",
            "label": __("Cost Center"),
            "fieldtype": "Link",
            "options": "Cost Center"
        },
        {
            "fieldname": "insurance",
            "label": __("Assurance"),
            "fieldtype": "Link",
            "options": "Customer",
            "filters": {
                "customer_group": "Assurance"
            }
        },
        {
            "fieldname": "project_type",
            "label": __("Type de projet"),
            "fieldtype": "Link",
            "options": "Project Type"
        },
        {
            "fieldname": "secteur_vt",
            "label": __("Secteur VT"),
            "fieldtype": "Link",
            "options": "Secteur VT"
        },
        {
            "fieldname": "quotation_owner",
            "label": __("Responsable du devis"),
            "fieldtype": "Link",
            "options": "User"
        },
        {
            "fieldname": "from_date",
            "label": __("Date de début"),
            "fieldtype": "Date",
            "default": frappe.datetime.add_months(frappe.datetime.get_today(), -1),  // Par défaut : il y a un mois
            "reqd": 1
        },
        {
            "fieldname": "to_date",
            "label": __("Date de fin"),
            "fieldtype": "Date",
            "default": frappe.datetime.get_today(),  // Par défaut : aujourd'hui
            "reqd": 1
        },
        {
            "fieldname": "range",
            "label": __("Plage"),
            "fieldtype": "Select",
            "options": ["Mensuel", "Trimestriel", "Annuel"],
            "default": "Mensuel"
        },
        {
            "fieldname": "value",
            "label": __("Valeur"),
            "fieldtype": "Select",
            "options": ["Marge réelle", "Différence avec le théorique"],
            "default": "Marge réelle"
        }
    ]
};
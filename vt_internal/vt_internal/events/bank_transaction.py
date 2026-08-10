"""Événements du document Bank Transaction.

Convertis depuis les Server Scripts ERP (type « DocType Event »).
Source de vérité : ce fichier (versionné). Les records DB ont été supprimés.
"""

import frappe


def after_insert(doc, method=None):
    # --- depuis Server Script « Nouvelle transaction bancaire » (After Insert) ---
    # --- rapprochement automatique CB → Expense (Server Script) ---
    try:
        if doc.debit and doc.debit > 0:
            # Boucle sur les cartes bancaires de la société
            for cb in frappe.get_all(
                "Carte bancaire",
                filters={"company": doc.company},
                fields=["numero_de_la_carte", "employé"]
            ):
                # Si la carte correspond à la description
                if cb.employé and cb.numero_de_la_carte in doc.description:
                    # On rattache la transaction à l'employé
                    doc.party_type = "Employee"
                    doc.party = cb.employé

                    # Récupérer l'user_id de l'employé
                    user_id = frappe.db.get_value("Employee", cb.employé, "user_id")

                    # Chercher une dépense non rapprochée pour ce montant + cet employé
                    expense_name = frappe.db.get_value(
                        "Expense",
                        {
                            "grand_total": doc.debit,
                            "company": doc.company,
                            "employee": cb.employé,
                            "docstatus": 0,
                            "custom_bank_transaction": ("is", "not set"),
                        }
                    )

                    if expense_name:
                        # Mise à jour de la dépense existante
                        frappe.db.set_value("Expense", expense_name, {
                            "expense_date": doc.date,
                            "custom_bank_transaction": doc.name,
                            "custom_description_de_la_transaction": doc.description,
                            "custom_état": "Rapprochée et justifiée",
                        })
                    else:
                        type_de_note_de_frais = frappe.db.get_value(
                            "Bank Transaction Category",
                            doc.category,
                            "custom_type_de_note_de_frais"
                        ) or "Carburant"

                        # Création d'une nouvelle dépense
                        expense = frappe.get_doc({
                            "doctype": "Expense",
                            "expense_date": doc.date,
                            "custom_bank_transaction": doc.name,
                            "employee": cb.employé,
                            "custom_état": "À justifier",
                            "grand_total": doc.debit,
                            "company": doc.company,
                            "expense_details": [{
                                "expense_type": type_de_note_de_frais,
                                "amount": doc.debit
                            }],
                        })
                        expense.flags.ignore_permissions = True
                        expense.insert()

                    # Stop dès qu'on a traité la carte correspondante
                    break

    except Exception as e:
        frappe.log_error(
            message=f"Erreur lors du rapprochement CB → Expense pour la transaction {doc.name}: {frappe.get_traceback()}",
            title="Rapprochement CB automatique"
        )

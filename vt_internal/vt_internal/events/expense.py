"""Événements du document Expense.

Convertis depuis les Server Scripts ERP (type « DocType Event »).
Source de vérité : ce fichier (versionné). Les records DB ont été supprimés.
"""

import frappe


def validate(doc, method=None):
    # --- depuis Server Script « Date des dépense » (Before Save) ---
    if doc.custom_bank_transaction:
        doc.expense_date = frappe.db.get_value('Bank Transaction', doc.custom_bank_transaction, "date")
        doc.grand_total = frappe.db.get_value('Bank Transaction', doc.custom_bank_transaction, "debit")
        if not doc.receipt and not doc.custom_attestation_sur_lhonneur_de_note_de_frais:
            doc.custom_état = "À justifier"
        else:
            doc.custom_état = "Rapprochée et justifiée"
    else:
        if doc.receipt:
            doc.custom_état = "À rapprocher"
            corresponding_expense = frappe.db.get_value('Expense', {
                'custom_état': 'À justifier',
                'status': 'Draft',
                'employee': doc.employee,
                'grand_total': doc.grand_total,
            }, ['name', 'custom_bank_transaction'], as_dict=1)
            if corresponding_expense and corresponding_expense.custom_bank_transaction:
                doc.custom_bank_transaction = corresponding_expense.custom_bank_transaction
                doc.custom_état = "Rapprochée et justifiée"
                frappe.delete_doc("Expense", corresponding_expense.name)
                frappe.msgprint(
                    msg='Une transaction bancaire correspondante a été trouvé',
                    title='Succès',
                )
            else:
                frappe.msgprint(
                    msg='Aucune transaction bancaire ne correspond à votre dépense, cela peut prendre plusieurs heures',
                    title='En attente de la transaction',
                )
        else:
            doc.custom_état = "À justifier et à rapprocher"


def before_submit(doc, method=None):
    # --- depuis Server Script « Avant validation des dépenses » (Before Submit) ---
    # 1. On vérifie que la dépense est bien liée à une transaction bancaire
    if not doc.custom_bank_transaction:
        frappe.throw("Veuillez lier cette dépense avec la transaction bancaire correspondante avant de la valider")

    # On vérifie que la transaction bancaire n'est pas déjà rapprochée
    if frappe.db.get_value("Bank Transaction", doc.custom_bank_transaction, "status") == "Reconciled":
        frappe.throw("La transaction bancaire est déjà réconciliée")

    if not doc.cost_center:
        frappe.throw("Le centre de coût est obligatoire")

    if not doc.custom_attestation_sur_lhonneur_de_note_de_frais and not doc.receipt:
        frappe.throw("Il manque un justificatif ou une atestation sur l'honneur")

    if doc.net_amount == 0:
        frappe.throw("Le total net ne peut pas être de 0")


    employee = frappe.get_doc("Employee", doc.employee)
    validator_employee = frappe.get_doc("Employee", {
        "user_id": frappe.session.user
    })
    superiors = employee.get_ancestors()

    if superiors and validator_employee.name not in superiors:
        frappe.throw(f"Vous n'êtes pas approbateur. Liste des approbateurs: {', '.join(superiors)}")



def on_submit(doc, method=None):
    # --- depuis Server Script « Après validation des dépenses » (After Submit) ---
    # 1. On enlève la personne assignée
    #todo = frappe.db.get_value("ToDo", {"reference_type": doc.doctype, "reference_name": doc.name})
    #if todo:
    #    frappe.delete_doc("ToDo", todo)

    # 2. On crée une note de frais
    ec = frappe.call("hrms.hr.doctype.expense.expense.make_expense_claim", source_name=doc.name)
    ec.posting_date = doc.expense_date
    ec.set_payable_account()
    ec.expense_approver = doc.custom_approbateur
    ec.is_paid = 1
    ec.mode_of_payment = "Carte de crédit"
    ec.approval_status = "Approved"
    ec.exchange_rate = 1
    for row in ec.expenses:
        row.sanctioned_amount = row.amount
    ec.insert()
    ec.submit()


    # 3. On rapproche cette note de frais avec la transaction bancaire
    bt = frappe.get_doc("Bank Transaction", doc.custom_bank_transaction)
    bt.append(
    	"payment_entries",
    	{
    		"payment_document": ec.doctype,
    		"payment_entry": ec.name,
    		"allocated_amount": ec.total_claimed_amount,
    		"party": ec.employee,
    		"date": doc.expense_date,
    	},
    )
    bt.save()

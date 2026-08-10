"""Tâche planifiée « Dépense mail hebdomadaire » (fréquence : Weekly).

Convertie depuis le Server Script ERP (type « Scheduler Event »).
Câblage de la fréquence dans hooks.py (scheduler_events).
Source de vérité : ce fichier (versionné). Le record DB a été supprimé.
"""

import frappe


def weekly_expense_reminder():

    for employee in frappe.db.get_all("Employee", fields=["name", "user_id"]):
        expenses_html = []
        all_expenses = frappe.db.get_all('Expense',
            fields=['grand_total', 'custom_état', 'employee', 'project', 'expense_date', "name", "custom_description_de_la_transaction"],
            filters={
                "employee": employee.name,
                'custom_état': "À justifier",
                "docstatus": 0
            },
        )
        for i in range(len(all_expenses)):
            e = all_expenses[i]
            bg_color = i % 2 == 0 and "white" or "#f9f9f9"

            age = frappe.utils.date_diff(frappe.utils.now(), e.expense_date)
            age_color = age < 7 and "green" or age < 15 and "orange" or "red"
            age_html = f"<b style='color: {age_color}'>({age} jours)</b>"

            expenses_html.append(f"""
            <tr style="background-color: {bg_color};">
                <td style="border: 1px solid #ddd; padding: 8px;"><a href="{frappe.utils.get_url_to_form('Expense', e.name)}">{e.custom_description_de_la_transaction}</a></td>
                <td style="border: 1px solid #ddd; padding: 8px;">{e.grand_total} €</td>
                <td style="border: 1px solid #ddd; padding: 8px;">{age_html}</td>
            </tr>
            """)
        EMAIL_SUBJECT = f"{len(all_expenses)} dépense(s) en attente de justification"
        EMAIL_BODY = f"""
        <table style="width: 100%; border-collapse: collapse; font-family: Arial, sans-serif;">
                <thead>
                    <tr style="background-color: #f4f4f4;">
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Dépense</th>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Montant</th>
                        <th style="border: 1px solid #ddd; padding: 8px; text-align: left;">Délai</th>
                    </tr>
                </thead>
                <tbody>
                    {" ".join(expenses_html)}
                </tbody>
            </table>

        """
        if len(all_expenses) > 0:
            frappe.sendmail(
                recipients=[employee.user_id],
                subject=EMAIL_SUBJECT,
                message=EMAIL_BODY,
            )

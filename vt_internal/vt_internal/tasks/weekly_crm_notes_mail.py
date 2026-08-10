"""Tâche planifiée « Notes CRM Mail » (fréquence : Weekly).

Convertie depuis le Server Script ERP (type « Scheduler Event »).
Câblage de la fréquence dans hooks.py (scheduler_events).
Source de vérité : ce fichier (versionné). Le record DB a été supprimé.
"""

import frappe


def weekly_crm_notes_mail():
    # début et fin de la semaine (lundi → aujourd’hui)
    today = frappe.utils.getdate(frappe.utils.nowdate())
    start_of_week = frappe.utils.add_days(today, - today.weekday())
    end_of_week = today

    # toutes les CRM Note (table enfant "notes" de Customer) créées cette semaine
    notes = frappe.db.get_all(
        "CRM Note",
        fields=["name", "note", "added_on", "parent", "owner"],
        filters=[
            ["added_on", ">=", start_of_week],
            ["added_on", "<=", end_of_week],
            ["parenttype", "=", "Customer"]
        ],
        order_by="parent, added_on",
    )

    if notes:
        # regrouper par société (depuis le champ custom_company du Customer) puis par client
        grouped = {}
        for n in notes:
            cli = n.parent or "— Client non renseigné —"
            # récupérer la société via custom_company
            comp = frappe.db.get_value("Customer", cli, "custom_company") or "Aucune société"
            grouped.setdefault(comp, {}).setdefault(cli, []).append(n)

        # construire le HTML de l'email
        html = []
        html.append("""
        <thead>
          <tr style=\"background-color:#f4f4f4;\">
            <th style=\"border:1px solid #ddd;padding:8px;\">Société</th>
            <th style=\"border:1px solid #ddd;padding:8px;\">Client</th>
            <th style=\"border:1px solid #ddd;padding:8px;\">Note</th>
            <th style=\"border:1px solid #ddd;padding:8px;\">Ajoutée le</th>
            <th style=\"border:1px solid #ddd;padding:8px;\">Ajouté par</th>
          </tr>
        </thead>
        <tbody>
        """)

        toggle = False
        for comp, clients in grouped.items():
            for cli, cl_notes in clients.items():
                # générer le lien vers le client
                client_link = frappe.utils.get_url_to_form("Customer", cli)
                for note in cl_notes:
                    bg = "#ffffff" if toggle else "#f9f9f9"
                    toggle = not toggle
                    date_fr = frappe.utils.format_date(note.added_on, "dd/mm/yyyy")
                    html.append(f"""
                    <tr style=\"background-color:{bg};\">
                      <td style=\"border:1px solid #ddd;padding:8px;\">{comp}</td>
                      <td style=\"border:1px solid #ddd;padding:8px;\">
                        <a href=\"{client_link}\">{cli}</a>
                      </td>
                      <td style=\"border:1px solid #ddd;padding:8px;\">{note.note or note.name}</td>
                      <td style=\"border:1px solid #ddd;padding:8px;\">{date_fr}</td>
                      <td style=\"border:1px solid #ddd;padding:8px;\">{note.owner}</td>
                    </tr>
                    """)

        html.append("</tbody>")

                # préparer la liste des destinataires : tous les employés actifs via user_id
        employees = frappe.get_all(
            "Employee",
            fields=["user_id"]
        )
        recipients = [e.user_id for e in employees if e.user_id]

        # corps du mail
        message = f"""
        <div style=\"font-family:Arial,sans-serif;\">
          <p>Bonjour,</p>
          <p>Voici les <b>{len(notes)}</b> CRM Note(s) créées cette semaine
          ({frappe.utils.formatdate(start_of_week, 'dd/MM/yyyy')} – {frappe.utils.formatdate(end_of_week, 'dd/MM/yyyy')}):</p>
          <table style=\"width:100%;border-collapse:collapse;\">
            {''.join(html)}
          </table>
          <p>L'équipe commerciale</p>
        </div>
        """
        frappe.sendmail(
            recipients=recipients,
            subject=f"{len(notes)} Note(s) CRM cette semaine",
            message=message
        )

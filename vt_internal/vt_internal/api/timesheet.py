"""Endpoints feuilles de temps / fiches de travail.

Convertis depuis les Server Scripts ERP (type « API »).
URLs courtes historiques préservées via override_whitelisted_methods (hooks.py).
Source de vérité : ces fichiers (versionnés). Les records DB ont été supprimés.
"""

import frappe

@frappe.whitelist()
def ft_timer_html():
    # Converti depuis le Server Script API « Fiche » (/api/method/ft_timer_html).
    ft_id = frappe.form_dict.get("ft")
    ft = frappe.get_doc("Fiche de travail", ft_id)

    tss = frappe.db.sql("""
        SELECT ts.employee AS employee, SUM(tsd.hours) AS hours
        FROM `tabTimesheet` ts
        INNER JOIN `tabTimesheet Detail` tsd ON tsd.parent = ts.name
        WHERE ts.docstatus != 2
          AND tsd.custom_fiche_de_travail = %s
        GROUP BY ts.employee
    """, (ft_id,), as_dict=True)

    total_hours = sum([t.hours for t in tss])
    hours_per_person = []
    for t in tss:
        url = frappe.utils.get_url('/app/timesheet/' + f"?employee={t.employee.replace(' ', '%20')}&custom_fiche_de_travail={ft_id}")
        print(url)
        hours_per_person.append(f"""<tr class="table-light">
    	            <td><a href={url}>{t.employee}</a></td>
    	            <td>{t["hours"]}</td>
    	        </tr>""")

    html = ""
    if len(tss) > 0:
        html = f"""
        <h6>Récapitulatif d'activité</h6>
        <small class="text-primary">Nombre total d'heures : {total_hours}</small>
        <table class="table">
            <thead>
                <tr class="table-primary">
                  <th scope="col">Employé</th>
                  <th scope="col">Heures</th>
                </tr>
            </thead>
            <tbody>{" ".join(hours_per_person)}</tbody>
        </table>

        """
    frappe.response['message'] = {}
    frappe.response['message']["html"] = html


@frappe.whitelist()
def timesheet_html_block():
    # Converti depuis le Server Script API « timesheet_html_block » (/api/method/timesheet_html_block).
    employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
    today_timesheet_exists = frappe.db.exists("Timesheet", {
        "employee": employee,
        "start_date": frappe.utils.today(),
        "docstatus": 0
    })

    frappe.response['message'] = {}

    if not today_timesheet_exists:
        frappe.response['message']["current_task"] = "Day not started"

    else:
        today_timesheet = frappe.get_doc("Timesheet", {
            "employee": employee,
            "start_date": frappe.utils.today(),
            "docstatus": 0
        })
        frappe.response['message']["from_time"] = today_timesheet.time_logs[0].from_time
        frappe.response['message']["timesheet"] = today_timesheet.name
        if today_timesheet.custom_day_finished:
            frappe.response['message']["current_task"] = "Day finished"
        else:
            last_time_log = today_timesheet.time_logs[-1]
            frappe.response['message']["current_task"] = last_time_log.activity_type
            frappe.response['message']["fiche_de_travail"] = last_time_log.custom_fiche_de_travail
            if last_time_log.to_time is not None:
                frappe.response['message']["current_task"] = "Pause"


@frappe.whitelist()
def timesheet_post_api():
    # Converti depuis le Server Script API « timesheet_post_api » (/api/method/timesheet_post_api).
    action = frappe.form_dict.get("action")
    user = frappe.session.user
    employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
    company = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "company")
    activity_type = frappe.form_dict.get("activity_type") or 'Atelier'
    sav = frappe.form_dict.get("sav") or 0

    # Obtenir l'heure actuelle
    current_time = frappe.utils.now_datetime()

    # Calculer la différence des minutes avec la quinzaine la plus proche
    minutes = (current_time.minute // 15) * 15
    if current_time.minute % 15 >= 8:
        minutes = minutes + 15

    # Arrondir à la quinzaine la plus proche
    rounded_time = current_time.replace(minute=0, second=0, microsecond=0)
    rounded_time = frappe.utils.add_to_date(rounded_time, minutes=minutes)

    today_timesheet_exists = frappe.db.exists("Timesheet", {
        "employee": employee,
        "start_date": frappe.utils.today(),
        "docstatus": 0
    })
    if today_timesheet_exists:
        doc = frappe.get_doc("Timesheet", {
            "employee": employee,
            "start_date": frappe.utils.today(),
            "docstatus": 0
        })
    else:
        doc = frappe.get_doc({
            "doctype": "Timesheet",
            'company': company,
            "employee": employee,
            "title": employee,
            "time_logs": [{
                "activity_type": activity_type,
                "from_time": rounded_time
            }]
        })
        doc.insert()

    duration = None
    if doc.time_logs[-1] and doc.time_logs[-1].to_time is None:
        duration = frappe.utils.time_diff_in_hours(rounded_time, doc.time_logs[-1].from_time)
    else:
        print("Aucune tâche commencé")

    ONE_MINUTE = 1/60
    print(frappe.form_dict)

    if action == "duplicate":
        new_employee = frappe.form_dict.get("new_employee")
        new_timesheet = frappe.copy_doc(doc)
        new_timesheet.employee = new_employee
        new_timesheet.title = new_employee + " dupliqué" 
        new_timesheet.note = (new_timesheet.note or "") + (frappe.form_dict.get("comment") or "") + "\n"
        new_timesheet.save()

    if action == "start_break":
        if duration is not None:
            if rounded_time == doc.time_logs[-1].from_time:
                if len(doc.time_logs) != 1:
                    doc.time_logs.pop()
            else:
                doc.time_logs[-1].to_time = rounded_time
                doc.time_logs[-1].hours = duration
            doc.save()

    if action == "add_comment":
        doc.note = (doc.note or "") + (frappe.form_dict.get("comment") or "") + "\n"
        doc.save()

    if action == "start_construction":
        fiche_de_travail = frappe.form_dict.get("fiche_de_travail")
        atelier = frappe.form_dict.get("atelier")
        if duration is not None:
            if duration < ONE_MINUTE:
                doc.time_logs.pop()
            else:
                doc.time_logs[-1].to_time = rounded_time
                doc.time_logs[-1].hours = duration
        if fiche_de_travail:
            doc.append('time_logs', {
                "activity_type": activity_type,
                "custom_fiche_de_travail": fiche_de_travail,
                "project": frappe.db.get_value("Fiche de travail", fiche_de_travail, "projet"),
                "from_time": rounded_time,
                "custom_sav": sav,
            })
        else:
            doc.append('time_logs', {
                "activity_type": activity_type,
                "from_time": rounded_time,
                "custom_sav": sav,
            })
        doc.save()

    if action == "stop_day":

        if duration is not None:
            if duration < ONE_MINUTE:
                doc.time_logs.pop()
            else:
                doc.time_logs[-1].to_time = rounded_time
                doc.time_logs[-1].hours = duration
        doc.custom_day_finished=True

        doc.save()


@frappe.whitelist()
def update_fiche_de_travail_status():
    # Converti depuis le Server Script API « update_fiche_de_travail_status » (/api/method/update_fiche_de_travail_status).
    doc_name = frappe.form_dict.doc_name
    doc = frappe.get_doc("Fiche de travail", doc_name)
    statuses = [item.status for item in doc.items]
    if "⚫️" in statuses:
        avancement = "⚫️"
    if "🔴" in statuses:
        avancement = "🔴"
    elif "🟠" in statuses:
        avancement = "🟠"
    elif "🟢" in statuses:
        avancement = "🟢"
    else: avancement = ""
    frappe.db.set_value("Fiche de travail", doc.name, "avancement", avancement)
    print(frappe.db.get_value("Fiche de travail", doc.name, "avancement"))

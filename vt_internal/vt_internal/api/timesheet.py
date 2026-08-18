"""Endpoints feuilles de temps / fiches de travail.

Convertis depuis les Server Scripts ERP (type « API »).
URLs courtes historiques préservées via override_whitelisted_methods (hooks.py).
Source de vérité : ces fichiers (versionnés). Les records DB ont été supprimés.
"""

import frappe

from vt_internal.vt_internal.constants import (
    ACTIVITY_ATELIER,
    ACTIVITY_VISITE,
    AVANCEMENT_MARKERS,
    TASK_DAY_FINISHED,
    TASK_DAY_NOT_STARTED,
    TASK_PAUSE,
)
from vt_internal.vt_internal.utils.time_utils import round_to_quarter

ONE_MINUTE = 1 / 60


# ---------------------------------------------------------------------------
# Récap heures par fiche (bloc HTML injecté dans la Fiche de travail)
# ---------------------------------------------------------------------------
@frappe.whitelist()
def ft_timer_html():
    # Converti depuis le Server Script API « Fiche » (/api/method/ft_timer_html).
    ft_id = frappe.form_dict.get("ft")

    rows = frappe.db.sql(
        """
        SELECT ts.employee AS employee, SUM(tsd.hours) AS hours
        FROM `tabTimesheet` ts
        INNER JOIN `tabTimesheet Detail` tsd ON tsd.parent = ts.name
        WHERE ts.docstatus != 2
          AND tsd.custom_fiche_de_travail = %s
        GROUP BY ts.employee
        """,
        (ft_id,),
        as_dict=True,
    )

    html = ""
    if rows:
        total_hours = sum(r.hours for r in rows)
        html = frappe.render_template(
            "vt_internal/templates/includes/ft_timer.html",
            {"rows": rows, "total_hours": total_hours, "ft_id": ft_id},
        )

    frappe.response["message"] = {"html": html}


# ---------------------------------------------------------------------------
# État de pointage du jour + actions autorisées
# ---------------------------------------------------------------------------
def _allowed_actions(task):
    """Décrit les boutons de pointage à afficher, selon l'état courant.

    Logique métier centralisée ici (le front se contente de rendre la liste).
    Chaque action : {action, activity_type?, label, toast, primary}.
    """
    actions = []

    if task not in (ACTIVITY_ATELIER, TASK_DAY_FINISHED):
        actions.append({
            "action": "start_construction", "activity_type": ACTIVITY_ATELIER,
            "label": "Démarrer l'atelier",
            "icon": "hammer",
            "toast": "Atelier commencé",
        })
    if task not in (ACTIVITY_VISITE, TASK_DAY_FINISHED):
        actions.append({
            "action": "start_construction", "activity_type": ACTIVITY_VISITE,
            "label": "Commencer une visite technique",
            "icon": "map-pin",
            "toast": "Visite technique commencée",
        })
    if task not in (TASK_PAUSE, TASK_DAY_FINISHED, TASK_DAY_NOT_STARTED):
        actions.append({
            "action": "start_break",
            "label": "Faire une pause",
            "icon": "coffee",
            "toast": "Pause commencée",
        })
    if task not in (TASK_DAY_NOT_STARTED, TASK_DAY_FINISHED):
        actions.append({
            "action": "stop_day",
            "label": "Terminer la journée",
            "icon": "circle-stop",
            "toast": "Journée terminée",
            "confirm": "Terminer la journée ?",
        })

    # Bouton principal contextuel : la pause en cours de journée, sinon le
    # premier démarrage (journée non commencée).
    primary = next((a for a in actions if a["action"] == "start_break"), None)
    if not primary and task == TASK_DAY_NOT_STARTED:
        primary = actions[0] if actions else None
    if primary:
        primary["primary"] = True

    return actions


@frappe.whitelist()
def timesheet_state():
    """État de pointage du jour de l'employé courant + actions autorisées."""
    employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")

    state = {
        "employee": employee,
        "employee_name": frappe.db.get_value("Employee", employee, "employee_name") if employee else None,
        "timesheet": None,
        "current_task": TASK_DAY_NOT_STARTED,
        "from_time": None,        # début de journée (1er log)
        "task_from_time": None,   # début de la tâche courante (dernier log ouvert)
        "fiche_de_travail": None,       # nom (id) de la fiche pointée
        "fiche_reference": None,        # référence pièce de la fiche pointée (affichage)
        "total_hours": 0,               # total pointé aujourd'hui (heures)
    }

    ts_name = frappe.db.exists("Timesheet", {
        "employee": employee, "start_date": frappe.utils.today(), "docstatus": 0,
    })
    if ts_name:
        doc = frappe.get_doc("Timesheet", ts_name)
        state["timesheet"] = doc.name
        state["total_hours"] = doc.total_hours or 0
        state["from_time"] = doc.time_logs[0].from_time if doc.time_logs else None
        if doc.custom_day_finished:
            state["current_task"] = TASK_DAY_FINISHED
        else:
            last = doc.time_logs[-1]
            state["fiche_de_travail"] = last.custom_fiche_de_travail
            if last.custom_fiche_de_travail:
                state["fiche_reference"] = frappe.db.get_value(
                    "Fiche de travail", last.custom_fiche_de_travail, "référence_pièce"
                )
            if last.to_time is not None:
                state["current_task"] = TASK_PAUSE
            else:
                state["current_task"] = last.activity_type
                state["task_from_time"] = last.from_time

    state["today_events"] = _today_events(employee) if employee else []
    state["actions"] = _allowed_actions(state["current_task"])
    return state


def _today_events(employee):
    """Événements planifiés aujourd'hui pour l'employé (table Event).

    Un Event porte `custom_employé` (nom Employee) et `starts_on`. Selon les
    liens présents, on qualifie l'événement :
      - `fiche`  : lié à une fiche de travail (custom_fiche_de_travail) ;
      - `visite` : lié à une visite technique (custom_visite_technique) ;
      - `event`  : autre événement (agenda simple).
    """
    rows = frappe.db.sql(
        """
        SELECT
            e.name AS event,
            e.subject AS subject,
            e.starts_on AS starts_on,
            e.custom_fiche_de_travail AS fiche,
            e.custom_visite_technique AS visite,
            e.project AS project,
            ft.`référence_pièce` AS fiche_reference,
            ft.status AS fiche_status,
            ft.address AS fiche_address,
            vt.address AS visite_address
        FROM `tabEvent` e
        LEFT JOIN `tabFiche de travail` ft ON ft.name = e.custom_fiche_de_travail
        LEFT JOIN `tabVisite Technique` vt ON vt.name = e.custom_visite_technique
        WHERE e.custom_employé = %s
          AND DATE(e.starts_on) = %s
        ORDER BY e.starts_on
        """,
        (employee, frappe.utils.today()),
        as_dict=True,
    )
    for r in rows:
        r["kind"] = "fiche" if r.fiche else ("visite" if r.visite else "event")
        r["maps"] = _address_query(r.fiche_address if r.fiche else r.visite_address)
    return rows


def _address_query(address_name):
    """Adresse formatée (pour une recherche Google Maps) depuis un lien Address."""
    if not address_name:
        return None
    a = frappe.db.get_value(
        "Address", address_name,
        ["address_line1", "address_line2", "city", "pincode"],
        as_dict=True,
    )
    if not a:
        return None
    parts = [a.address_line1, a.address_line2, a.city, a.pincode]
    return ", ".join(p for p in parts if p) or None


@frappe.whitelist()
def timesheet_html_block():
    """Alias rétro-compatible : même charge utile que timesheet_state (superset).

    Conservé pour les anciens appels front (`method: "timesheet_html_block"`).
    """
    return timesheet_state()


# ---------------------------------------------------------------------------
# Actions de pointage (POST)
# ---------------------------------------------------------------------------
def _close_last_log(doc, rounded_time, duration, drop_if_shorter_than=ONE_MINUTE):
    """Ferme le dernier log ouvert : pose to_time/hours, ou le supprime si trop court.

    Le log trop court est toujours supprimé (y compris le log-graine d'une feuille
    fraîche) : les appelants (`start_construction`, `stop_day`) ne comptent jamais
    sur sa présence. Ne pas ajouter de garde `len != 1` ici — sinon une première
    action laisse une ligne parasite à 0h. La protection « ne pas vider une feuille
    manuelle » est propre à `start_break`, qui gère son propre cas.
    """
    if duration is None:
        return
    if duration < drop_if_shorter_than:
        doc.time_logs.pop()
    else:
        doc.time_logs[-1].to_time = rounded_time
        doc.time_logs[-1].hours = duration


def _act_start_construction(doc, rounded_time, duration):
    fiche_de_travail = frappe.form_dict.get("fiche_de_travail")
    project = frappe.form_dict.get("project")
    activity_type = frappe.form_dict.get("activity_type") or ACTIVITY_ATELIER
    sav = frappe.form_dict.get("sav") or 0

    _close_last_log(doc, rounded_time, duration)

    log = {"activity_type": activity_type, "from_time": rounded_time, "custom_sav": sav}
    if fiche_de_travail:
        log["custom_fiche_de_travail"] = fiche_de_travail
        log["project"] = frappe.db.get_value("Fiche de travail", fiche_de_travail, "projet")
    elif project:
        # Pointage rattaché à un projet sans fiche (ex : visite technique).
        log["project"] = project
    doc.append("time_logs", log)
    doc.save()


def _act_start_break(doc, rounded_time, duration):
    # Une pause = on ferme simplement le log courant (pas de nouveau log).
    if duration is None:
        return
    if rounded_time == doc.time_logs[-1].from_time:
        if len(doc.time_logs) != 1:
            doc.time_logs.pop()
    else:
        doc.time_logs[-1].to_time = rounded_time
        doc.time_logs[-1].hours = duration
    doc.save()


def _act_stop_day(doc, rounded_time, duration):
    _close_last_log(doc, rounded_time, duration)
    doc.custom_day_finished = True
    doc.save()


def _act_duplicate(doc, rounded_time, duration):
    new_employee = frappe.form_dict.get("new_employee")
    new_timesheet = frappe.copy_doc(doc)
    new_timesheet.employee = new_employee
    new_timesheet.title = f"{new_employee} dupliqué"
    new_timesheet.note = (new_timesheet.note or "") + (frappe.form_dict.get("comment") or "") + "\n"
    new_timesheet.save()


def _act_add_comment(doc, rounded_time, duration):
    doc.note = (doc.note or "") + (frappe.form_dict.get("comment") or "") + "\n"
    doc.save()


_ACTIONS = {
    "start_construction": _act_start_construction,
    "start_break": _act_start_break,
    "stop_day": _act_stop_day,
    "duplicate": _act_duplicate,
    "add_comment": _act_add_comment,
}


@frappe.whitelist()
def timesheet_post_api():
    # Converti depuis le Server Script API « timesheet_post_api ».
    action = frappe.form_dict.get("action")
    handler = _ACTIONS.get(action)
    if not handler:
        frappe.throw(f"Action de pointage inconnue : {action}")

    employee = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name")
    company = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "company")
    activity_type = frappe.form_dict.get("activity_type") or ACTIVITY_ATELIER

    rounded_time = round_to_quarter(frappe.utils.now_datetime())

    ts_name = frappe.db.exists("Timesheet", {
        "employee": employee, "start_date": frappe.utils.today(), "docstatus": 0,
    })
    if ts_name:
        doc = frappe.get_doc("Timesheet", ts_name)
    else:
        doc = frappe.get_doc({
            "doctype": "Timesheet",
            "company": company,
            "employee": employee,
            "title": employee,
            "time_logs": [{"activity_type": activity_type, "from_time": rounded_time}],
        })
        doc.insert()

    # Durée du dernier log ouvert (None si aucun log ouvert).
    duration = None
    last = doc.time_logs[-1] if doc.time_logs else None
    if last and last.to_time is None:
        duration = frappe.utils.time_diff_in_hours(rounded_time, last.from_time)

    handler(doc, rounded_time, duration)


@frappe.whitelist()
def update_fiche_de_travail_status():
    # Converti depuis le Server Script API « update_fiche_de_travail_status ».
    doc = frappe.get_doc("Fiche de travail", frappe.form_dict.doc_name)
    statuses = [item.status for item in doc.items]

    # Priorité décroissante : premier marqueur présent l'emporte.
    avancement = next((m for m in AVANCEMENT_MARKERS if m in statuses), "")
    frappe.db.set_value("Fiche de travail", doc.name, "avancement", avancement)

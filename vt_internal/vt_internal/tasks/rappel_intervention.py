"""Tâches planifiées « Rappel J-1 » (fréquence : cron, tous les soirs à 18h).

Chaque soir, parcourt les Event du lendemain rattachés à une Fiche de travail
(pose) ou une Visite Technique. Envoi uniquement si
`custom_envoyer_sms_client = 1` (cochée par défaut pour toute société ;
décocher l'Event pour ne pas envoyer) :
  - SMS si un numéro mobile client est renseigné ;
  - sinon e-mail HTML si une adresse est renseignée.
Les numéros fixes commençant par 04 (AllMySMS les refuse, HTTP 400) sont
traités comme s'il n'y avait pas de téléphone.

Un SMS / e-mail est émis par Event (pas de regroupement par fiche/VT),
afin de respecter le flag et le créneau (matin / après-midi) de chaque RDV.

Créneau : heure de `starts_on` — matin si hour < 13, sinon après-midi.
Les Event « journée entière » (all_day) sont traités comme créneau matin
(8h–12h30) : convention locale faute d'horaire précis.

Pose : texte sans téléphone technicien.
VT : phrase « vous pouvez le joindre au … » si un téléphone est trouvé
(employé de l'Event → Employee.cell_number, sinon User, sinon Contact).
Sinon la phrase est omise.

Câblage de la fréquence dans hooks.py (scheduler_events > cron « 0 18 * * * »).
Source de vérité : ce fichier (versionné).
"""

from __future__ import annotations

import frappe
from frappe.core.doctype.sms_settings.sms_settings import send_sms
from frappe.utils import add_days, formatdate, get_datetime, today

from vt_internal.vt_internal.utils.event_employees import (
    EVENT_EMPLOYEE_FIELD,
    LEGACY_EMPLOYEE_FIELD,
    employee_ids_from_rows,
)
from vt_internal.vt_internal.utils.phone import is_french_landline

def default_envoyer_sms_for_company(company: str | None) -> int:
    """1 pour toute société : le SMS part, on décoche l'Event pour ne pas envoyer.

    `company` est conservé pour les appelants ; la règle ne dépend plus de la société.
    """
    return 1


def rappel_chantier():
    """Rappel pour les chantiers (événements liés à une Fiche de travail)."""
    _envoyer_rappels(
        link_field="custom_fiche_de_travail",
        doctype="Fiche de travail",
        email_field="contact_email",
        kind="pose",
        titre_email="Rappel de votre intervention",
        objet_email="Rappel : intervention prévue demain",
        corps_email=(
            "Pour rappel, notre équipe interviendra <b>{date}</b>, {horaire}, "
            "dans le cadre de votre chantier.<br/><br/>"
            "Nous vous remercions de veiller à ce que l'accès au site soit possible à cet horaire."
        ),
    )


def rappel_visite_technique():
    """Rappel pour les visites techniques (événements liés à une Visite Technique)."""
    _envoyer_rappels(
        link_field="custom_visite_technique",
        doctype="Visite Technique",
        email_field="email",
        kind="vt",
        titre_email="Rappel de votre visite technique",
        objet_email="Rappel : visite technique prévue demain",
        corps_email=(
            "Pour rappel, notre technicien réalisera la visite technique "
            "<b>{date}</b>, {horaire}.<br/><br/>"
            "Nous vous remercions de veiller à être disponible à cet horaire."
        ),
    )


def build_sms_message(
    *,
    kind: str,
    societe: str,
    date_lettres: str,
    is_morning: bool,
    telephone_tech: str | None = None,
) -> str:
    """Construit le texte SMS (pose ou VT, matin ou après-midi).

    Utilisable en dry-run / console sans envoi réel.
    """
    creneau = "entre 8h et 12h30" if is_morning else "entre 13h et 17h"

    if kind == "pose":
        return (
            f"Bonjour, la {societe} vous rappelle son intervention demain, "
            f"le {date_lettres} {creneau} dans le cadre de votre chantier."
        )

    # VT
    base = (
        f"Bonjour, la {societe} vous rappelle l'intervention de notre technicien demain "
        f"le {date_lettres} {creneau} dans le cadre de la visite technique de votre chantier."
    )
    if telephone_tech:
        return f"{base} En cas de besoin, vous pouvez le joindre au {telephone_tech}."
    return base


def preview_sms_for_event(event_name: str) -> dict | None:
    """Aperçu du SMS pour un Event (sans envoi). Retourne un dict ou None."""
    event = frappe.get_doc("Event", event_name)
    if event.custom_fiche_de_travail:
        kind, link_field, doctype, email_field = (
            "pose",
            "custom_fiche_de_travail",
            "Fiche de travail",
            "contact_email",
        )
        ref = event.custom_fiche_de_travail
    elif event.custom_visite_technique:
        kind, link_field, doctype, email_field = (
            "vt",
            "custom_visite_technique",
            "Visite Technique",
            "email",
        )
        ref = event.custom_visite_technique
    else:
        return None

    demain = add_days(today(), 1)
    date_lettres = formatdate(demain, "EEEE d MMMM yyyy")
    ctx = _context_for_event(event, link_field, doctype, email_field, ref, date_lettres)
    if not ctx:
        return None
    msg = build_sms_message(
        kind=kind,
        societe=ctx["societe"],
        date_lettres=date_lettres,
        is_morning=ctx["is_morning"],
        telephone_tech=ctx.get("telephone_tech"),
    )
    return {
        "event": event_name,
        "kind": kind,
        "ref": ref,
        "envoyer_sms": int(event.custom_envoyer_sms_client or 0),
        "phone": ctx.get("phone"),
        "email": ctx.get("email"),
        "sms_possible": ctx.get("sms_possible"),
        "societe": ctx["societe"],
        "is_morning": ctx["is_morning"],
        "message": msg,
    }


def dry_run_rappels(output_path: str = "/tmp/sms-preview.txt") -> str:
    """Parcourt les Event du lendemain éligibles et écrit les SMS prévus (sans envoi)."""
    demain = add_days(today(), 1)
    date_lettres = formatdate(demain, "EEEE d MMMM yyyy")
    lines = [
        "# Aperçu SMS rappel J-1 (dry-run, aucun envoi)",
        f"# Date cible (lendemain) : {date_lettres}",
        f"# Généré le : {frappe.utils.now_datetime()}",
        "",
    ]

    for kind, link_field, doctype, email_field in (
        ("pose", "custom_fiche_de_travail", "Fiche de travail", "contact_email"),
        ("vt", "custom_visite_technique", "Visite Technique", "email"),
    ):
        events = frappe.get_all(
            "Event",
            filters={
                link_field: ["is", "set"],
                "starts_on": ["between", [f"{demain} 00:00:00", f"{demain} 23:59:59"]],
                "status": ["!=", "Cancelled"],
            },
            fields=_event_fields(link_field),
            order_by="starts_on",
        )
        lines.append(f"## {kind.upper()} ({len(events)} event(s) demain)")
        for e in events:
            flag = int(e.custom_envoyer_sms_client or 0)
            ref = e[link_field]
            ctx = _context_for_event(e, link_field, doctype, email_field, ref, date_lettres)
            if not ctx:
                lines.append(f"- {e.name} → skip (pas de mobile/email client)")
                continue
            msg = build_sms_message(
                kind=kind,
                societe=ctx["societe"],
                date_lettres=date_lettres,
                is_morning=ctx["is_morning"],
                telephone_tech=ctx.get("telephone_tech"),
            )
            status = "ENVOI" if flag else "SKIP (case décochée)"
            if ctx.get("sms_possible"):
                canal = f"SMS→{ctx['phone']}"
            else:
                canal = f"EMAIL→{ctx.get('email')}"
            lines.append(f"- {e.name} [{status}] {canal} societe={ctx['societe']}")
            lines.append(f"  {msg}")
        lines.append("")

    lines.extend(
        [
            "## Exemples de templates (fictifs)",
            build_sms_message(
                kind="pose",
                societe="Miroiterie Avignonnaise",
                date_lettres=date_lettres,
                is_morning=True,
            ),
            build_sms_message(
                kind="pose",
                societe="Vitrerie Stéphanoise",
                date_lettres=date_lettres,
                is_morning=False,
            ),
            build_sms_message(
                kind="vt",
                societe="VT Riviera",
                date_lettres=date_lettres,
                is_morning=True,
                telephone_tech="06 12 34 56 78",
            ),
            build_sms_message(
                kind="vt",
                societe="Vitrerie Stéphanoise",
                date_lettres=date_lettres,
                is_morning=False,
                telephone_tech=None,
            ),
            "",
        ]
    )

    text = "\n".join(lines)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(text)
    return output_path


def _event_fields(link_field):
    return [
        "name",
        link_field,
        "starts_on",
        "all_day",
        "custom_company",
        LEGACY_EMPLOYEE_FIELD,
        "custom_envoyer_sms_client",
    ]


def _envoyer_rappels(link_field, doctype, email_field, kind, titre_email, objet_email, corps_email):
    demain = add_days(today(), 1)
    date_lettres = formatdate(demain, "EEEE d MMMM yyyy")

    events = frappe.get_all(
        "Event",
        filters={
            link_field: ["is", "set"],
            "starts_on": ["between", [f"{demain} 00:00:00", f"{demain} 23:59:59"]],
            "custom_envoyer_sms_client": 1,
            "status": ["!=", "Cancelled"],
        },
        fields=_event_fields(link_field),
    )

    if not events:
        return

    for e in events:
        ref_name = e[link_field]
        ctx = _context_for_event(e, link_field, doctype, email_field, ref_name, date_lettres)
        if not ctx:
            continue

        horaire_lib = "entre 8h et 12h30" if ctx["is_morning"] else "entre 13h et 17h"
        phone, email = ctx.get("phone"), ctx.get("email")
        societe = ctx["societe"]
        sms_possible = ctx.get("sms_possible")

        try:
            if sms_possible:
                msg = build_sms_message(
                    kind=kind,
                    societe=societe,
                    date_lettres=date_lettres,
                    is_morning=ctx["is_morning"],
                    telephone_tech=ctx.get("telephone_tech"),
                )
                send_sms(receiver_list=[phone], msg=msg)
                canal = f"SMS de rappel envoyé au {phone}"
            else:
                corps_html = _corps_email(
                    cost_center=ctx.get("cost_center"),
                    societe=societe,
                    titre=titre_email,
                    corps=corps_email.format(date=f"le {date_lettres}", horaire=horaire_lib),
                )
                frappe.sendmail(
                    recipients=[email],
                    subject=objet_email,
                    message=corps_html,
                    reference_doctype=doctype,
                    reference_name=ref_name,
                )
                canal = f"E-mail de rappel envoyé à {email}"
        except Exception as exc:
            destinataire = phone if sms_possible else email
            frappe.log_error(
                f"Échec de l'envoi du rappel pour Event {e.name} / {doctype} {ref_name} "
                f"({destinataire}) : {exc}",
                "Rappel intervention J-1",
            )
            continue

        frappe.get_doc(
            {
                "doctype": "Comment",
                "comment_type": "Comment",
                "comment_email": frappe.session.user,
                "reference_doctype": doctype,
                "reference_name": ref_name,
                "comment_by": frappe.session.user_fullname,
                "content": (
                    f"<u><b>{canal}</b></u> : rappel J-1 Event {e.name} ({horaire_lib})."
                ),
            }
        ).insert(ignore_permissions=True)


def _context_for_event(event, link_field, doctype, email_field, ref_name, date_lettres):
    """Résout téléphone client, e-mail, société affichée, créneau, tél. technicien (VT)."""
    values = frappe.db.get_value(
        doctype, ref_name, ["phone", email_field, "cost_center", "company"]
    )
    if not values:
        return None
    phone, email, cost_center, company_from_doc = values

    # SMS seulement si le numéro n'est pas un fixe 04 (AllMySMS le refuse).
    sms_possible = bool(phone) and not is_french_landline(phone)
    # Sans mobile ni e-mail, impossible de prévenir : on saute (un fixe
    # sans e-mail n'est pas une erreur — cas attendu, pas un bug).
    if not sms_possible and not email:
        return None

    company = _event_value(event, "custom_company") or company_from_doc
    # Même règle que la notification de devis : centre de coût « Riviera ».
    societe = "VT Riviera" if cost_center and "Riviera" in (cost_center or "") else company

    telephone_tech = None
    if link_field == "custom_visite_technique":
        employee = _primary_employee(event)
        if employee:
            telephone_tech = _telephone_technicien(employee)

    return {
        "phone": phone,
        "email": email,
        "sms_possible": sms_possible,
        "cost_center": cost_center,
        "societe": societe or company or "",
        "is_morning": _is_morning_slot(event),
        "telephone_tech": telephone_tech,
        "date_lettres": date_lettres,
    }


def _event_value(event, field):
    if isinstance(event, dict):
        return event.get(field)
    return getattr(event, field, None)


def _is_morning_slot(event) -> bool:
    """Matin si hour < 13 ; all_day → matin (8h–12h30), cf. docstring du module."""
    if _event_value(event, "all_day"):
        return True
    starts_on = _event_value(event, "starts_on")
    debut = get_datetime(starts_on) if starts_on else None
    if not debut:
        return True
    return debut.hour < 13


def _primary_employee(event):
    """Premier employé de l'Event (table enfant, sinon Link historique)."""
    rows = _event_value(event, EVENT_EMPLOYEE_FIELD)
    if rows:
        ids = employee_ids_from_rows(rows)
        if ids:
            return ids[0]

    name = _event_value(event, "name")
    if name and _event_employee_table_exists():
        child = _first_child_employee(name)
        if child:
            return child

    legacy = (_event_value(event, LEGACY_EMPLOYEE_FIELD) or "").strip()
    return legacy or None


def _event_employee_table_exists():
    try:
        return bool(frappe.db.table_exists("Event Employee"))
    except Exception:
        return False


def _first_child_employee(event_name):
    rows = frappe.db.sql(
        """
        SELECT employee
        FROM `tabEvent Employee`
        WHERE parent = %s
          AND parenttype = 'Event'
          AND IFNULL(employee, '') != ''
        ORDER BY idx ASC
        LIMIT 1
        """,
        event_name,
    )
    if rows and rows[0] and rows[0][0]:
        return rows[0][0]
    return None


def _telephone_technicien(employee_name: str) -> str | None:
    """Téléphone du technicien : Employee → User.mobile_no/phone, sinon Contact.user."""
    user_id, cell = frappe.db.get_value(
        "Employee", employee_name, ["user_id", "cell_number"]
    ) or (None, None)
    if cell:
        return cell
    if not user_id:
        return None

    mobile_no, phone = frappe.db.get_value("User", user_id, ["mobile_no", "phone"]) or (None, None)
    if mobile_no or phone:
        return mobile_no or phone

    contact_phone = frappe.db.get_value(
        "Contact",
        {"user": user_id},
        ["mobile_no", "phone"],
        as_dict=True,
    )
    if contact_phone:
        return contact_phone.mobile_no or contact_phone.phone
    return None


def _corps_email(cost_center, societe, titre, corps):
    """Construit le corps HTML de l'e-mail de rappel (inspiré de la notification de devis)."""
    logo_url = (
        frappe.db.get_value("Cost Center", cost_center, "custom_logo_url") if cost_center else None
    )
    logo_html = (
        f'<div style="text-align: center;">'
        f'<img src="{logo_url}" alt="{societe}" style="height: 60px; max-width: 100%;"></div>'
        if logo_url
        else ""
    )

    return f"""
<div style="font-family: Arial, sans-serif; background-color: #f8f9fa; margin: 0; padding: 40px 20px;">
    {logo_html}
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="border:0px!important; max-width: 100%;">
        <tr>
            <td align="center" style="padding: 40px 10px; border:none;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="max-width: 600px; width: 100%; background-color: #ffffff; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                    <tr>
                        <td style="padding: 15px; padding-top:40px; text-align: center; font-size: 22px; font-weight: bold; color: #333; border:none;">
                            {titre}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 30px 0 30px; font-size: 16px; color: #333; border:none;">
                            Madame, Monsieur,
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 20px 30px 0 30px; font-size: 16px; color: #333; line-height: 1.5; border:none;">
                            {corps}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 30px; font-size: 16px; color: #333; border:none;">
                            Cordialement,<br/>
                            L'équipe {societe}
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</div>
"""

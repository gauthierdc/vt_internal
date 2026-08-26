"""Tâches planifiées « Rappel J-1 » (fréquence : cron, tous les soirs à 18h).

Chaque soir, parcourt les événements (Event) du lendemain rattachés soit à une
Fiche de travail (chantier), soit à une Visite Technique. Pour chaque document,
on prévient le client de notre passage du lendemain :
  - par SMS si un numéro mobile est renseigné ;
  - sinon par e-mail (HTML) si une adresse est renseignée.
Les numéros fixes commençant par 04 (AllMySMS les refuse, HTTP 400) sont
traités comme s'il n'y avait pas de téléphone.
Si plusieurs événements portent sur le même document, on retient l'heure de
début la plus tôt.

Câblage de la fréquence dans hooks.py (scheduler_events > cron).
Source de vérité : ce fichier (versionné).
"""

import frappe
from frappe.core.doctype.sms_settings.sms_settings import send_sms
from frappe.utils import add_days, formatdate, get_datetime, getdate, today

from vt_internal.vt_internal.utils.phone import is_french_landline


def rappel_chantier():
    """Rappel pour les chantiers (événements liés à une Fiche de travail)."""
    _envoyer_rappels(
        link_field="custom_fiche_de_travail",
        doctype="Fiche de travail",
        email_field="contact_email",
        titre_email="Rappel de votre intervention",
        objet_email="Rappel : intervention prévue demain",
        modele_sms="Bonjour, notre équipe interviendra demain {horaire} dans le cadre de votre "
        "chantier. Cordialement, {societe}.",
        corps_email="Pour rappel, notre équipe interviendra <b>{date}</b>, {horaire}, "
        "dans le cadre de votre chantier.<br/><br/>"
        "Nous vous remercions de veiller à ce que l'accès au site soit possible à cet horaire.",
    )


def rappel_visite_technique():
    """Rappel pour les visites techniques (événements liés à une Visite Technique)."""
    _envoyer_rappels(
        link_field="custom_visite_technique",
        doctype="Visite Technique",
        email_field="email",
        titre_email="Rappel de votre visite technique",
        objet_email="Rappel : visite technique prévue demain",
        modele_sms="Bonjour, notre technicien réalisera demain {horaire} la visite technique "
        "prévue. Cordialement, {societe}.",
        corps_email="Pour rappel, notre technicien réalisera la visite technique "
        "<b>{date}</b>, {horaire}.<br/><br/>"
        "Nous vous remercions de veiller à être disponible à cet horaire.",
    )


def _envoyer_rappels(
    link_field, doctype, email_field, titre_email, objet_email, modele_sms, corps_email
):
    demain = add_days(today(), 1)
    date_lettres = f"le {formatdate(demain, 'EEEE d MMMM yyyy')}"

    # Événements du lendemain rattachés au document cible.
    events = frappe.get_all(
        "Event",
        filters={
            link_field: ["is", "set"],
            "starts_on": ["between", [f"{demain} 00:00:00", f"{demain} 23:59:59"]],
        },
        fields=["name", link_field, "starts_on", "all_day"],
    )

    if not events:
        return

    # Regroupement par document : on garde l'heure de début la plus tôt.
    docs = {}
    for e in events:
        ref = e[link_field]
        debut = get_datetime(e.starts_on) if e.starts_on else None
        info = docs.setdefault(ref, {"debut": None, "journee_entiere": False})
        if e.all_day:
            info["journee_entiere"] = True
        if debut and (info["debut"] is None or debut < info["debut"]):
            info["debut"] = debut

    for ref_name, info in docs.items():
        phone, email, cost_center, company = frappe.db.get_value(
            doctype, ref_name, ["phone", email_field, "cost_center", "company"]
        )
        # SMS seulement si le numéro n'est pas un fixe 04 (AllMySMS le refuse).
        sms_possible = bool(phone) and not is_french_landline(phone)
        # Sans mobile ni e-mail, impossible de prévenir : on saute (un fixe
        # sans e-mail n'est pas une erreur — cas attendu, pas un bug).
        if not sms_possible and not email:
            continue

        # Nom de la société affiché dans le message. Même règle que la notification
        # de devis : le centre de coût « Riviera » porte un autre nom commercial.
        societe = "VT Riviera" if cost_center and "Riviera" in cost_center else company

        # Ne considère l'heure que si l'événement n'est pas « journée entière ».
        debut = info["debut"]
        if info["journee_entiere"] or not debut or getdate(debut) != getdate(demain):
            horaire = "au cours de la journée"
        else:
            horaire = f"à partir de {debut.strftime('%Hh%M')}"

        # Canal : SMS si un mobile est renseigné, sinon repli sur l'e-mail.
        try:
            if sms_possible:
                msg = modele_sms.format(horaire=horaire, societe=societe)
                send_sms(receiver_list=[phone], msg=msg)
                canal = f"SMS de rappel envoyé au {phone}"
            else:
                corps_html = _corps_email(
                    cost_center=cost_center,
                    societe=societe,
                    titre=titre_email,
                    corps=corps_email.format(date=date_lettres, horaire=horaire),
                )
                frappe.sendmail(
                    recipients=[email],
                    subject=objet_email,
                    message=corps_html,
                    reference_doctype=doctype,
                    reference_name=ref_name,
                )
                canal = f"E-mail de rappel envoyé à {email}"
        except Exception as e:
            destinataire = phone if sms_possible else email
            frappe.log_error(
                f"Échec de l'envoi du rappel pour {doctype} {ref_name} ({destinataire}) : {e}",
                "Rappel intervention J-1",
            )
            continue

        # Trace sur le document source.
        frappe.get_doc(
            {
                "doctype": "Comment",
                "comment_type": "Comment",
                "comment_email": frappe.session.user,
                "reference_doctype": doctype,
                "reference_name": ref_name,
                "comment_by": frappe.session.user_fullname,
                "content": f"<u><b>{canal}</b></u> : rappel J-1 ({horaire}).",
            }
        ).insert(ignore_permissions=True)


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

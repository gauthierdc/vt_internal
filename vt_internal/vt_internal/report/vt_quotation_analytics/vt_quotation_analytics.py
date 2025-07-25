import frappe
from frappe import _
from frappe.utils import getdate
from collections import defaultdict
from datetime import date
from dateutil.relativedelta import relativedelta

def execute(filters=None):
    if not filters:
        filters = {}

    if getdate(filters.get("from_date")) > getdate(filters.get("to_date")):
        frappe.throw(_("From Date must be before To Date"))

    columns = get_columns(filters)
    data = get_data(filters)
    fieldtype = get_metric_fieldtype(filters.metric)
    skip_total_row = 0
    if fieldtype == "Percent" or fieldtype == "Data":
        skip_total_row = 1
    return columns, data, None, None, None, skip_total_row

def get_columns(filters):
    grouped_by = filters.get("grouped_by")
    metric = filters.get("metric")
    fieldname = get_fieldname(grouped_by)
    options = get_options(grouped_by)

    columns = [{
        "label": _(grouped_by),
        "fieldname": fieldname,
        "fieldtype": "Link" if options else "Data",
        "options": options,
        "width": 200
    }]

    if grouped_by == "Devis":
        columns.append({
            "label": _("Statut de suivi"),
            "fieldname": "statut_de_suivi",
            "fieldtype": "Data",
            "width": 150
        })

    fieldtype = get_metric_fieldtype(metric)
    precision = 2 if fieldtype == "Float" else None

    periods = get_periods(filters)
    for period in periods:
        columns.append({
            "label": period["label"],
            "fieldname": period["key"],
            "fieldtype": fieldtype,
            "precision": precision,
            "width": 150
        })

    columns.append({
        "label": _("Total"),
        "fieldname": "total",
        "fieldtype": fieldtype,
        "precision": precision,
        "width": 150
    })

    return columns

def get_metric_fieldtype(metric):
    if metric in ["Quantité de devis"]:
        return "Int"
    elif metric in ["Montant", "Montant attendu"]:
        return "Currency"
    elif metric in ["Pourcentage de relance (quantité)", "Pourcentage de relance (valeur)", "Taux de conversion (quantité)", "Taux de conversion (valeur)"]:
        return "Percent"
    return "Data"

def get_periods(filters):
    from_date = getdate(filters["from_date"])
    to_date = getdate(filters["to_date"])
    range_type = filters.get("range", "Mensuel")
    periods = []

    if range_type == "Hebdomadaire":
        current = from_date
        week_num = 1
        while current <= to_date:
            key = f"{from_date.year}_w{week_num}"
            label = f"Sem {week_num} ({current.strftime('%Y-%m-%d')})"
            end = current + relativedelta(days=6)
            if end > to_date:
                end = to_date
            periods.append({"key": key, "label": label, "start": current, "end": end})
            current = end + relativedelta(days=1)
            week_num += 1

    elif range_type == "Mensuel":
        current = date(from_date.year, from_date.month, 1)
        while current <= to_date:
            key = current.strftime("%Y_%m")
            label = current.strftime("%b %Y")
            end = current + relativedelta(months=1, days=-1)
            if end > to_date:
                end = to_date
            periods.append({"key": key, "label": label, "start": current, "end": end})
            current += relativedelta(months=1)

    elif range_type == "Trimestriel":
        current_year = from_date.year
        current_quarter = (from_date.month - 1) // 3 + 1
        while True:
            key = f"{current_year}_q{current_quarter}"
            label = f"Q{current_quarter} {current_year}"
            start_month = (current_quarter - 1) * 3 + 1
            start = date(current_year, start_month, 1)
            end = start + relativedelta(months=3, days=-1)
            if start > to_date:
                break
            if end > to_date:
                end = to_date
            if start < from_date:
                start = from_date
            periods.append({"key": key, "label": label, "start": start, "end": end})
            current_quarter += 1
            if current_quarter > 4:
                current_quarter = 1
                current_year += 1

    elif range_type == "Annuel":
        current_year = from_date.year
        while current_year <= to_date.year:
            key = str(current_year)
            label = str(current_year)
            start = date(current_year, 1, 1)
            end = date(current_year, 12, 31)
            if start < from_date:
                start = from_date
            if end > to_date:
                end = to_date
            periods.append({"key": key, "label": label, "start": start, "end": end})
            current_year += 1

    return periods

def get_data(filters):
    conditions, params = get_conditions(filters)
    quotations = frappe.db.sql("""
        SELECT 
            q.name AS quotation,
            q.party_name AS client,
            q.company,
            q.cost_center,
            q.transaction_date,
            q.grand_total AS montant,
            q.custom_expected_amount AS attendu,
            q.custom_responsable_du_devis AS responsable_du_devis,
            q.custom_insurance_client AS insurance,
            q.custom_type_de_projet AS type_de_projet,
            q.secteur_vt,
            q.custom_dernier_statut_de_suivi,
            q.status
        FROM `tabQuotation` q
        WHERE q.docstatus <> 2 AND {conditions}
    """.format(conditions=" AND ".join(conditions)), params, as_dict=1)

    grouped_by = filters.get("grouped_by")
    metric = filters.get("metric")
    range_type = filters.get("range", "Mensuel")

    aggregated = defaultdict(lambda: defaultdict(lambda: {
        'qty': 0,
        'montant': 0,
        'relance_qty': 0,
        'relance_montant': 0,
        'conv_qty': 0,
        'conv_montant': 0,
        'attendu': 0
    }))

    group_info = defaultdict(dict) if grouped_by == "Devis" else None

    period_agg = defaultdict(lambda: {
        'qty': 0,
        'montant': 0,
        'relance_qty': 0,
        'relance_montant': 0,
        'conv_qty': 0,
        'conv_montant': 0,
        'attendu': 0
    })

    grand_qty = 0
    grand_montant = 0
    grand_relance_qty = 0
    grand_relance_montant = 0
    grand_conv_qty = 0
    grand_conv_montant = 0
    grand_attendu = 0

    for quot in quotations:
        if not quot.transaction_date:
            continue
        period_key = get_period_key(quot.transaction_date, range_type)
        group_value = get_group_value(grouped_by, quot)

        if grouped_by == "Devis":
            if quot.status in ["Ordered", "Partially Ordered"]:
                group_info[group_value]["statut_de_suivi"] = "Commmandé"
            else:
                group_info[group_value]["statut_de_suivi"] = quot["custom_dernier_statut_de_suivi"] or ""

        is_relance = quot.custom_dernier_statut_de_suivi is not None and quot.custom_dernier_statut_de_suivi != "Relance manuelle"
        is_conv = quot.status in ["Ordered", "Partially Ordered"]

        montant = quot.montant or 0
        attendu = quot.attendu or 0

        aggregated[group_value][period_key]['qty'] += 1
        aggregated[group_value][period_key]['montant'] += montant
        aggregated[group_value][period_key]['attendu'] += attendu

        if is_relance:
            aggregated[group_value][period_key]['relance_qty'] += 1
            aggregated[group_value][period_key]['relance_montant'] += montant
        if is_conv:
            aggregated[group_value][period_key]['conv_qty'] += 1
            aggregated[group_value][period_key]['conv_montant'] += montant

        period_agg[period_key]['qty'] += 1
        period_agg[period_key]['montant'] += montant
        period_agg[period_key]['attendu'] += attendu

        if is_relance:
            period_agg[period_key]['relance_qty'] += 1
            period_agg[period_key]['relance_montant'] += montant
        if is_conv:
            period_agg[period_key]['conv_qty'] += 1
            period_agg[period_key]['conv_montant'] += montant

        grand_qty += 1
        grand_montant += montant
        grand_attendu += attendu
        if is_relance:
            grand_relance_qty += 1
            grand_relance_montant += montant
        if is_conv:
            grand_conv_qty += 1
            grand_conv_montant += montant

    periods = get_periods(filters)
    data = []
    fieldname = get_fieldname(grouped_by)

    for group in sorted(aggregated.keys()):
        row = {fieldname: group}
        if grouped_by == "Devis":
            row["statut_de_suivi"] = group_info[group]["statut_de_suivi"]
        group_total_qty = 0
        group_total_montant = 0
        group_total_relance_qty = 0
        group_total_relance_montant = 0
        group_total_conv_qty = 0
        group_total_conv_montant = 0
        group_total_attendu = 0

        for period in periods:
            p_key = period["key"]
            if p_key in aggregated[group]:
                qty = aggregated[group][p_key]['qty']
                montant = aggregated[group][p_key]['montant']
                relance_qty = aggregated[group][p_key]['relance_qty']
                relance_montant = aggregated[group][p_key]['relance_montant']
                conv_qty = aggregated[group][p_key]['conv_qty']
                conv_montant = aggregated[group][p_key]['conv_montant']
                attendu = aggregated[group][p_key]['attendu']

                value = get_metric_value(metric, qty, montant, relance_qty, relance_montant, conv_qty, conv_montant, attendu)
                row[p_key] = value

                group_total_qty += qty
                group_total_montant += montant
                group_total_relance_qty += relance_qty
                group_total_relance_montant += relance_montant
                group_total_conv_qty += conv_qty
                group_total_conv_montant += conv_montant
                group_total_attendu += attendu
            else:
                row[p_key] = 0

        total_value = get_metric_value(metric, group_total_qty, group_total_montant, group_total_relance_qty, group_total_relance_montant, group_total_conv_qty, group_total_conv_montant, group_total_attendu)
        row["total"] = total_value
        data.append(row)

    # Grand Total row
    if data:
        total_row = {fieldname: "Total"}

        for period in periods:
            p_key = period["key"]
            if p_key in period_agg:
                qty = period_agg[p_key]['qty']
                montant = period_agg[p_key]['montant']
                relance_qty = period_agg[p_key]['relance_qty']
                relance_montant = period_agg[p_key]['relance_montant']
                conv_qty = period_agg[p_key]['conv_qty']
                conv_montant = period_agg[p_key]['conv_montant']
                attendu = period_agg[p_key]['attendu']

                value = get_metric_value(metric, qty, montant, relance_qty, relance_montant, conv_qty, conv_montant, attendu)
                total_row[p_key] = value
            else:
                total_row[p_key] = 0

        grand_total_value = get_metric_value(metric, grand_qty, grand_montant, grand_relance_qty, grand_relance_montant, grand_conv_qty, grand_conv_montant, grand_attendu)
        total_row["total"] = grand_total_value
        #data.append(total_row)

    return data

def get_metric_value(metric, qty, montant, relance_qty, relance_montant, conv_qty, conv_montant, attendu):
    if metric == "Quantité de devis":
        return qty
    elif metric == "Montant":
        return montant
    elif metric == "Pourcentage de relance (quantité)":
        return (relance_qty / qty * 100) if qty > 0 else 0
    elif metric == "Pourcentage de relance (valeur)":
        return (relance_montant / montant * 100) if montant > 0 else 0
    elif metric == "Taux de conversion (quantité)":
        return (conv_qty / qty * 100) if qty > 0 else 0
    elif metric == "Taux de conversion (valeur)":
        return (conv_montant / montant * 100) if montant > 0 else 0
    elif metric == "Montant attendu":
        return attendu
    return 0

def get_conditions(filters):
    conditions = ["q.transaction_date >= %(from_date)s", "q.transaction_date <= %(to_date)s"]
    params = {
        "from_date": filters["from_date"],
        "to_date": filters["to_date"]
    }

    if filters.get("company"):
        conditions.append("q.company = %(company)s")
        params["company"] = filters["company"]

    if filters.get("secteur_vt"):
        conditions.append("q.secteur_vt = %(secteur_vt)s")
        params["secteur_vt"] = filters["secteur_vt"]

    if filters.get("assurance"):
        conditions.append("q.custom_insurance_client = %(assurance)s")
        params["assurance"] = filters["assurance"]

    if filters.get("responsable_du_devis"):
        conditions.append("q.custom_responsable_du_devis = %(responsable_du_devis)s")
        params["responsable_du_devis"] = filters["responsable_du_devis"]

    if filters.get("centre_de_cout"):
        cc = filters["centre_de_cout"]
        descendants = frappe.db.get_descendants("Cost Center", cc)
        centers = [cc] + descendants
        conditions.append("q.cost_center IN %(cost_centers)s")
        params["cost_centers"] = centers

    return conditions, params

def get_period_key(trans_date, range_type):
    trans_date = getdate(trans_date)
    if range_type == "Hebdomadaire":
        year, week, _ = trans_date.isocalendar()
        return f"{year}_w{week}"
    elif range_type == "Mensuel":
        return trans_date.strftime("%Y_%m")
    elif range_type == "Trimestriel":
        quarter = (trans_date.month - 1) // 3 + 1
        return f"{trans_date.year}_q{quarter}"
    elif range_type == "Annuel":
        return str(trans_date.year)

def get_group_value(grouped_by, quot):
    if grouped_by == "Devis":
        return quot["quotation"] or ""
    elif grouped_by == "Secteur VT":
        return quot["secteur_vt"] or ""
    elif grouped_by == "Assurance":
        return quot["insurance"] or ""
    elif grouped_by == "Centre de cout":
        return quot["cost_center"] or ""
    elif grouped_by == "Type de projet":
        return quot["type_de_projet"] or ""
    elif grouped_by == "Responsable du devis":
        return quot["responsable_du_devis"] or ""
    elif grouped_by == "Statut de suivi":
        if quot.status in ["Ordered", "Partially Ordered"]:
            return "Commandé"
        else:
            return quot["custom_dernier_statut_de_suivi"] or ""

def get_fieldname(grouped_by):
    if grouped_by == "Devis":
        return "quotation"
    elif grouped_by == "Secteur VT":
        return "secteur_vt"
    elif grouped_by == "Assurance":
        return "insurance"
    elif grouped_by == "Centre de cout":
        return "cost_center"
    elif grouped_by == "Type de projet":
        return "type_de_projet"
    elif grouped_by == "Responsable du devis":
        return "responsable_du_devis"
    elif grouped_by == "Statut de suivi":
        return "custom_dernier_statut_de_suivi"

def get_options(grouped_by):
    if grouped_by == "Devis":
        return "Quotation"
    elif grouped_by == "Secteur VT":
        return "Secteur VT"
    elif grouped_by == "Assurance":
        return "Customer"
    elif grouped_by == "Centre de cout":
        return "Cost Center"
    elif grouped_by == "Type de projet":
        return "Project Type"
    elif grouped_by == "Responsable du devis":
        return "User"
    elif grouped_by == "Statut de suivi":
        return ""
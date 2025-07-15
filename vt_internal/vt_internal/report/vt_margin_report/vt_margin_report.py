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
    return columns, data

def get_columns(filters):
    grouped_by = filters.get("grouped_by")
    fieldname = grouped_by.lower().replace(" ", "_")  # e.g., "centre_de_coût" -> "centre_de_cout", but since French, adjust
    if grouped_by == "Project":
        fieldname = "project"
    elif grouped_by == "Company":
        fieldname = "company"
    elif grouped_by == "cost_center":
        fieldname = "cost_center"

    columns = [{
        "label": _(grouped_by),
        "fieldname": fieldname,
        "fieldtype": "Link",
        "options": grouped_by,
        "width": 200
    }]

    periods = get_periods(filters)
    for period in periods:
        columns.append({
            "label": period["label"] if filters["value"] == "Marge réelle" else period["label"] + " (pp)",
            "fieldname": period["key"],
            "fieldtype": "Percent" if filters["value"] == "Marge réelle" else "Float",
            "width": 120
        })
        columns.append({
            "label": period["label"] + " Montant",
            "fieldname": period["key"] + "_montant",
            "fieldtype": "Currency",
            "width": 150
        })

    columns.append({
        "label": _("Total") if filters["value"] == "Marge réelle" else _("Total (pp)"),
        "fieldname": "total",
        "fieldtype": "Percent" if filters["value"] == "Marge réelle" else "Float",
        "width": 120
    })
    columns.append({
        "label": _("Total Montant"),
        "fieldname": "total_montant",
        "fieldtype": "Currency",
        "width": 150
    })

    return columns

def get_periods(filters):
    from_date = getdate(filters["from_date"])
    to_date = getdate(filters["to_date"])
    range_type = filters.get("range", "Mensuel")
    periods = []

    if range_type == "Mensuel":
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
    projects = frappe.db.sql("""
        SELECT 
            p.name AS project,
            p.company,
            p.cost_center,
            p.expected_end_date,
            p.total_sales_amount,
            p.total_billable_amount,
            p.total_costing_amount,
            p.total_purchase_cost,
            p.total_consumed_material_cost,
            p.total_expense_claim,
            (SELECT COALESCE(SUM(f.manufacturing_costs), 0) FROM `tabFabrication VT` f WHERE f.project = p.name) AS total_manufacturing_cost
        FROM `tabProject` p
        WHERE {conditions}
    """.format(conditions=" AND ".join(conditions)), params, as_dict=1)

    analysis_axis = filters.get("analysis_axis")
    value_type = filters.get("value")
    grouped_by = filters.get("grouped_by")
    range_type = filters.get("range", "Mensuel")

    aggregated = defaultdict(lambda: defaultdict(lambda: {
        'real_vente': 0, 'real_cost': 0, 'theo_vente': 0, 'theo_cost': 0
    }))

    period_agg = defaultdict(lambda: {
        'real_vente': 0, 'real_cost': 0, 'theo_vente': 0, 'theo_cost': 0
    })

    grand_real_vente = 0
    grand_real_cost = 0
    grand_theo_vente = 0
    grand_theo_cost = 0

    for project in projects:
        if not project.expected_end_date:
            continue
        period_key = get_period_key(project.expected_end_date, range_type)
        group_value = get_group_value(grouped_by, project)

        real_vente, real_cost = get_real_vente_cost(analysis_axis, project)
        theo_vente, theo_cost = get_theoretical(project.project, analysis_axis)

        aggregated[group_value][period_key]['real_vente'] += real_vente
        aggregated[group_value][period_key]['real_cost'] += real_cost
        aggregated[group_value][period_key]['theo_vente'] += theo_vente
        aggregated[group_value][period_key]['theo_cost'] += theo_cost

        period_agg[period_key]['real_vente'] += real_vente
        period_agg[period_key]['real_cost'] += real_cost
        period_agg[period_key]['theo_vente'] += theo_vente
        period_agg[period_key]['theo_cost'] += theo_cost

        grand_real_vente += real_vente
        grand_real_cost += real_cost
        grand_theo_vente += theo_vente
        grand_theo_cost += theo_cost

    periods = get_periods(filters)
    data = []
    fieldname = get_fieldname(grouped_by)
		
    for group in sorted(aggregated.keys()):
        row = {fieldname: group}
        group_total_real_vente = 0
        group_total_real_cost = 0
        group_total_theo_vente = 0
        group_total_theo_cost = 0

        for period in periods:
            p_key = period["key"]
            if p_key in aggregated[group]:
                rv = aggregated[group][p_key]['real_vente']
                rc = aggregated[group][p_key]['real_cost']
                tv = aggregated[group][p_key]['theo_vente']
                tc = aggregated[group][p_key]['theo_cost']

                real_m = (rv - rc) / rv * 100 if rv > 0 else 0
                theo_m = (tv - tc) / tv * 100 if tv > 0 else 0
                val = real_m if value_type == "Marge réelle" else real_m - theo_m
                row[p_key] = val

                montant_val = (rv - rc) if value_type == "Marge réelle" else ((rv - rc) - (tv - tc))
                row[p_key + "_montant"] = montant_val

                group_total_real_vente += rv
                group_total_real_cost += rc
                group_total_theo_vente += tv
                group_total_theo_cost += tc
            else:
                row[p_key] = 0
                row[p_key + "_montant"] = 0

        group_total_real_m = (group_total_real_vente - group_total_real_cost) / group_total_real_vente * 100 if group_total_real_vente > 0 else 0
        group_total_theo_m = (group_total_theo_vente - group_total_theo_cost) / group_total_theo_vente * 100 if group_total_theo_vente > 0 else 0
        row["total"] = group_total_real_m if value_type == "Marge réelle" else group_total_real_m - group_total_theo_m
        row["total_montant"] = (group_total_real_vente - group_total_real_cost) if value_type == "Marge réelle" else ((group_total_real_vente - group_total_real_cost) - (group_total_theo_vente - group_total_theo_cost))
        data.append(row)

    # Grand Total row
    if data:
        total_row = {fieldname: _("Grand Total")}
        grand_total_real_m = (grand_real_vente - grand_real_cost) / grand_real_vente * 100 if grand_real_vente > 0 else 0
        grand_total_theo_m = (grand_theo_vente - grand_theo_cost) / grand_theo_vente * 100 if grand_theo_vente > 0 else 0
        total_row["total"] = grand_total_real_m if value_type == "Marge réelle" else grand_total_real_m - grand_total_theo_m
        total_row["total_montant"] = (grand_real_vente - grand_real_cost) if value_type == "Marge réelle" else ((grand_real_vente - grand_real_cost) - (grand_theo_vente - grand_theo_cost))

        for period in periods:
            p_key = period["key"]
            if p_key in period_agg:
                rv = period_agg[p_key]['real_vente']
                rc = period_agg[p_key]['real_cost']
                tv = period_agg[p_key]['theo_vente']
                tc = period_agg[p_key]['theo_cost']

                real_m = (rv - rc) / rv * 100 if rv > 0 else 0
                theo_m = (tv - tc) / tv * 100 if tv > 0 else 0
                val = real_m if value_type == "Marge réelle" else real_m - theo_m
                total_row[p_key] = val

                montant_val = (rv - rc) if value_type == "Marge réelle" else ((rv - rc) - (tv - tc))
                total_row[p_key + "_montant"] = montant_val
            else:
                total_row[p_key] = 0
                total_row[p_key + "_montant"] = 0

        data.append(total_row)

    return data

def get_conditions(filters):
    conditions = ["p.status = 'Completed'"]
    params = {
        "from_date": filters["from_date"],
        "to_date": filters["to_date"]
    }
    conditions.append("p.expected_end_date >= %(from_date)s")
    conditions.append("p.expected_end_date <= %(to_date)s")

    if filters.get("company"):
        conditions.append("p.company = %(company)s")
        params["company"] = filters["company"]

    if filters.get("project"):
        conditions.append("p.name = %(project)s")
        params["project"] = filters["project"]

    if filters.get("cost_center"):
        cc = filters["cost_center"]
        descendants = frappe.db.get_descendants("Cost Center", cc)
        centers = [cc] + descendants
        conditions.append("p.cost_center IN %(cost_centers)s")
        params["cost_centers"] = centers
        
    if filters.get("quotation_owner"):
        conditions.append("p.custom_project_manager = %(quotation_owner)s")
        params["quotation_owner"] = filters["quotation_owner"]

    return conditions, params

def get_period_key(end_date, range_type):
    end_date = getdate(end_date)
    if range_type == "Mensuel":
        return end_date.strftime("%Y_%m")
    elif range_type == "Trimestriel":
        quarter = (end_date.month - 1) // 3 + 1
        return f"{end_date.year}_q{quarter}"
    elif range_type == "Annuel":
        return str(end_date.year)

def get_group_value(grouped_by, project):
    if grouped_by == "Project":
        return project["project"]
    elif grouped_by == "Company":
        return project["company"]
    elif grouped_by == "Cost Center":
        return project["cost_center"] or ""

def get_fieldname(grouped_by):
    if grouped_by == "Project":
        return "project"
    elif grouped_by == "Company":
        return "company"
    elif grouped_by == "Cost Center":
        return "cost_center"

def get_real_vente_cost(analysis_axis, project):
    theo_vente_tp, theo_cost_tp = get_theoretical(project["project"], "Temps passé")
    theo_vente_ach, theo_cost_ach= get_theoretical(project["project"], "Achats")
    if analysis_axis == "Marge globale":
        vente = theo_vente_ach + theo_vente_tp
        cost = (project["total_costing_amount"] or 0) + (project["total_purchase_cost"] or 0) + (project["total_consumed_material_cost"] or 0) + (project["total_expense_claim"] or 0) + (project["total_manufacturing_cost"] or 0)
    elif analysis_axis == "Temps passé":
        vente = theo_vente_tp
        cost = project["total_costing_amount"] or 0
    elif analysis_axis == "Achats":
        vente = theo_vente_tp + theo_vente_ach
        cost = (project["total_purchase_cost"] or 0) + (project["total_expense_claim"] or 0) + (project["total_consumed_material_cost"] or 0) + (project["total_manufacturing_cost"] or 0)
    return vente, cost

def get_theoretical(project, analysis_axis):
    item_group_condition = ""
    params = {"project": project}
    if analysis_axis == "Temps passé":
        item_group_condition = "AND i.custom_pose_vt = 1"
    elif analysis_axis == "Achats":
        item_group_condition = "AND NOT i.custom_pose_vt = 1"
		
    result = frappe.db.sql("""
        SELECT 
            SUM(soi.amount) AS vente,
            SUM(soi.qty * COALESCE(soi.base_unit_cost_price, 0)) AS cost
        FROM `tabSales Order Item` soi
        INNER JOIN `tabSales Order` so ON so.name = soi.parent
        INNER JOIN `tabItem` i ON i.name = soi.item_code
        WHERE so.project = %(project)s AND so.docstatus = 1 {item_group_condition}
    """.format(item_group_condition=item_group_condition), params, as_dict=1)
    
    if result and result[0]["vente"] is not None:
        return result[0]["vente"], result[0]["cost"]
    return 0, 0
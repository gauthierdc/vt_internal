# Copyright (c) 2025, Verre & Transparence and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe


def _matches_analysis_axis(custom_pose_vt, analysis_axis):
    """True if an Item's custom_pose_vt flag belongs to the requested axis."""
    is_pose = bool(custom_pose_vt)
    if analysis_axis == "Temps passé":
        return is_pose
    if analysis_axis == "Achats":
        return not is_pose
    return True


def _line_cost(qty, unit_cost):
    return (qty or 0) * (unit_cost or 0)


def compute_theoretical(sales_order_items, packed_items, analysis_axis="global"):
    """
    Theoretical (vente, cost) from Sales Order lines and Packed Item children.

    Vente uses Sales Order Item.amount, including Product Bundle **parent** lines.
    Packed Item.rate is never added to vente: those rates are internal and do not
    split the parent sell price (CC-2607-025: parent 2300.73 vs packed qty×rate ~7623).

    Cost prefers packed qty×base_unit_cost_price for bundles, plus
    qty×base_unit_cost_price on non-bundle SOI lines. If a bundle has no packed
    cost, fall back to the parent line cost so we neither drop nor double-count it.

    analysis_axis ("Temps passé" / "Achats" / anything else = global) filters via
    Item.custom_pose_vt on the relevant lines: SOI for vente and non-bundle cost,
    packed children for bundle cost.
    """
    packed_by_soi = defaultdict(list)
    for packed in packed_items or []:
        packed_by_soi[packed.get("parent_detail_docname")].append(packed)

    total_vente = 0.0
    total_cost = 0.0

    for soi in sales_order_items or []:
        soi_matches = _matches_analysis_axis(soi.get("custom_pose_vt"), analysis_axis)
        if soi_matches:
            total_vente += soi.get("amount") or 0

        soi_cost = _line_cost(soi.get("qty"), soi.get("base_unit_cost_price"))
        is_bundle = bool(soi.get("product_bundle_name"))
        if not is_bundle:
            if soi_matches:
                total_cost += soi_cost
            continue

        children = packed_by_soi.get(soi.get("name")) or []
        packed_cost_all = sum(
            _line_cost(child.get("qty"), child.get("base_unit_cost_price")) for child in children
        )
        if packed_cost_all:
            total_cost += sum(
                _line_cost(child.get("qty"), child.get("base_unit_cost_price"))
                for child in children
                if _matches_analysis_axis(child.get("custom_pose_vt"), analysis_axis)
            )
        elif soi_matches:
            total_cost += soi_cost

    return total_vente, total_cost


def _fetch_theoretical_source_rows(projects):
    """Submitted Sales Order Item + Packed Item rows for the given projects."""
    if not projects:
        return [], []
    if isinstance(projects, str):
        projects = [projects]

    placeholders = ", ".join(["%s"] * len(projects))
    params = tuple(projects)

    sales_order_items = frappe.db.sql(
        f"""
        SELECT
            so.project AS project,
            soi.name,
            soi.amount,
            soi.qty,
            soi.base_unit_cost_price,
            soi.product_bundle_name,
            i.custom_pose_vt
        FROM `tabSales Order Item` soi
        INNER JOIN `tabSales Order` so ON so.name = soi.parent
        INNER JOIN `tabItem` i ON i.name = soi.item_code
        WHERE so.project IN ({placeholders})
        AND so.docstatus = 1
        AND so.custom_exclude_from_statistics != 1
        """,
        params,
        as_dict=1,
    )

    packed_items = frappe.db.sql(
        f"""
        SELECT
            so.project AS project,
            pi.parent_detail_docname,
            pi.qty,
            pi.base_unit_cost_price,
            i.custom_pose_vt
        FROM `tabPacked Item` pi
        INNER JOIN `tabSales Order` so ON so.name = pi.parent AND pi.parenttype = 'Sales Order'
        INNER JOIN `tabItem` i ON i.name = pi.item_code
        WHERE so.project IN ({placeholders})
        AND so.docstatus = 1
        AND so.custom_exclude_from_statistics != 1
        """,
        params,
        as_dict=1,
    )

    return sales_order_items or [], packed_items or []


def get_theoretical(project, analysis_axis):
    """
    Calcule les ventes et coûts théoriques d'un projet basé sur les Sales Order Items.

    Args:
        project: Le nom du projet
        analysis_axis: "Temps passé", "Achats", ou autre pour global

    Returns:
        tuple: (total_vente, total_cost)
    """
    sales_order_items, packed_items = _fetch_theoretical_source_rows([project])
    return compute_theoretical(sales_order_items, packed_items, analysis_axis)


def get_theoretical_map(projects, analysis_axis="global"):
    """Batch (vente, cost) per project — same rules as get_theoretical."""
    sales_order_items, packed_items = _fetch_theoretical_source_rows(projects)
    soi_by_project = defaultdict(list)
    packed_by_project = defaultdict(list)
    for row in sales_order_items:
        soi_by_project[row.get("project")].append(row)
    for row in packed_items:
        packed_by_project[row.get("project")].append(row)

    return {
        name: compute_theoretical(
            soi_by_project.get(name, []),
            packed_by_project.get(name, []),
            analysis_axis,
        )
        for name in projects
    }


def get_project_costs(project_name):
    """
    Récupère les coûts réels d'un projet.
    
    Args:
        project_name: Le nom du projet
        
    Returns:
        dict: {
            'total_costing_amount': float,  # MO (timesheets)
            'total_purchase_order': float,  # Commandes fournisseur
            'total_consumed_material_cost': float,  # Matériaux consommés
            'total_expense_claim': float,  # Notes de frais
            'total_manufacturing_cost': float,  # Fabrications VT
            'total_real_cost': float,  # Total de tous les coûts
        }
    """
    # Récupérer les champs natifs du projet
    project = frappe.db.get_value(
        "Project",
        project_name,
        ["total_costing_amount", "total_consumed_material_cost", "total_expense_claim"],
        as_dict=True
    ) or {}
    
    total_costing_amount = project.get("total_costing_amount") or 0
    total_consumed_material_cost = project.get("total_consumed_material_cost") or 0
    total_expense_claim = project.get("total_expense_claim") or 0
    
    # Calculer total_purchase_order via SQL
    total_purchase_order = frappe.db.sql("""
        SELECT COALESCE(SUM(poi.amount), 0) as total
        FROM `tabPurchase Order Item` poi
        INNER JOIN `tabPurchase Order` po ON po.name = poi.parent
        WHERE poi.project = %s AND po.docstatus < 2
    """, project_name)[0][0] or 0
    
    # Calculer total_manufacturing_cost via SQL
    total_manufacturing_cost = frappe.db.sql("""
        SELECT COALESCE(SUM(manufacturing_costs), 0) as total
        FROM `tabFabrication VT`
        WHERE project = %s AND docstatus < 2
    """, project_name)[0][0] or 0
    
    total_real_cost = (
        total_costing_amount +
        total_purchase_order +
        total_consumed_material_cost +
        total_expense_claim +
        total_manufacturing_cost
    )
    
    return {
        'total_costing_amount': total_costing_amount,
        'total_purchase_order': total_purchase_order,
        'total_consumed_material_cost': total_consumed_material_cost,
        'total_expense_claim': total_expense_claim,
        'total_manufacturing_cost': total_manufacturing_cost,
        'total_real_cost': total_real_cost,
    }


def calculate_margin(vente, cost):
    """
    Calcule la marge en pourcentage.
    
    Args:
        vente: Montant des ventes
        cost: Montant des coûts
        
    Returns:
        float: Marge en pourcentage (0-100)
    """
    if not vente or vente == 0:
        return 0
    return (vente - cost) / vente * 100


def get_project_margins(project_name):
    """
    Calcule les marges théorique et réelle d'un projet.
    
    Args:
        project_name: Le nom du projet
        
    Returns:
        dict: {
            'theo_vente': float,
            'theo_cost': float,
            'theo_margin': float,
            'real_vente': float,
            'real_cost': float,
            'real_margin': float,
            'margin_diff': float,  # Écart en points de pourcentage
        }
    """
    # Calcul théorique
    theo_vente_tp, theo_cost_tp = get_theoretical(project_name, "Temps passé")
    theo_vente_ach, theo_cost_ach = get_theoretical(project_name, "Achats")
    
    theo_vente = theo_vente_tp + theo_vente_ach
    theo_cost = theo_cost_tp + theo_cost_ach
    theo_margin = calculate_margin(theo_vente, theo_cost)
    
    # Calcul réel
    real_vente = theo_vente  # Même base de vente
    costs = get_project_costs(project_name)
    real_cost = costs['total_real_cost']
    real_margin = calculate_margin(real_vente, real_cost)
    
    margin_diff = real_margin - theo_margin
    
    return {
        'theo_vente': theo_vente,
        'theo_cost': theo_cost,
        'theo_margin': theo_margin,
        'real_vente': real_vente,
        'real_cost': real_cost,
        'real_margin': real_margin,
        'margin_diff': margin_diff,
    }


def get_project_labour_hours(project_name):
    """
    Récupère les heures prévues et réalisées d'un projet.
    
    Args:
        project_name: Le nom du projet
        
    Returns:
        dict: {
            'expected_hours': float,
            'actual_hours': float,
            'hours_diff': float,
        }
    """
    # Heures prévues via Sales Orders
    expected_hours = frappe.db.sql("""
        SELECT COALESCE(SUM(custom_labour_hours), 0) as hours
        FROM `tabSales Order`
        WHERE project = %s AND docstatus = 1 AND custom_exclude_from_statistics != 1
    """, project_name)[0][0] or 0
    
    # Heures réalisées via Timesheets
    actual_hours = frappe.db.sql("""
        SELECT COALESCE(SUM(d.hours), 0) as hours
        FROM `tabTimesheet` t
        JOIN `tabTimesheet Detail` d ON d.parent = t.name
        WHERE d.project = %s AND t.docstatus != 2
    """, project_name)[0][0] or 0
    
    hours_diff = actual_hours - expected_hours
    
    return {
        'expected_hours': expected_hours,
        'actual_hours': actual_hours,
        'hours_diff': hours_diff,
    }

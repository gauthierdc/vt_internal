# Copyright (c) 2025, Verre & Transparence and contributors
# For license information, please see license.txt

import frappe


def get_theoretical(project, analysis_axis):
    """
    Calcule les ventes et coûts théoriques d'un projet basé sur les Sales Order Items.
    
    Args:
        project: Le nom du projet
        analysis_axis: "Temps passé", "Achats", ou autre pour global
        
    Returns:
        tuple: (total_vente, total_cost)
    """
    params = {"project": project}
    item_group_condition = ""

    if analysis_axis == "Temps passé":
        item_group_condition = "AND i.custom_pose_vt = 1"
    elif analysis_axis == "Achats":
        item_group_condition = "AND NOT i.custom_pose_vt = 1"

    # Récupération des ventes et coûts des lignes NON bundles
    regular_items = frappe.db.sql(f"""
        SELECT 
            SUM(soi.amount) AS vente,
            SUM(soi.qty * COALESCE(soi.base_unit_cost_price, 0)) AS cost
        FROM `tabSales Order Item` soi
        INNER JOIN `tabSales Order` so ON so.name = soi.parent
        INNER JOIN `tabItem` i ON i.name = soi.item_code
        WHERE so.project = %(project)s
        AND so.docstatus = 1
        AND so.custom_exclude_from_statistics != 1
        AND COALESCE(soi.product_bundle_name, '') = ''
        {item_group_condition}
    """, params, as_dict=1)[0]

    # Récupération des packed_items (enfants des bundles)
    packed_items = frappe.db.sql(f"""
        SELECT 
            SUM(pi.qty * pi.rate) AS vente,
            SUM(pi.qty * COALESCE(pi.base_unit_cost_price, 0)) AS cost
        FROM `tabPacked Item` pi
        INNER JOIN `tabSales Order` so ON so.name = pi.parent AND pi.parenttype = 'Sales Order'
        INNER JOIN `tabItem` i ON i.name = pi.item_code
        WHERE so.project = %(project)s
        AND so.docstatus = 1
        AND so.custom_exclude_from_statistics != 1
        {item_group_condition}
    """, params, as_dict=1)[0]

    total_vente = (regular_items.vente or 0) + (packed_items.vente or 0)
    total_cost = (regular_items.cost or 0) + (packed_items.cost or 0)

    return total_vente, total_cost


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

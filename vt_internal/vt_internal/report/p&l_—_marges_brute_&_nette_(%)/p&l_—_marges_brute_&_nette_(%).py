# Copyright (c) 2013, Frappe Technologies
# License: see license.txt

from __future__ import annotations

import copy
from typing import Dict, List, Any, Optional, Protocol

import frappe
from frappe import _
from frappe.utils import flt

from erpnext.accounts.report.financial_statements import (
	get_columns,
	get_data,
	get_period_list,
)

# ---- Typing / helpers -------------------------------------------------------

class Period(Protocol):
	key: str
	label: str

Row = Dict[str, Any]
Totals = Dict[str, float]

PERCENT_PREFIX = "%_"


def row_totals_for_periods(row: Row, period_list: List[Period]) -> Totals:
	return {p.key: flt(row.get(p.key, 0)) for p in period_list}


def interleave_percent_columns(columns: List[Dict[str, Any]], period_list: List[Period]) -> List[Dict[str, Any]]:
	"""Insère la colonne % juste après chaque colonne de période."""
	period_key_set = {p.key for p in period_list}
	new_cols: List[Dict[str, Any]] = []

	for col in columns:
		new_cols.append(col)
		fn = col.get("fieldname")
		if fn in period_key_set:
			new_cols.append({
				"label": f"{col.get('label', fn)} %",
				"fieldname": f"{PERCENT_PREFIX}{fn}",
				"fieldtype": "Percent",
				"width": 110,
			})

	return new_cols


def remove_parent_with_no_child(data: List[Row]) -> (List[Row], bool):
	data_to_be_removed = False
	for parent in list(data):
		if "is_group" in parent and parent.get("is_group") == 1:
			have_child = False
			for child in data:
				if "parent_account" in child and child.get("parent_account") == parent.get("account"):
					have_child = True
					break
			if not have_child:
				data_to_be_removed = True
				data.remove(parent)
	return data, data_to_be_removed


def adjust_account_totals(data: List[Row], period_list: List[Period]) -> None:
	"""Recalcule les totaux de groupes et propage 'total' de bas en haut (compatible ERPNext)."""
	totals: Totals = {}
	for d in reversed(data):
		if d.get("is_group"):
			for period in period_list:
				d[period.key] = sum(
					item[period.key] for item in data if item.get("parent_account") == d.get("account")
				)
		else:
			set_total(d, d["total"], data, totals)
		d["total"] = totals[d["account"]]


def set_total(node: Row, value: float, complete_list: List[Row], totals: Totals):
	if not totals.get(node["account"]):
		totals[node["account"]] = 0
	totals[node["account"]] += value

	parent = node["parent_account"]
	if parent != "":
		return set_total(
			next(item for item in complete_list if item["account"] == parent),
			value, complete_list, totals
		)


# ---- Calculs + % intégrés ---------------------------------------------------

def get_revenue(
	data: List[Row],
	period_list: List[Period],
	include_in_gross: int = 1,
	denominator_totals: Optional[Totals] = None,
	add_self_to_denominator: bool = False,
) -> List[Row]:
	"""
	Construit une section Produits/Charges, ajuste les totaux et calcule les % directement.
	- include_in_gross=1 : lignes 'brutes' (marge brute)
	- include_in_gross=0 : lignes 'nettes' (marge nette)
	- denominator_totals : base % imposée (par période)
	- add_self_to_denominator : si True, base = denominator_totals + totaux de la section
	"""
	revenue: List[Row] = [
		item for item in data if item["include_in_gross"] == include_in_gross or item["is_group"] == 1
	]

	# nettoyer les groupes orphelins
	data_to_be_removed = True
	while data_to_be_removed:
		revenue, data_to_be_removed = remove_parent_with_no_child(revenue)

	# totaux hiérarchiques
	adjust_account_totals(revenue, period_list)

	# base de % : soit imposée, soit la somme de la section elle-même
	if revenue and isinstance(revenue[0], dict):
		own_totals = row_totals_for_periods(revenue[0], period_list)
		base: Totals = {}
		for p in period_list:
			v = flt(denominator_totals.get(p.key, 0)) if denominator_totals else flt(own_totals.get(p.key, 0))
			if add_self_to_denominator:
				v += flt(own_totals.get(p.key, 0))
			base[p.key] = v

		for row in revenue:
			for p in period_list:
				key = p.key
				num = flt(row.get(key, 0))
				den = flt(base.get(key, 0))
				row[f"{PERCENT_PREFIX}{key}"] = round((num / den) * 100, 2) if den else None

	return copy.deepcopy(revenue)


def get_profit(
	gross_income: List[Row],
	gross_expense: List[Row],
	period_list: List[Period],
	company: str,
	profit_type: str,
	currency: Optional[str] = None,
	consolidated: bool = False,
) -> Optional[Row]:
	"""Ligne de marge brute, % sur produit brut."""
	profit_loss: Row = {
		"account_name": "'" + _(profit_type) + "'",
		"account": "'" + _(profit_type) + "'",
		"warn_if_negative": True,
		"currency": currency or frappe.get_cached_value("Company", company, "default_currency"),
	}

	has_value = False

	for period in period_list:
		key = period if consolidated else period.key
		gi = flt(gross_income[0].get(key, 0)) if gross_income else 0
		ge = flt(gross_expense[0].get(key, 0)) if gross_expense else 0
		value = gi - ge
		profit_loss[key] = value
		profit_loss[f"{PERCENT_PREFIX}{key}"] = round((value / gi) * 100, 2) if gi else None

		if value:
			has_value = True
			profit_loss["total"] = flt(profit_loss.get("total", 0)) + value

	return profit_loss if has_value else None


def get_net_profit(
	non_gross_income: List[Row],
	gross_income: List[Row],
	gross_expense: List[Row],
	non_gross_expense: List[Row],
	period_list: List[Period],
	company: str,
	currency: Optional[str] = None,
	consolidated: bool = False,
	denominator_totals: Optional[Totals] = None,  # CA (produit brut + produit net)
) -> Optional[Row]:
	"""Ligne de résultat net, % sur CA (produit brut + produit net)."""
	profit_loss: Row = {
		"account_name": "'" + _("Net Profit") + "'",
		"account": "'" + _("Net Profit") + "'",
		"warn_if_negative": True,
		"currency": currency or frappe.get_cached_value("Company", company, "default_currency"),
	}

	has_value = False

	for period in period_list:
		key = period if consolidated else period.key
		gi = flt(gross_income[0].get(key, 0)) if gross_income else 0
		ngi = flt(non_gross_income[0].get(key, 0)) if non_gross_income else 0
		ge = flt(gross_expense[0].get(key, 0)) if gross_expense else 0
		nge = flt(non_gross_expense[0].get(key, 0)) if non_gross_expense else 0

		total_income = gi + ngi
		value = flt(total_income) - flt(ge + nge)
		profit_loss[key] = value

		base = flt(denominator_totals.get(key, 0)) if denominator_totals else flt(total_income)
		profit_loss[f"{PERCENT_PREFIX}{key}"] = round((value / base) * 100, 2) if base else None

		if value:
			has_value = True
			profit_loss["total"] = flt(profit_loss.get("total", 0)) + value

	return profit_loss if has_value else None


# ---- Entrée du rapport ------------------------------------------------------

def execute(filters=None):
	period_list: List[Period] = get_period_list(
		filters.from_fiscal_year,
		filters.to_fiscal_year,
		filters.period_start_date,
		filters.period_end_date,
		filters.filter_based_on,
		filters.periodicity,
		filters.accumulated_values,
		filters.company,
	)

	columns: List[Dict[str, Any]] = []
	data: List[Row] = []

	income = get_data(
		filters.company,
		"Income",
		"Credit",
		period_list,
		filters=filters,
		accumulated_values=filters.accumulated_values,
		ignore_closing_entries=True,
		ignore_accumulated_values_for_fy=True,
		total=False,
	)

	expense = get_data(
		filters.company,
		"Expense",
		"Debit",
		period_list,
		filters=filters,
		accumulated_values=filters.accumulated_values,
		ignore_closing_entries=True,
		ignore_accumulated_values_for_fy=True,
		total=False,
	)

	columns = get_columns(
		filters.periodicity, period_list, filters.accumulated_values, filters.company
	)

	# 1) Produit brut (inclu marge brute), % sur produit brut
	gross_income = get_revenue(income, period_list, include_in_gross=1)

	# 2) Charges brutes, % sur produit brut
	gross_income_totals: Totals = row_totals_for_periods(gross_income[0], period_list) if gross_income else {}
	gross_expense = get_revenue(
		expense, period_list, include_in_gross=1, denominator_totals=gross_income_totals
	)

	# Cas sans lignes
	if len(gross_income) == 0 and len(gross_expense) == 0:
		data.append({
			"account_name": "'" + _("Nothing is included in gross") + "'",
			"account": "'" + _("Nothing is included in gross") + "'",
		})
		# colonnes intercalées (même si vides)
		columns = interleave_percent_columns(columns, period_list)
		return columns, data, None, None, []

	# Garde-fous
	if not gross_income:
		gross_income = [{}]
	if not gross_expense:
		gross_expense = [{}]

	# Bloc "Included in Gross Profit"
	data.append({"account_name": "'" + _("Included in Gross Profit") + "'", "account": "'" + _("Included in Gross Profit") + "'"})
	data.append({})
	data.extend(gross_income or [])
	data.append({})
	data.extend(gross_expense or [])

	# 3) Marge brute (%, base produit brut)
	data.append({})
	gross_profit = get_profit(
		gross_income, gross_expense, period_list, filters.company, "Gross Profit", filters.presentation_currency
	)
	if gross_profit:
		data.append(gross_profit)

	# 4) Produits nets : % sur CA (produit brut + produit net)
	non_gross_income = get_revenue(
		income,
		period_list,
		include_in_gross=0,
		denominator_totals=gross_income_totals,  # base partielle
		add_self_to_denominator=True,           # + propres totaux => CA
	)
	data.append({})
	data.extend(non_gross_income or [])

	# Totaux CA = produit brut + produit net (par période)
	non_gross_income_totals: Totals = row_totals_for_periods(non_gross_income[0], period_list) if non_gross_income else {}
	net_product_totals: Totals = {
		p.key: flt(gross_income_totals.get(p.key, 0)) + flt(non_gross_income_totals.get(p.key, 0))
		for p in period_list
	}

	# 5) Charges nettes : % sur CA
	non_gross_expense = get_revenue(
		expense,
		period_list,
		include_in_gross=0,
		denominator_totals=net_product_totals,
	)
	data.append({})
	data.extend(non_gross_expense or [])

	# 6) Résultat net : % sur CA
	net_profit = get_net_profit(
		non_gross_income,
		gross_income,
		gross_expense,
		non_gross_expense,
		period_list,
		filters.company,
		filters.presentation_currency,
		denominator_totals=net_product_totals,
	)
	data.append({})
	if net_profit:
		data.append(net_profit)

	# --- Colonnes : insérer les % juste après chaque période
	columns = interleave_percent_columns(columns, period_list)

	# --- KPIs d’en-tête (report_summary) avec ARRONDIS
	def safe_total(row: Optional[Row]) -> float:
		return flt((row or {}).get("total", 0))

	gross_income_total = safe_total(gross_income[0] if gross_income else None)
	non_gross_income_total = safe_total(non_gross_income[0] if non_gross_income else None)
	gross_profit_total = flt((gross_profit or {}).get("total", 0))
	net_profit_total = flt((net_profit or {}).get("total", 0))
	ca_total = flt(gross_income_total + non_gross_income_total)

	gross_margin_pct = (gross_profit_total / gross_income_total * 100) if gross_income_total else 0
	net_margin_pct = (net_profit_total / ca_total * 100) if ca_total else 0

	# Arrondis : montants à l’unité, % à 1 décimale
	gross_income_total_r = round(gross_income_total)
	net_profit_total_r = round(net_profit_total)
	gross_margin_pct_r = round(gross_margin_pct, 1)
	net_margin_pct_r = round(net_margin_pct, 1)

	report_summary = [
		{"label": _("Revenu brute"), "value": gross_income_total_r, "indicator": "Blue", "datatype": "Currency"},
		{"label": _("Marge brute %"), "value": gross_margin_pct_r, "datatype": "Percent", "indicator": "Green" if gross_margin_pct_r >= 0 else "Red"},
		{"label": _("Marge nette"), "value": net_profit_total_r, "datatype": "Currency", "indicator": "Green" if net_profit_total_r >= 0 else "Red"},
		{"label": _("Marge nette %"), "value": net_margin_pct_r, "datatype": "Percent", "indicator": "Green" if net_margin_pct_r >= 0 else "Red"},
	]

	# --- Courbe en ligne : % de marge brute uniquement
	labels = [p.label for p in period_list]
	gross_margin_series: List[float] = []
	for p in period_list:
		gi = flt(gross_income[0].get(p.key, 0)) if gross_income else 0
		# utiliser la ligne 'gross_profit' si elle existe, sinon recalcul
		if gross_profit:
			gp = flt(gross_profit.get(p.key, 0))
		else:
			ge = flt(gross_expense[0].get(p.key, 0)) if gross_expense else 0
			gp = gi - ge
		gross_margin_series.append(round((gp / gi) * 100, 2) if gi else 0)

	chart = {
		"data": {
			"labels": labels,
			"datasets": [
				{"name": _("Gross Margin %"), "values": gross_margin_series},
			],
		},
		"type": "line",
	}

	# Retour étendu : columns, data, message, chart, report_summary
	return columns, data, None, chart, report_summary

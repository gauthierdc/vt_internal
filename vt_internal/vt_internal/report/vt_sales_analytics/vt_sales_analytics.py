# Copyright (c) 2013, Frappe Technologies Pvt. Ltd.
# For license information, please see license.txt

import frappe
from frappe import _, scrub
from frappe.utils import add_days, add_to_date, flt, getdate, cint
from erpnext.accounts.utils import get_fiscal_year


def execute(filters=None):
    return Analytics(filters).run()


class Analytics(object):
    def __init__(self, filters=None):
        self.filters = frappe._dict(filters or {})
        self.filters.doc_type = "Sales Order"
        self.date_field = (
            "transaction_date"
            if self.filters.doc_type in ["Sales Order", "Purchase Order"]
            else "posting_date"
        )
        self.months = [
            "Jan", "Feb", "Mar", "Apr", "May", "Jun",
            "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
        ]
        # Nouveau : axe colonnes
        self.column_by = (self.filters.get("column_by") or "Période")

        if self.filters.get("tree_type") == "Secteur VT":
            self.filters.tree_type = "Secteur VT"

        self.get_period_date_ranges()

    # ----------------------------- Run ---------------------------------------

    def run(self):
        """
        Si colonnes = périodes, on peut construire les colonnes avant les données.
        Sinon on a besoin des données pour connaître les valeurs distinctes de col_entity.
        """
        if self.column_by == "Période":
            self.get_columns()
            self.get_data()
        else:
            self.get_data()
            self.get_columns()

        self.get_chart_data()

        skip_total_row = 0
        if self.filters.tree_type in ["Supplier Group", "Item Group", "Customer Group", "Territory"]:
            skip_total_row = 1

        return self.columns, self.data, None, self.chart, None, skip_total_row

    # ----------------------------- Helpers pivot -----------------------------

    def get_col_entity_select(self, table_alias="s", item_alias=None):
        """
        Pour SQL: renvoie (select_expression, label, fieldtype, options) pour la colonne dynamique.
        Si Période, None (on reste sur les dates).
        """
        if self.column_by == "Période":
            return (None, None, None, None)

        match self.column_by:
            case "Secteur VT":
                return (f"{table_alias}.secteur_vt as col_entity", _("Secteur VT"), "Link", "Secteur VT")
            case "Assurance":
                return (f"{table_alias}.custom_insurance_client as col_entity", _("Assurance"), "Data", "")
            case "Responsable du devis":
                return (f"{table_alias}.custom_responsable_du_devis as col_entity", _("Responsable du devis"), "Link", "User")
            # (Retiré: case "Origine" — on ne permet plus column_by = "Origine")
            case _:
                return (None, None, None, None)

    def get_col_entity_field_for_get_all(self):
        """
        Pour frappe.get_all: champ équivalent 'as col_entity' si disponible sans jointure.
        (Origine nécessite une jointure et n'est donc pas proposée ici.)
        """
        if self.column_by == "Période":
            return None
        if self.column_by == "Secteur VT":
            return "secteur_vt as col_entity"
        if self.column_by == "Assurance":
            return "custom_insurance_client as col_entity"
        if self.column_by == "Responsable du devis":
            return "custom_responsable_du_devis as col_entity"
        # Origine -> non pris en charge via get_all (besoin de jointure item)
        return None

    def current_col_key(self, d):
        """Clé de colonne effective selon le mode."""
        if self.column_by == "Période":
            return self.get_period(d.get(self.date_field))
        return (getattr(d, "col_entity", None) or _("(vide)"))

    # ----------------------------- Colonnes ----------------------------------

    def get_columns(self):
        # 1) Colonne d'entité (ligne)
        if self.filters.tree_type == "Secteur VT":
            self.columns = [
                {
                    "label": _("Secteur"),
                    "options": "Secteur VT",
                    "fieldname": "entity",
                    "fieldtype": "Link",
                    "width": 140,
                }
            ]
        else:
            match self.filters.tree_type:
                case "Order Type" | "Origine" | "Assurance":
                    options, fieldtype = "", "Data"
                    label = _(self.filters.tree_type)
                case "Par verre":
                    options, fieldtype = "Item", "Link"
                    label = _(self.filters.tree_type)
                case "Responsable du devis":
                    options, fieldtype = "User", "Link"
                    label = _("User")
                case _:
                    options, fieldtype = self.filters.tree_type, "Link"
                    label = _(self.filters.tree_type)
            self.columns = [
                {
                    "label": label,
                    "options": options,
                    "fieldname": "entity",
                    "fieldtype": fieldtype,
                    "width": 200 if self.filters.tree_type in ["Order Type", "Origine", "Assurance"] else 140,
                }
            ]

        if self.filters.tree_type in ["Customer", "Supplier", "Item"]:
            self.columns.append(
                {
                    "label": _(self.filters.tree_type + " Name") if self.filters.tree_type != "Item" else _("Item Name"),
                    "fieldname": "entity_name",
                    "fieldtype": "Data",
                    "width": 140,
                }
            )

        if self.filters.tree_type == "Item":
            self.columns.append(
                {
                    "label": _("UOM"),
                    "fieldname": "stock_uom",
                    "fieldtype": "Link",
                    "options": "UOM",
                    "width": 100,
                }
            )

        # 2) Colonnes dynamiques
        if self.column_by == "Période":
            for end_date in self.periodic_daterange:
                period = self.get_period(end_date)
                self.columns.append(
                    {"label": _(period), "fieldname": scrub(period), "fieldtype": "Float", "width": 120}
                )
        else:
            # Valeurs distinctes rencontrées dans les données
            for key in sorted(self.all_column_keys or []):
                self.columns.append(
                    {"label": _(str(key)), "fieldname": scrub(str(key)), "fieldtype": "Float", "width": 140}
                )

        self.columns.append({"label": _("Total"), "fieldname": "total", "fieldtype": "Float", "width": 120})

    # ----------------------------- Données -----------------------------------

    def get_data(self):
        if self.filters.tree_type == "Par verre":
            self.get_sales_transactions_based_on_glass()
            self.get_rows_or_groups()
        elif self.filters.tree_type == "Secteur VT":
            self.get_sales_transactions_based_on_secteur()
            self.get_rows_or_groups(grouped=True)
        elif self.filters.tree_type in ["Customer", "Supplier"]:
            self.get_sales_transactions_based_on_customers_or_suppliers()
            self.get_rows_or_groups()
        elif self.filters.tree_type == "Item":
            self.get_sales_transactions_based_on_items()
            self.get_rows_or_groups()
        elif self.filters.tree_type in ["Customer Group", "Supplier Group", "Territory"]:
            self.get_sales_transactions_based_on_customer_or_territory_group()
            self.get_rows_or_groups(grouped=True)
        elif self.filters.tree_type == "Item Group":
            self.get_sales_transactions_based_on_item_group()
            self.get_rows_or_groups(grouped=True)
        elif self.filters.tree_type == "Order Type":
            self.get_sales_transactions_based_on_order_type()
            self.get_rows_or_groups(grouped=True)  # garde la hiérarchie "Order Types"
        elif self.filters.tree_type == "Origine":
            self.get_sales_transactions_based_on_origine()
            self.get_rows_or_groups()
        elif self.filters.tree_type == "Assurance":
            self.get_sales_transactions_based_on_assurance()
            self.get_rows_or_groups()
        elif self.filters.tree_type == "Project":
            self.get_sales_transactions_based_on_project()
            self.get_rows_or_groups()
        elif self.filters.tree_type == "Responsable du devis":
            self.get_sales_transactions_based_on_responsable()
            self.get_rows_or_groups()

    # ----------------------------- Fetchers ----------------------------------

    def _common_filters_dict(self):
        filters = {
            "docstatus": 1,
            "company": self.filters.company,
            self.date_field: ("between", [self.filters.from_date, self.filters.to_date]),
        }
        if self.filters.get("secteur"):
            filters["secteur_vt"] = self.filters.secteur
        if self.filters.get("cost_center"):
            filters["cost_center"] = self.filters.cost_center
        if self.filters.get("insurance"):
            filters["custom_insurance_client"] = self.filters.insurance
        if self.filters.get("custom_responsable_du_devis"):
            filters["custom_responsable_du_devis"] = self.filters.custom_responsable_du_devis
        return filters

    def _common_sql_filters(self, alias="s"):
        secteur_filter = ""
        cost_center_filter = ""
        insurance_filter = ""
        responsable_filter = ""
        params = [self.filters.company, self.filters.from_date, self.filters.to_date]

        if self.filters.get("secteur"):
            secteur_filter = f" and {alias}.secteur_vt = %s"
            params.append(self.filters.secteur)
        if self.filters.get("cost_center"):
            cost_center_filter = f" and {alias}.cost_center = %s"
            params.append(self.filters.cost_center)
        if self.filters.get("insurance"):
            insurance_filter = f" and {alias}.custom_insurance_client = %s"
            params.append(self.filters.insurance)
        if self.filters.get("custom_responsable_du_devis"):
            responsable_filter = f" and {alias}.custom_responsable_du_devis = %s"
            params.append(self.filters.custom_responsable_du_devis)

        return secteur_filter, cost_center_filter, insurance_filter, responsable_filter, params

    # -- Secteur (hiérarchique) via get_all
    def get_sales_transactions_based_on_secteur(self):
        value_field = "base_net_total as value_field" if self.filters["value_quantity"] == "Value" else "total_qty as value_field"
        fields = ["secteur_vt as entity", value_field, self.date_field]
        col_field = self.get_col_entity_field_for_get_all()
        if col_field:
            fields.append(col_field)

        self.entries = frappe.get_all(
            self.filters.doc_type,
            fields=fields,
            filters=self._common_filters_dict(),
        )
        self.get_secteur_groups()

    def get_secteur_groups(self):
        self.depth_map = frappe._dict()
        self.group_entries = frappe.db.sql(
            """select name from `tabSecteur VT` order by name""",
            as_dict=1,
        )
        for d in self.group_entries:
            self.depth_map.setdefault(d["name"], 0)

    # -- Order Type (SQL)
    def get_sales_transactions_based_on_order_type(self):
        value_field = "base_net_total" if self.filters["value_quantity"] == "Value" else "total_qty"
        secteur_filter, cost_center_filter, insurance_filter, responsable_filter, params = self._common_sql_filters("s")
        col_select, _, _, _ = self.get_col_entity_select("s", item_alias="i")

        select_col = f", {col_select}" if (col_select and self.column_by != "Période") else ""
        date_select = f", s.{self.date_field}" if self.column_by == "Période" else ""

        self.entries = frappe.db.sql(
            f"""
            select s.order_type as entity, s.{value_field} as value_field{date_select}{select_col}
            from `tabSales Order` s
            where s.docstatus = 1 and s.company = %s and s.{self.date_field} between %s and %s
              and ifnull(s.order_type, '') != ''{secteur_filter}{cost_center_filter}{insurance_filter}{responsable_filter}
            order by s.order_type
            """,
            tuple(params),
            as_dict=1,
        )
        self.get_teams()

    # -- Origine (SQL)
    def get_sales_transactions_based_on_origine(self):
        value_field = "SUM(i.base_net_amount)" if self.filters["value_quantity"] == "Value" else "COUNT(DISTINCT s.name)"
        secteur_filter, cost_center_filter, insurance_filter, responsable_filter, params = self._common_sql_filters("s")
        # colonne dynamique éventuelle
        col_select, _, _, _ = self.get_col_entity_select("s", item_alias="i")
        select_col = f", {col_select}" if (col_select and self.column_by != "Période") else ""
        date_select = f", s.{self.date_field}" if self.column_by == "Période" else ""

        self.entries = frappe.db.sql(
            f"""
            select 
                case when i.prevdoc_docname is not null then 'Devis' else 'Commande' end as entity,
                {value_field} as value_field
                {date_select}
                {select_col}
            from `tabSales Order Item` i
            join `tabSales Order` s on s.name = i.parent
            where s.docstatus = 1 and s.company = %s
              and s.{self.date_field} between %s and %s
              {secteur_filter}{cost_center_filter}{insurance_filter}{responsable_filter}
            group by entity{', s.' + self.date_field if self.column_by == 'Période' else ''}{', col_entity' if (self.column_by != 'Période' and select_col) else ''}
            """,
            tuple(params),
            as_dict=1,
        )

    # -- Assurance (SQL)
    def get_sales_transactions_based_on_assurance(self):
        value_field = "SUM(s.base_net_total)" if self.filters["value_quantity"] == "Value" else "COUNT(DISTINCT s.name)"
        secteur_filter, cost_center_filter, insurance_filter, responsable_filter, params = self._common_sql_filters("s")
        col_select, _, _, _ = self.get_col_entity_select("s", item_alias="i")
        select_col = f", {col_select}" if (col_select and self.column_by != "Période") else ""
        date_select = f", s.{self.date_field}" if self.column_by == "Période" else ""

        self.entries = frappe.db.sql(
            f"""
            select s.custom_insurance_client as entity, {value_field} as value_field{date_select}{select_col}
            from `tabSales Order` s
            where s.docstatus = 1 and s.company = %s and s.{self.date_field} between %s and %s
              {secteur_filter}{cost_center_filter}{insurance_filter}{responsable_filter}
            group by entity{', s.' + self.date_field if self.column_by == 'Période' else ''}{', col_entity' if (self.column_by != 'Période' and select_col) else ''}
            """,
            tuple(params),
            as_dict=1,
        )

    # -- Customer / Supplier (get_all)
    def get_sales_transactions_based_on_customers_or_suppliers(self):
        value_field = "base_net_total as value_field" if self.filters["value_quantity"] == "Value" else "total_qty as value_field"

        if self.filters.tree_type == "Customer":
            entity = "customer as entity"
            entity_name = "customer_name as entity_name"
        else:
            entity = "supplier as entity"
            entity_name = "supplier_name as entity_name"

        fields = [entity, entity_name, value_field, self.date_field]
        col_field = self.get_col_entity_field_for_get_all()
        if col_field:
            fields.append(col_field)

        self.entries = frappe.get_all(
            "Sales Order",
            fields=fields,
            filters=self._common_filters_dict(),
        )

        self.entity_names = {}
        for d in self.entries:
            self.entity_names.setdefault(d.entity, d.entity_name)

    # -- Items (SQL)
    def get_sales_transactions_based_on_items(self):
        value_field = "base_net_amount" if self.filters["value_quantity"] == "Value" else "stock_qty"
        secteur_filter, cost_center_filter, insurance_filter, responsable_filter, params = self._common_sql_filters("s")
        col_select, _, _, _ = self.get_col_entity_select("s", item_alias="i")
        select_col = f", {col_select}" if (col_select and self.column_by != "Période") else ""
        date_select = f", s.{self.date_field}" if self.column_by == "Période" else ""

        self.entries = frappe.db.sql(
            f"""
            select i.item_code as entity, i.item_name as entity_name, i.stock_uom,
                   i.{value_field} as value_field{date_select}{select_col}
            from `tabSales Order Item` i
            join `tabSales Order` s on s.name = i.parent
            where i.docstatus = 1 and s.company = %s
              and s.{self.date_field} between %s and %s
              {secteur_filter}{cost_center_filter}{insurance_filter}{responsable_filter}
            """,
            tuple(params),
            as_dict=1,
        )

        self.entity_names = {}
        for d in self.entries:
            self.entity_names.setdefault(d.entity, d.entity_name)

    # -- Customer Group / Supplier Group / Territory (get_all + tree)
    def get_sales_transactions_based_on_customer_or_territory_group(self):
        value_field = "base_net_total as value_field" if self.filters["value_quantity"] == "Value" else "total_qty as value_field"

        if self.filters.tree_type == "Customer Group":
            entity_field = "customer_group as entity"
        elif self.filters.tree_type == "Supplier Group":
            entity_field = "supplier as entity"
            self.get_supplier_parent_child_map()
        else:
            entity_field = "territory as entity"

        fields = [entity_field, value_field, self.date_field]
        col_field = self.get_col_entity_field_for_get_all()
        if col_field:
            fields.append(col_field)

        self.entries = frappe.get_all(
            "Sales Order",
            fields=fields,
            filters=self._common_filters_dict(),
        )
        self.get_groups()

    # -- Item Group (SQL)
    def get_sales_transactions_based_on_item_group(self):
        value_field = "base_net_amount" if self.filters["value_quantity"] == "Value" else "qty"
        secteur_filter, cost_center_filter, insurance_filter, responsable_filter, params = self._common_sql_filters("s")
        col_select, _, _, _ = self.get_col_entity_select("s", item_alias="i")
        select_col = f", {col_select}" if (col_select and self.column_by != "Période") else ""
        date_select = f", s.{self.date_field}" if self.column_by == "Période" else ""

        self.entries = frappe.db.sql(
            f"""
            select i.item_group as entity, i.{value_field} as value_field{date_select}{select_col}
            from `tabSales Order Item` i
            join `tabSales Order` s on s.name = i.parent
            where i.docstatus = 1 and s.company = %s
              and s.{self.date_field} between %s and %s
              {secteur_filter}{cost_center_filter}{insurance_filter}{responsable_filter}
            """,
            tuple(params),
            as_dict=1,
        )

        self.get_groups()

    # -- Project (get_all)
    def get_sales_transactions_based_on_project(self):
        value_field = "base_net_total as value_field" if self.filters["value_quantity"] == "Value" else "total_qty as value_field"

        fields = ["project as entity", value_field, self.date_field]
        col_field = self.get_col_entity_field_for_get_all()
        if col_field:
            fields.append(col_field)

        filters = self._common_filters_dict()
        filters["project"] = ["!=", ""]

        self.entries = frappe.get_all(
            "Sales Order",
            fields=fields,
            filters=filters,
        )

    # -- Responsable (get_all)
    def get_sales_transactions_based_on_responsable(self):
        value_field = "base_net_total as value_field" if self.filters["value_quantity"] == "Value" else "total_qty as value_field"

        fields = ["custom_responsable_du_devis as entity", value_field, self.date_field]
        col_field = self.get_col_entity_field_for_get_all()
        if col_field:
            fields.append(col_field)

        self.entries = frappe.get_all(
            "Sales Order",
            fields=fields,
            filters=self._common_filters_dict(),
        )

    # -- Par verre (SQL)
    def get_sales_transactions_based_on_glass(self):
        if self.filters["value_quantity"] == "Value":
            value_field = "SUM(soi.base_net_amount) AS value_field"
        else:
            value_field = "SUM((bom.hauteur / 1000) * (bom.largeur / 1000)) AS value_field"

        secteur_filter, cost_center_filter, insurance_filter, responsable_filter, params = self._common_sql_filters("so")
        col_select, _, _, _ = self.get_col_entity_select("so", item_alias="soi")
        select_col = f", {col_select}" if (col_select and self.column_by != "Période") else ""
        date_select = f", so.{self.date_field}" if self.column_by == "Période" else ""

        self.entries = frappe.db.sql(
            f"""
            SELECT
                (
                    SELECT bi.item_code
                    FROM `tabBOM Item` bi
                    WHERE bi.parent = bom.name
                    ORDER BY bi.idx ASC
                    LIMIT 1
                ) AS entity,
                {value_field}
                {date_select}
                {select_col}
            FROM `tabSales Order Item` soi
            JOIN `tabSales Order` so ON soi.parent = so.name
            JOIN `tabBOM` bom ON soi.bom_no = bom.name
            WHERE so.docstatus = 1
              AND soi.item_code IN ('Produit fini (double vitrage)', 'Produit fini (verre)')
              AND so.company = %s
              AND so.{self.date_field} BETWEEN %s AND %s
              {secteur_filter}{cost_center_filter}{insurance_filter}{responsable_filter}
            GROUP BY entity{', so.' + self.date_field if self.column_by == 'Période' else ''}{', col_entity' if (self.column_by != 'Période' and select_col) else ''}
            """,
            tuple(params),
            as_dict=1,
        )

    # ----------------------------- Agrégation 2D -----------------------------

    def get_rows_or_groups(self, grouped=False):
        self.get_periodic_data()

        if grouped:
            self.get_rows_by_group_generic()
        else:
            self.get_rows_generic()

    def iter_column_labels(self):
        if self.column_by == "Période":
            return [self.get_period(d) for d in self.periodic_daterange]
        else:
            return sorted(self.all_column_keys or [])

    def get_rows_generic(self):
        self.data = []
        col_labels = self.iter_column_labels()

        for entity, pdata in self.entity_periodic_data.items():
            row = {
                "entity": entity,
                "entity_name": getattr(self, "entity_names", {}).get(entity),
            }
            total = 0.0
            for label in col_labels:
                amount = flt(pdata.get(label, 0.0))
                row[scrub(str(label))] = amount
                total += amount
            row["total"] = total
            if self.filters.tree_type == "Item":
                row["stock_uom"] = pdata.get("stock_uom")
            self.data.append(row)

    def get_rows_by_group_generic(self):
        col_labels = self.iter_column_labels()
        out = []

        for d in reversed(self.group_entries):
            row = {"entity": d.name, "indent": self.depth_map.get(d.name)}
            total = 0.0
            for label in col_labels:
                amount = flt(self.entity_periodic_data.get(d.name, {}).get(label, 0.0))
                row[scrub(str(label))] = amount
                if d.parent and (self.filters.tree_type != "Order Type" or d.parent == "Order Types"):
                    self.entity_periodic_data.setdefault(d.parent, frappe._dict()).setdefault(label, 0.0)
                    self.entity_periodic_data[d.parent][label] += amount
                total += amount
            row["total"] = total
            out = [row] + out

        self.data = out

    def get_periodic_data(self):
        self.entity_periodic_data = frappe._dict()
        self.all_column_keys = set()

        for d in self.entries:
            if self.filters.tree_type == "Supplier Group":
                d.entity = self.parent_child_map.get(d.entity)

            col_key = self.current_col_key(d)
            self.all_column_keys.add(col_key)

            self.entity_periodic_data.setdefault(d.entity, frappe._dict()).setdefault(col_key, 0.0)
            self.entity_periodic_data[d.entity][col_key] += flt(d.value_field)

            if self.filters.tree_type == "Item":
                self.entity_periodic_data[d.entity]["stock_uom"] = getattr(d, "stock_uom", None)

    # ----------------------------- Périodes ----------------------------------

    def get_period(self, posting_date):
        if self.filters.range == "Weekly":
            period = _("Week {0} {1}").format(str(posting_date.isocalendar()[1]), str(posting_date.year))
        elif self.filters.range == "Monthly":
            period = _(str(self.months[posting_date.month - 1])) + " " + str(posting_date.year)
        elif self.filters.range == "Quarterly":
            period = _("Quarter {0} {1}").format(
                str(((posting_date.month - 1) // 3) + 1), str(posting_date.year)
            )
        else:
            year = get_fiscal_year(posting_date, company=self.filters.company)
            period = str(year[0])
        return period

    def get_period_date_ranges(self):
        from dateutil.relativedelta import MO, relativedelta

        from_date, to_date = getdate(self.filters.from_date), getdate(self.filters.to_date)

        increment = {"Monthly": 1, "Quarterly": 3, "Half-Yearly": 6, "Yearly": 12}.get(
            self.filters.range, 1
        )

        if self.filters.range in ["Monthly", "Quarterly"]:
            from_date = from_date.replace(day=1)
        elif self.filters.range == "Yearly":
            from_date = get_fiscal_year(from_date)[1]
        else:
            from_date = from_date + relativedelta(from_date, weekday=MO(-1))

        self.periodic_daterange = []
        for dummy in range(1, 53):
            if self.filters.range == "Weekly":
                period_end_date = add_days(from_date, 6)
            else:
                period_end_date = add_to_date(from_date, months=increment, days=-1)

            if period_end_date > to_date:
                period_end_date = to_date

            self.periodic_daterange.append(period_end_date)

            from_date = add_days(period_end_date, 1)
            if period_end_date == to_date:
                break

    # ----------------------------- Groupes -----------------------------------

    def get_groups(self):
        if self.filters.tree_type == "Territory":
            parent = "parent_territory"
        if self.filters.tree_type == "Customer Group":
            parent = "parent_customer_group"
        if self.filters.tree_type == "Item Group":
            parent = "parent_item_group"
        if self.filters.tree_type == "Supplier Group":
            parent = "parent_supplier_group"

        self.depth_map = frappe._dict()

        self.group_entries = frappe.db.sql(
            """select name, lft, rgt , {parent} as parent
            from `tab{tree}` order by lft""".format(
                tree=self.filters.tree_type, parent=parent
            ),
            as_dict=1,
        )

        for d in self.group_entries:
            if d.parent:
                self.depth_map.setdefault(d.name, self.depth_map.get(d.parent) + 1)
            else:
                self.depth_map.setdefault(d.name, 0)

    def get_teams(self):
        self.depth_map = frappe._dict()

        self.group_entries = frappe.db.sql(
            """ select * from (
                select "Order Types" as name, 0 as lft, 2 as rgt, '' as parent
                union
                select distinct order_type as name, 1 as lft, 1 as rgt, "Order Types" as parent
                from `tab{doctype}` where ifnull(order_type, '') != ''
            ) as b order by lft, name
            """.format(doctype=self.filters.doc_type),
            as_dict=1,
        )

        for d in self.group_entries:
            if d.parent:
                self.depth_map.setdefault(d.name, self.depth_map.get(d.parent) + 1)
            else:
                self.depth_map.setdefault(d.name, 0)

    def get_supplier_parent_child_map(self):
        self.parent_child_map = frappe._dict(
            frappe.db.sql(""" select name, supplier_group from `tabSupplier`""")
        )

    # ----------------------------- Chart -------------------------------------

    def get_chart_data(self):
        length = len(self.columns)

        # Labels des colonnes (sans la/les colonnes d'identité & Total)
        if self.filters.tree_type in ["Customer", "Supplier"]:
            col_slice = self.columns[2 : length - 1]
        elif self.filters.tree_type == "Item":
            col_slice = self.columns[3 : length - 1]
        else:
            col_slice = self.columns[1 : length - 1]

        labels = [d.get("label") for d in col_slice]
        self.chart = {"data": {"labels": labels, "datasets": []}, "type": "line"}

        if self.filters["value_quantity"] == "Value":
            self.chart["fieldtype"] = "Currency"
        else:
            self.chart["fieldtype"] = "Float"

    # ----------------------------- Misc SQL util -----------------------------

    def get_additional_filters_sql(self):
        filters = []
        if self.filters.get("secteur"):
            filters.append("so.secteur_vt = '{}'".format(self.filters.secteur))
        if self.filters.get("cost_center"):
            filters.append("so.cost_center = '{}'".format(self.filters.cost_center))
        if self.filters.get("custom_responsable_du_devis"):
            filters.append("so.custom_responsable_du_devis = '{}'".format(self.filters.custom_responsable_du_devis))
        if self.filters.get("insurance"):
            filters.append("so.custom_insurance_client = '{}'".format(self.filters.insurance))
        return " AND " + " AND ".join(filters) if filters else ""

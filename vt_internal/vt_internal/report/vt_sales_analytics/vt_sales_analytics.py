# Copyright (c) 2013, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

import frappe
from frappe import _, scrub
from frappe.utils import add_days, add_to_date, flt, getdate
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
        if self.filters.get("tree_type") == "Secteur VT":
            self.filters.tree_type = "Secteur VT"
        self.get_period_date_ranges()

    def run(self):
        self.get_columns()
        self.get_data()
        self.get_chart_data()
        skip_total_row = 0
        if self.filters.tree_type in ["Supplier Group", "Item Group", "Customer Group", "Territory"]:
            skip_total_row = 1
        return self.columns, self.data, None, self.chart, None, skip_total_row

    def get_columns(self):
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
                    "label": _(self.filters.tree_type + " Name"),
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
        for end_date in self.periodic_daterange:
            period = self.get_period(end_date)
            self.columns.append(
                {"label": _(period), "fieldname": scrub(period), "fieldtype": "Float", "width": 120}
            )
        self.columns.append(
            {"label": _("Total"), "fieldname": "total", "fieldtype": "Float", "width": 120}
        )

    def get_data(self):
        if self.filters.tree_type == "Par verre":
            self.get_sales_transactions_based_on_glass()
            self.get_rows()
        elif self.filters.tree_type == "Secteur VT":
            self.get_sales_transactions_based_on_secteur()
            self.get_rows_by_group()
        elif self.filters.tree_type in ["Customer", "Supplier"]:
            self.get_sales_transactions_based_on_customers_or_suppliers()
            self.get_rows()
        elif self.filters.tree_type == "Item":
            self.get_sales_transactions_based_on_items()
            self.get_rows()
        elif self.filters.tree_type in ["Customer Group", "Supplier Group", "Territory"]:
            self.get_sales_transactions_based_on_customer_or_territory_group()
            self.get_rows_by_group()
        elif self.filters.tree_type == "Item Group":
            self.get_sales_transactions_based_on_item_group()
            self.get_rows_by_group()
        elif self.filters.tree_type == "Order Type":
            self.get_sales_transactions_based_on_order_type()
            self.get_rows_by_group()
        elif self.filters.tree_type == "Origine":
            self.get_sales_transactions_based_on_origine()
            self.get_rows()
        elif self.filters.tree_type == "Assurance":
            self.get_sales_transactions_based_on_assurance()
            self.get_rows()
        elif self.filters.tree_type == "Project":
            self.get_sales_transactions_based_on_project()
            self.get_rows()
        elif self.filters.tree_type == "Responsable du devis":
            self.get_sales_transactions_based_on_responsable()
            self.get_rows()

    def get_sales_transactions_based_on_secteur(self):
        if self.filters["value_quantity"] == "Value":
            value_field = "base_net_total as value_field"
        else:
            value_field = "total_qty as value_field"

        entity_field = "secteur_vt as entity"

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

        self.entries = frappe.get_all(
            self.filters.doc_type,
            fields=[entity_field, value_field, self.date_field],
            filters=filters,
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

    def get_sales_transactions_based_on_order_type(self):
        if self.filters["value_quantity"] == "Value":
            value_field = "base_net_total"
        else:
            value_field = "total_qty"

        secteur_filter = ""
        cost_center_filter = ""
        insurance_filter = ""
        responsable_filter = ""
        params = [self.filters.company, self.filters.from_date, self.filters.to_date]
        if self.filters.get("secteur"):
            secteur_filter = " and s.secteur_vt = %s"
            params.append(self.filters.secteur)
        if self.filters.get("cost_center"):
            cost_center_filter = " and s.cost_center = %s"
            params.append(self.filters.cost_center)
        if self.filters.get("insurance"):
            insurance_filter = " and s.custom_insurance_client = %s"
            params.append(self.filters.insurance)
        if self.filters.get("custom_responsable_du_devis"):
            responsable_filter = " and s.custom_responsable_du_devis = %s"
            params.append(self.filters.custom_responsable_du_devis)

        self.entries = frappe.db.sql(
            """ select s.order_type as entity, s.{value_field} as value_field, s.{date_field}
            from `tabSales Order` s where s.docstatus = 1 and s.company = %s and s.{date_field} between %s and %s
            and ifnull(s.order_type, '') != ''{secteur_filter}{cost_center_filter}{insurance_filter}{responsable_filter} order by s.order_type
        """.format(
                date_field=self.date_field, value_field=value_field, secteur_filter=secteur_filter, cost_center_filter=cost_center_filter, insurance_filter=insurance_filter, responsable_filter=responsable_filter
            ),
            tuple(params),
            as_dict=1,
        )

        self.get_teams()

    def get_sales_transactions_based_on_origine(self):
        if self.filters["value_quantity"] == "Value":
            value_field = "SUM(i.base_net_amount)"
        else:
            value_field = "COUNT(DISTINCT s.name)"

        secteur_filter = ""
        cost_center_filter = ""
        insurance_filter = ""
        responsable_filter = ""
        params = [self.filters.company, self.filters.from_date, self.filters.to_date]
        if self.filters.get("secteur"):
            secteur_filter = " and s.secteur_vt = %s"
            params.append(self.filters.secteur)
        if self.filters.get("cost_center"):
            cost_center_filter = " and s.cost_center = %s"
            params.append(self.filters.cost_center)
        if self.filters.get("insurance"):
            insurance_filter = " and s.custom_insurance_client = %s"
            params.append(self.filters.insurance)
        if self.filters.get("custom_responsable_du_devis"):
            responsable_filter = " and s.custom_responsable_du_devis = %s"
            params.append(self.filters.custom_responsable_du_devis)

        self.entries = frappe.db.sql(
            """
            select 
                case when i.prevdoc_docname is not null then 'Devis' else 'Commande' end as entity,
                {value_field} as value_field, 
                s.{date_field}
            from `tabSales Order Item` i , `tabSales Order` s
            where s.name = i.parent and s.docstatus = 1 and s.company = %s
            and s.{date_field} between %s and %s{secteur_filter}{cost_center_filter}{insurance_filter}{responsable_filter}
            group by entity, s.{date_field}
        """.format(
                date_field=self.date_field, value_field=value_field, secteur_filter=secteur_filter, cost_center_filter=cost_center_filter, insurance_filter=insurance_filter, responsable_filter=responsable_filter
            ),
            tuple(params),
            as_dict=1,
        )

    def get_sales_transactions_based_on_assurance(self):
        if self.filters["value_quantity"] == "Value":
            value_field = "SUM(s.base_net_total)"
        else:
            value_field = "COUNT(DISTINCT s.name)"

        secteur_filter = ""
        cost_center_filter = ""
        insurance_filter = ""
        responsable_filter = ""
        params = [self.filters.company, self.filters.from_date, self.filters.to_date]
        if self.filters.get("secteur"):
            secteur_filter = " and s.secteur_vt = %s"
            params.append(self.filters.secteur)
        if self.filters.get("cost_center"):
            cost_center_filter = " and s.cost_center = %s"
            params.append(self.filters.cost_center)
        if self.filters.get("insurance"):
            insurance_filter = " and s.custom_insurance_client = %s"
            params.append(self.filters.insurance)
        if self.filters.get("custom_responsable_du_devis"):
            responsable_filter = " and s.custom_responsable_du_devis = %s"
            params.append(self.filters.custom_responsable_du_devis)

        self.entries = frappe.db.sql(
            """ select s.custom_insurance_client as entity, {value_field} as value_field, s.{date_field}
            from `tabSales Order` s where s.docstatus = 1 and s.company = %s and s.{date_field} between %s and %s
            {secteur_filter}{cost_center_filter}{insurance_filter}{responsable_filter}
            group by entity, s.{date_field}
        """.format(
                date_field=self.date_field, value_field=value_field, secteur_filter=secteur_filter, cost_center_filter=cost_center_filter, insurance_filter=insurance_filter, responsable_filter=responsable_filter
            ),
            tuple(params),
            as_dict=1,
        )

    def get_sales_transactions_based_on_customers_or_suppliers(self):
        if self.filters["value_quantity"] == "Value":
            value_field = "base_net_total as value_field"
        else:
            value_field = "total_qty as value_field"

        if self.filters.tree_type == "Customer":
            entity = "customer as entity"
            entity_name = "customer_name as entity_name"
        else:
            entity = "supplier as entity"
            entity_name = "supplier_name as entity_name"

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

        self.entries = frappe.get_all(
            "Sales Order",
            fields=[entity, entity_name, value_field, self.date_field],
            filters=filters,
        )

        self.entity_names = {}
        for d in self.entries:
            self.entity_names.setdefault(d.entity, d.entity_name)

    def get_sales_transactions_based_on_items(self):
        if self.filters["value_quantity"] == "Value":
            value_field = "base_net_amount"
        else:
            value_field = "stock_qty"

        secteur_filter = ""
        cost_center_filter = ""
        insurance_filter = ""
        responsable_filter = ""
        params = [self.filters.company, self.filters.from_date, self.filters.to_date]
        if self.filters.get("secteur"):
            secteur_filter = " and s.secteur_vt = %s"
            params.append(self.filters.secteur)
        if self.filters.get("cost_center"):
            cost_center_filter = " and s.cost_center = %s"
            params.append(self.filters.cost_center)
        if self.filters.get("insurance"):
            insurance_filter = " and s.custom_insurance_client = %s"
            params.append(self.filters.insurance)
        if self.filters.get("custom_responsable_du_devis"):
            responsable_filter = " and s.custom_responsable_du_devis = %s"
            params.append(self.filters.custom_responsable_du_devis)

        self.entries = frappe.db.sql(
            """
            select i.item_code as entity, i.item_name as entity_name, i.stock_uom, i.{value_field} as value_field, s.{date_field}
            from `tabSales Order Item` i , `tabSales Order` s
            where s.name = i.parent and i.docstatus = 1 and s.company = %s
            and s.{date_field} between %s and %s{secteur_filter}{cost_center_filter}{insurance_filter}{responsable_filter}
        """.format(
                date_field=self.date_field, value_field=value_field, secteur_filter=secteur_filter, cost_center_filter=cost_center_filter, insurance_filter=insurance_filter, responsable_filter=responsable_filter
            ),
            tuple(params),
            as_dict=1,
        )

        self.entity_names = {}
        for d in self.entries:
            self.entity_names.setdefault(d.entity, d.entity_name)

    def get_sales_transactions_based_on_customer_or_territory_group(self):
        if self.filters["value_quantity"] == "Value":
            value_field = "base_net_total as value_field"
        else:
            value_field = "total_qty as value_field"

        if self.filters.tree_type == "Customer Group":
            entity_field = "customer_group as entity"
        elif self.filters.tree_type == "Supplier Group":
            entity_field = "supplier as entity"
            self.get_supplier_parent_child_map()
        else:
            entity_field = "territory as entity"

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

        self.entries = frappe.get_all(
            "Sales Order",
            fields=[entity_field, value_field, self.date_field],
            filters=filters,
        )
        self.get_groups()

    def get_sales_transactions_based_on_item_group(self):
        if self.filters["value_quantity"] == "Value":
            value_field = "base_net_amount"
        else:
            value_field = "qty"

        secteur_filter = ""
        cost_center_filter = ""
        insurance_filter = ""
        responsable_filter = ""
        params = [self.filters.company, self.filters.from_date, self.filters.to_date]
        if self.filters.get("secteur"):
            secteur_filter = " and s.secteur_vt = %s"
            params.append(self.filters.secteur)
        if self.filters.get("cost_center"):
            cost_center_filter = " and s.cost_center = %s"
            params.append(self.filters.cost_center)
        if self.filters.get("insurance"):
            insurance_filter = " and s.custom_insurance_client = %s"
            params.append(self.filters.insurance)
        if self.filters.get("custom_responsable_du_devis"):
            responsable_filter = " and s.custom_responsable_du_devis = %s"
            params.append(self.filters.custom_responsable_du_devis)

        self.entries = frappe.db.sql(
            """
            select i.item_group as entity, i.{value_field} as value_field, s.{date_field}
            from `tabSales Order Item` i , `tabSales Order` s
            where s.name = i.parent and i.docstatus = 1 and s.company = %s
            and s.{date_field} between %s and %s{secteur_filter}{cost_center_filter}{insurance_filter}{responsable_filter}
        """.format(
                date_field=self.date_field, value_field=value_field, secteur_filter=secteur_filter, cost_center_filter=cost_center_filter, insurance_filter=insurance_filter, responsable_filter=responsable_filter
            ),
            tuple(params),
            as_dict=1,
        )

        self.get_groups()

    def get_sales_transactions_based_on_project(self):
        if self.filters["value_quantity"] == "Value":
            value_field = "base_net_total as value_field"
        else:
            value_field = "total_qty as value_field"

        entity = "project as entity"

        filters = {
            "docstatus": 1,
            "company": self.filters.company,
            "project": ["!=", ""],
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

        self.entries = frappe.get_all(
            "Sales Order",
            fields=[entity, value_field, self.date_field],
            filters=filters,
        )

    def get_sales_transactions_based_on_responsable(self):
        if self.filters["value_quantity"] == "Value":
            value_field = "base_net_total as value_field"
        else:
            value_field = "total_qty as value_field"

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

        self.entries = frappe.get_all(
            "Sales Order",
            fields=["custom_responsable_du_devis as entity", value_field, self.date_field],
            filters=filters,
        )

    def get_rows(self):
        self.data = []
        self.get_periodic_data()

        for entity, period_data in self.entity_periodic_data.items():
            row = {
                "entity": entity,
                "entity_name": self.entity_names.get(entity) if hasattr(self, "entity_names") else None,
            }
            total = 0
            for end_date in self.periodic_daterange:
                period = self.get_period(end_date)
                amount = flt(period_data.get(period, 0.0))
                row[scrub(period)] = amount
                total += amount

            row["total"] = total

            if self.filters.tree_type == "Item":
                row["stock_uom"] = period_data.get("stock_uom")

            self.data.append(row)

    def get_rows_by_group(self):
        self.get_periodic_data()
        out = []

        for d in reversed(self.group_entries):
            row = {"entity": d.name, "indent": self.depth_map.get(d.name)}
            total = 0
            for end_date in self.periodic_daterange:
                period = self.get_period(end_date)
                amount = flt(self.entity_periodic_data.get(d.name, {}).get(period, 0.0))
                row[scrub(period)] = amount
                if d.parent and (self.filters.tree_type != "Order Type" or d.parent == "Order Types"):
                    self.entity_periodic_data.setdefault(d.parent, frappe._dict()).setdefault(period, 0.0)
                    self.entity_periodic_data[d.parent][period] += amount
                total += amount

            row["total"] = total
            out = [row] + out

        self.data = out

    def get_periodic_data(self):
        self.entity_periodic_data = frappe._dict()

        for d in self.entries:
            if self.filters.tree_type == "Supplier Group":
                d.entity = self.parent_child_map.get(d.entity)
            period = self.get_period(d.get(self.date_field))
            self.entity_periodic_data.setdefault(d.entity, frappe._dict()).setdefault(period, 0.0)
            self.entity_periodic_data[d.entity][period] += flt(d.value_field)

            if self.filters.tree_type == "Item":
                self.entity_periodic_data[d.entity]["stock_uom"] = d.stock_uom

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
            """ select * from (select "Order Types" as name, 0 as lft,
            2 as rgt, '' as parent union select distinct order_type as name, 1 as lft, 1 as rgt, "Order Types" as parent
            from `tab{doctype}` where ifnull(order_type, '') != '') as b order by lft, name
        """.format(
                doctype=self.filters.doc_type
            ),
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

    def get_chart_data(self):
        length = len(self.columns)

        if self.filters.tree_type in ["Customer", "Supplier"]:
            labels = [d.get("label") for d in self.columns[2 : length - 1]]
        elif self.filters.tree_type == "Item":
            labels = [d.get("label") for d in self.columns[3 : length - 1]]
        else:
            labels = [d.get("label") for d in self.columns[1 : length - 1]]
        self.chart = {"data": {"labels": labels, "datasets": []}, "type": "line"}

        if self.filters["value_quantity"] == "Value":
            self.chart["fieldtype"] = "Currency"
        else:
            self.chart["fieldtype"] = "Float"

    def get_sales_transactions_based_on_glass(self):
        if self.filters["value_quantity"] == "Value":
            value_field = "SUM(soi.base_net_amount) AS value_field"
        else:
            value_field = "SUM((bom.hauteur / 1000) * (bom.largeur / 1000)) AS value_field"

        secteur_filter = ""
        cost_center_filter = ""
        insurance_filter = ""
        responsable_filter = ""
        params = [self.filters.company, self.filters.from_date, self.filters.to_date]
        if self.filters.get("secteur"):
            secteur_filter = " and so.secteur_vt = %s"
            params.append(self.filters.secteur)
        if self.filters.get("cost_center"):
            cost_center_filter = " and so.cost_center = %s"
            params.append(self.filters.cost_center)
        if self.filters.get("insurance"):
            insurance_filter = " and so.custom_insurance_client = %s"
            params.append(self.filters.insurance)
        if self.filters.get("custom_responsable_du_devis"):
            responsable_filter = " and so.custom_responsable_du_devis = %s"
            params.append(self.filters.custom_responsable_du_devis)

        self.entries = frappe.db.sql(
            """
            SELECT
                (
                    SELECT bi.item_code
                    FROM `tabBOM Item` bi
                    WHERE bi.parent = bom.name
                    ORDER BY bi.idx ASC
                    LIMIT 1
                ) AS entity,
                {value_field},
                so.{date_field}
            FROM `tabSales Order Item` soi
            JOIN `tabSales Order` so ON soi.parent = so.name
            JOIN `tabBOM` bom ON soi.bom_no = bom.name
            WHERE so.docstatus = 1
            AND soi.item_code IN ('Produit fini (double vitrage)', 'Produit fini (verre)')
            AND so.company = %s
            AND so.{date_field} BETWEEN %s AND %s
            {secteur_filter}{cost_center_filter}{insurance_filter}{responsable_filter}
            GROUP BY entity, so.{date_field}
            """.format(
                value_field=value_field,
                date_field=self.date_field,
                secteur_filter=secteur_filter,
                cost_center_filter=cost_center_filter,
                insurance_filter=insurance_filter,
                responsable_filter=responsable_filter
            ),
            tuple(params),
            as_dict=1,
        )

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
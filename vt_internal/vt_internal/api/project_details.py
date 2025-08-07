import frappe
from frappe import _

@frappe.whitelist(allow_guest=True)
def project_details():
    # Logique pour créer un client
    def get_theoretical(project_id, axis):
        condition = ""
        if axis == "Temps passé":
            condition = "AND i.custom_pose_vt = 1"
        elif axis == "Achats":
            condition = "AND (i.custom_pose_vt = 0 OR i.custom_pose_vt IS NULL)"
        # For "global", condition remains empty

        # Query for non-bundle items
        sql_non_bundle = """
            SELECT SUM(soi.amount) AS vente, SUM(soi.qty * COALESCE(soi.base_unit_cost_price, 0)) AS cost
            FROM `tabSales Order Item` soi
            INNER JOIN `tabSales Order` so ON so.name = soi.parent
            INNER JOIN `tabItem` i ON i.name = soi.item_code
            WHERE so.project = %s AND so.docstatus = 1 {condition}
            AND product_bundle_name IS NOT NULL
        """.format(condition=condition)
        result_non_bundle = frappe.db.sql(sql_non_bundle, project_id, as_dict=1)[0]
        vente_non_bundle = result_non_bundle.vente or 0
        cost_non_bundle = result_non_bundle.cost or 0

        # Query for packed items (components of bundles)
        sql_packed = """
            SELECT SUM(pi.qty * pi.rate) AS vente, SUM(pi.qty * COALESCE(pi.base_unit_cost_price, 0)) AS cost
            FROM `tabPacked Item` pi
            INNER JOIN `tabSales Order` so ON so.name = pi.parent
            INNER JOIN `tabItem` i ON i.name = pi.item_code
            WHERE so.project = %s AND so.docstatus = 1 {condition}
        """.format(condition=condition)
        result_packed = frappe.db.sql(sql_packed, project_id, as_dict=1)[0]
        vente_packed = result_packed.vente or 0
        cost_packed = result_packed.cost or 0

        vente = vente_non_bundle + vente_packed
        cost = cost_non_bundle + cost_packed
        return vente, cost

    def get_expenses(project_id):
        es = frappe.db.get_list('Expense',
            filters={'project': project_id, 'docstatus': ['!=', 2]},
            fields=["name", "custom_état", "net_amount", "expense_date"]
        )
        return [{
            "doctype": "<span class='badge badge-danger'>Dépense</span>",
            "name": f"<a href={frappe.utils.get_url_to_form('Expense', i.name)}>{i.name}</a>",
            "status": i.custom_état,
            "description": frappe.utils.fmt_money(i.net_amount, currency='EUR'),
            "date": i.expense_date,
        } for i in es]

    def get_payment_entries(project_id):
        pe = frappe.db.get_list('Payment Entry',
            filters={'project': project_id, 'docstatus': ['!=', 2]},
            fields=["name", "status", "paid_amount", "reference_date", "mode_of_payment", "payment_type"]
        )
        return [{
            "doctype": "<span class='badge badge-warning'>Ecriture de paiement</span>",
            "name": f"<a href={frappe.utils.get_url_to_form('Payment Entry', i.name)}>{i.name}</a>",
            "status": i.status,
            "description": frappe.utils.fmt_money(i.paid_amount, currency='EUR') + (i.mode_of_payment or "") + " " + _(i.payment_type, context='Payment Entry'),
            "date": i.reference_date,
        } for i in pe]

    def get_purchase_orders(project_id):
        pos = frappe.db.get_list('Purchase Order',
            filters=[['docstatus', '!=', 2], ["Purchase Order Item", "project", "=", project_id]],
            group_by="name",
            fields=["name", "status", "transaction_date", "supplier", "sum(`tabPurchase Order Item`.amount) as total"]
        )
        total_purchase_order = sum(i.total for i in pos)
        items = [{
            "doctype": "<span class='badge badge-secondary'>Commande fournisseur</span>",
            "name": f"<a href={frappe.utils.get_url_to_form('Purchase Order', i.name)}>{i.name}</a>",
            "status": i.status,
            "description": frappe.utils.fmt_money(i.total, currency='EUR') + i.supplier,
            "date": i.transaction_date,
        } for i in pos]
        return items, total_purchase_order

    def get_visite_techniques(project_id):
        vts = frappe.db.get_list('Visite Technique',
            filters={'projet': project_id, 'docstatus': ['!=', 2]},
            fields=["name", "status", "creation", "plans", "photo_5", "photo_2", "photo_3", "photo_4"]
        )
        return [{
            "doctype": "<span class='badge badge-secondary'>Visite technique</span>",
            "name": f"<a href={frappe.utils.get_url_to_form('Visite Technique', i.name)}>{i.name}</a>",
            "status": i.status,
            "description": f"{sum(1 for p in [i.plans, i.photo_2, i.photo_3, i.photo_4, i.photo_5] if p)} photos",
            "date": i.creation,
        } for i in vts]

    def get_fiches_travail(project_id):
        ft = frappe.db.get_list('Fiche de travail',
            filters={'projet': project_id, 'docstatus': ['!=', 2]},
            fields=["name", "status", "creation", "time_spent", "labor_costs"]
        )
        return [{
            "doctype": "<span class='badge badge-secondary' style='background-color: #52159e'>Fiche de travail</span>",
            "name": f"<a href={frappe.utils.get_url_to_form('Fiche de travail', i.name)}>{i.name}</a>",
            "status": i.status,
            "description": "",
            "date": i.creation,
        } for i in ft]

    def get_timesheets(project_id):
        tss = frappe.db.get_all('Timesheet',
            filters=[['docstatus', '!=', 2], ["Timesheet Detail", "project", "=", project_id]],
            group_by="project",
            fields=["name", "sum(`tabTimesheet Detail`.costing_amount) as costing_amount", "sum(`tabTimesheet Detail`.hours) as hours"]
        )
        time_spent = round(sum(t.hours for t in tss), 2) or 0
        return time_spent

    def get_fabrications(project_id):
        fab = frappe.db.get_list('Fabrication VT',
            filters={'project': project_id, 'docstatus': ['!=', 2]},
            fields=["name", "status", "creation", "article", "manufacturing_costs", "quantity"]
        )
        total_manufacturing_cost = sum(i.manufacturing_costs for i in fab)
        items = [{
            "doctype": "<span class='badge badge-secondary'>Fabrication</span>",
            "name": f"<a href={frappe.utils.get_url_to_form('Fabrication VT', i.name)}>{i.quantity} x {i.article}</a>",
            "status": i.status,
            "description": frappe.utils.fmt_money(i.manufacturing_costs, currency='EUR'),
            "date": i.creation,
        } for i in fab]
        return items, total_manufacturing_cost

    def get_purchase_invoices(project_id):
        pis = frappe.db.get_list('Purchase Invoice',
            filters={'docstatus': ['!=', 2]},
            or_filters=[["Purchase Invoice Item", "project", "=", project_id], ["project", "=", project_id]],
            group_by="name",
            fields=["name", "status", "posting_date", "supplier", "sum(`tabPurchase Invoice Item`.amount) as total", 'custom_mode_of_paiement']
        )
        return [{
            "doctype": "<span class='badge badge-danger'>Facture d'achat</span>",
            "name": f"<a href={frappe.utils.get_url_to_form('Purchase Invoice', i.name)}>{i.name}</a>",
            "status": i.status,
            "description": frappe.utils.fmt_money(i.total, currency='EUR') + (i.custom_mode_of_paiement or ""),
            "date": i.posting_date,
        } for i in pis]

    def get_sales_invoices(project_id):
        sis = frappe.db.get_list('Sales Invoice',
            filters={'project': project_id, 'docstatus': ['!=', 2]},
            fields=["name", "status", "total", "posting_date", "is_down_payment_invoice", "grand_total"]
        )
        return [{
            "doctype": "<span class='badge badge-success'>Facture d'acompte</span>" if i.is_down_payment_invoice else "<span class='badge badge-success'>Facture de vente</span>",
            "name": f"<a href={frappe.utils.get_url_to_form('Sales Invoice', i.name)}>{i.name}</a>",
            "status": i.status,
            "description": frappe.utils.fmt_money(i.grand_total if i.is_down_payment_invoice else i.total, currency='EUR'),
            "date": i.posting_date,
        } for i in sis]

    def get_quality_incidents(project_id):
        iqs = frappe.db.get_list('Quality Incident',
            filters={'project': project_id},
            fields=["name", "origine", "total_costs", 'object', 'status', 'date']
        )
        return [{
            "doctype": "<span class='badge badge-dark'>Incident Qualité</span>",
            "name": f"<a href={frappe.utils.get_url_to_form('Quality Incident', i.name)}>{i.object}</a>",
            "status": i.status,
            "description": (i.origine or "") + " " + frappe.utils.fmt_money(i.total_costs, currency='EUR'),
            "date": i.date,
        } for i in iqs]

    def get_work_completion_receipts(project_id):
        rts = frappe.db.get_list('Work Completion Receipt',
            filters={'project': project_id, 'docstatus': ["!=", 2]},
            fields=["name", "docstatus", 'le']
        )
        return [{
            "doctype": "<span class='badge badge-success' style='background-color: #0f0bcf'>Réception de travaux</span>",
            "name": f"<a href={frappe.utils.get_url_to_form('Work Completion Receipt', i.name)}>{i.name}</a>",
            "status": "Non signé" if i.docstatus == 0 else "Signé",
            "description": "",
            "date": i.le,
        } for i in rts]

    def get_supplier_quotations(project_id):
        qss = frappe.db.get_list('Supplier Quotation',
            filters={'project': project_id, 'docstatus': ['!=', 2]},
            fields=["name", "status", "total", "transaction_date", "supplier_name"]
        )
        return [{
            "doctype": "<span class='badge badge-info' style='background-color: #6fc5e8;'>Devis fournisseur</span>",
            "name": f"<a href={frappe.utils.get_url_to_form('Supplier Quotation', i.name)}>{i.name}</a>",
            "status": i.status,
            "description": frappe.utils.fmt_money(i.total, currency='EUR') + " " + i.supplier_name,
            "date": i.transaction_date,
        } for i in qss]

    def get_quotations(project_id):
        qs = frappe.db.get_list('Quotation',
            filters={'project': project_id, 'docstatus': ['!=', 2]},
            fields=["name", "status", "total", "transaction_date"]
        )
        return [{
            "doctype": "<span class='badge badge-info'>Devis</span>",
            "name": f"<a href={frappe.utils.get_url_to_form('Quotation', i.name)}>{i.name}</a>",
            "status": i.status,
            "description": frappe.utils.fmt_money(i.total, currency='EUR'),
            "date": i.transaction_date,
        } for i in qs]

    def get_delivery_notes(project_id):
        dns = frappe.db.get_list('Delivery Note',
            filters={'project': project_id, 'docstatus': ['!=', 2]},
            fields=["name", "status", "posting_date", "custom_livré"]
        )
        return [{
            "doctype": "<span class='badge badge-info'>Bon de livraison</span>",
            "name": f"<a href={frappe.utils.get_url_to_form('Delivery Note', i.name)}>{i.name}</a>",
            "status": i.status,
            "description": "Livré" if i.custom_livré else "",
            "date": i.posting_date
        } for i in dns]

    def get_sales_orders(project_id):
        sos = frappe.db.get_list('Sales Order',
            filters={'project': project_id, 'docstatus': ['!=', 2]},
            fields=["name", "status", "grand_total", "total", "transaction_date", "markup_percentage", "custom_labour_hours"]
        )
        items = [{
            "doctype": "<span class='badge badge-info'>Commande client</span>",
            "name": f"<a href={frappe.utils.get_url_to_form('Sales Order', i.name)}>{i.name}</a>",
            "status": i.status,
            "description": frappe.utils.fmt_money(i.total, currency='EUR'),
            "date": i.transaction_date
        } for i in sos]
        return items, sos

    def get_sales_invoices_for_payments(project_id):
        si = frappe.db.get_list('Sales Invoice',
            filters=[['docstatus', '=', 1], ["project", "=", project_id]],
            group_by="is_down_payment_invoice",
            fields=["status", "sum(grand_total) as grand_total", "is_down_payment_invoice", "sum(outstanding_amount) as outstanding_amount"]
        )
        return si

    project_id = frappe.form_dict.get("project")
    project = frappe.get_doc("Project", project_id)
    theo_vente_global, theo_cost_global = get_theoretical(project_id, "global")
    theo_vente_tp, theo_cost_tp = get_theoretical(project_id, "Temps passé")
    theo_vente_ach, theo_cost_ach = get_theoretical(project_id, "Achats")
    theoretical_margin = int((theo_vente_global - theo_cost_global) / theo_vente_global * 100 if theo_vente_global else 0)
    theo_margin_ach = int((theo_vente_ach - theo_cost_ach) / theo_vente_ach * 100 if theo_vente_ach else 0)
    items = []
    items.extend(get_expenses(project_id))
    items.extend(get_payment_entries(project_id))
    po_items, total_purchase_order = get_purchase_orders(project_id)
    items.extend(po_items)
    items.extend(get_visite_techniques(project_id))
    items.extend(get_fiches_travail(project_id))
    time_spent = get_timesheets(project_id)
    fab_items, total_manufacturing_cost = get_fabrications(project_id)
    items.extend(fab_items)
    items.extend(get_purchase_invoices(project_id))
    items.extend(get_sales_invoices(project_id))
    items.extend(get_quality_incidents(project_id))
    items.extend(get_work_completion_receipts(project_id))
    items.extend(get_supplier_quotations(project_id))
    items.extend(get_quotations(project_id))
    items.extend(get_delivery_notes(project_id))
    so_items, sales_orders = get_sales_orders(project_id)
    items.extend(so_items)
    grand_total_sold_ttc = max(1, sum(s.grand_total for s in sales_orders))
    sales_invoices_payments = get_sales_invoices_for_payments(project_id)
    per_down_payment_paid = round(sum((s.grand_total - s.outstanding_amount if s.is_down_payment_invoice else 0 for s in sales_invoices_payments)) / grand_total_sold_ttc * 100)
    per_down_payment_unpaid = round(sum((s.outstanding_amount if s.is_down_payment_invoice else 0 for s in sales_invoices_payments)) / grand_total_sold_ttc * 100)
    per_billed_paid = round(sum((s.grand_total - s.outstanding_amount) if not s.is_down_payment_invoice else 0 for s in sales_invoices_payments)/grand_total_sold_ttc*100)
    per_billed_unpaid = round(sum([s.outstanding_amount if not s.is_down_payment_invoice else 0 for s in sales_invoices_payments])/grand_total_sold_ttc*100)
    labour_hours = sum(i.custom_labour_hours or 0 for i in sales_orders) or 0
    items = sorted(items, key=lambda k: frappe.utils.getdate(k['date']) if k['date'] else frappe.utils.getdate('1900-01-01'))
    total_purchases = total_purchase_order + project.total_expense_claim
    total_expenses = total_purchases + project.total_costing_amount + total_manufacturing_cost
    real_cost_ach = total_purchases + total_manufacturing_cost
    real_margin_ach = int((theo_vente_ach - real_cost_ach) / theo_vente_ach * 100 if theo_vente_ach else 0)
    vente = theo_vente_global or project.total_sales_amount
    real_margin = int((vente - total_expenses) / vente * 100 if vente else 0)
    real_margin_color = "success" if real_margin >= theoretical_margin else "warning" if real_margin > (theoretical_margin - 7) else "danger"
    ach_margin_color = "success" if real_margin_ach >= theo_margin_ach else "warning" if real_margin_ach > (theo_margin_ach - 7) else "danger"
    time_spent_color = "success" if time_spent <= labour_hours else "warning" if time_spent < labour_hours * 1.1 else "danger"
    diff_global = real_margin - theoretical_margin
    diff_ach = real_margin_ach - theo_margin_ach
    diff_time = time_spent - labour_hours
    has_pose_vt = labour_hours > 0 or time_spent > 0
    marges_table = f"""
        <table class="table mb-0">
            <thead>
                <tr>
                    <th></th>
                    <th>Théorique</th>
                    <th>Réel</th>
                    <th>Différence</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>Marge globale</td>
                    <td>{theoretical_margin} %</td>
                    <td>{real_margin} %</td>
                    <td class="text-{real_margin_color}"><b>{diff_global} pp</b></td>
                </tr>
        """
    if has_pose_vt:
        marges_table += f"""
                <tr>
                    <td>Temps passé</td>
                    <td>{labour_hours} h</td>
                    <td>{time_spent} h</td>
                    <td class="text-{time_spent_color}"><b>{diff_time} h</b></td>
                </tr>
                <tr>
                    <td>Marge sur achats</td>
                    <td>{theo_margin_ach} %</td>
                    <td>{real_margin_ach} %</td>
                    <td class="text-{ach_margin_color}"><b>{diff_ach} pp</b></td>
                </tr>
            """
    marges_table += """
            </tbody>
        </table>
        """
    mo_html = ""
    if project.total_costing_amount > 0:
        mo_html = f"""
          <p style="margin: 0; color: black; font-size: 16px; margin-top:30px; font-weight: bolder;">-</p>
          <div style="text-align: center;">
            <p style="margin: 0; color: gray; font-size: 16px;">Total MO</p>
            <p style="color: red; font-size: 24px; margin: 5px 0;">{frappe.utils.fmt_money(project.total_costing_amount, currency='EUR')}</p>
          </div>"""
    manufacturing_html = ""
    if total_manufacturing_cost > 0:
        manufacturing_html = f"""
          <p style="margin: 0; color: black; font-size: 16px; margin-top:30px; font-weight: bolder;">-</p>
          <div style="text-align: center;">
            <p style="margin: 0; color: gray; font-size: 16px;">Total fabrication</p>
            <p style="color: red; font-size: 24px; margin: 5px 0;">{frappe.utils.fmt_money(total_manufacturing_cost, currency='EUR')}</p>
          </div>"""
    purchase_html = ""
    if total_purchases > 0:
        purchase_html = f"""
          <p style="margin: 0; color: black; font-size: 16px; margin-top:30px; font-weight: bolder;">-</p>
          <div style="text-align: center;">
            <p style="margin: 0; color: gray; font-size: 16px;">Total des achats (HT)</p>
            <p style="color: red; font-size: 24px; margin: 5px 0;">{frappe.utils.fmt_money(total_purchases, currency='EUR')}</p>
          </div>"""
    temps_du_projet = frappe.utils.date_diff(items[-1]["date"], items[0]["date"]) if items else 0
    content_rows = [
        f"""<tr>
                <td>{i["doctype"]}</td>
                <td>{i["name"]}</td>
                <td>{i["description"]}</td>
                <td>{_(i["status"])}</td>
                <td>{frappe.utils.format_date(i["date"])}</td>
            </tr>""" for i in items
        ]
    content = "".join(content_rows)
    html = f"""<div>
        <div style="display: flex; flex-direction: row; justify-content: space-between;">
            <div style="width: 45%">
              <h4>Marges</h4>
    {marges_table}
            </div>
            <div style="width: 45%">
                <h4>Paiements</h4>
                Acompte:
                <div class="progress" style="height: 20px;">
                  <div class="progress-bar bg-success" role="progressbar" style="width: {per_down_payment_paid}%">{per_down_payment_paid}% Payé</div>
                  <div class="progress-bar bg-info" role="progressbar" style="width: {per_down_payment_unpaid}%">{per_down_payment_unpaid}% Non payé</div>
                </div>
                Facture finale:
                <div class="progress" style="height: 20px;">
                  <div class="progress-bar bg-success" role="progressbar" style="width: {per_billed_paid}%">{per_billed_paid}% Payé</div>
                  <div class="progress-bar bg-info" role="progressbar" style="width: {per_billed_unpaid}%">{per_billed_unpaid}% Non payé</div>
                </div>
            </div>
        </div>
        <div style="display: flex; justify-content: space-between; width: 100%; padding-top:20px; padding-bottom:20px; box-sizing: border-box;">
          <div style="text-align: center;">
            <p style="margin: 0; color: gray; font-size: 16px;">Total commandé (HT)</p>
            <p style="color: green; font-size: 24px; margin: 5px 0;">{frappe.utils.fmt_money(vente, currency='EUR')}</p>
          </div>
    {purchase_html}
    {manufacturing_html}
    {mo_html}
          <p style="margin: 0; color: black; font-size: 16px; margin-top:30px; font-weight: bolder;">=</p>
          <div style="text-align: center;">
            <p style="margin: 0; color: gray; font-size: 16px;">Bénéfice ({real_margin} % de marge)</p>
            <p style="color: blue; font-size: 24px; margin: 5px 0;">{frappe.utils.fmt_money(vente - total_expenses, currency='EUR')}</p>
          </div>
        </div>
        <table class="table">
            <thead>
                <tr>
                  <th scope="col">Type de document</th>
                  <th scope="col">Nom</th>
                  <th scope="col">Description</th>
                  <th scope="col">Statut</th>
                  <th scope="col">Date</th>
                </tr>
            </thead>
            <tbody>
    {content}
            </tbody>
        </table>
        <p style="color: black; font-size: 16px; font-weight: bolder;">Durée totale du projet: {temps_du_projet} jours</p>
        </div>"""
    frappe.response['message'] = {"html": html}
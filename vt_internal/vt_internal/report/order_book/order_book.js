// Copyright (c) 2025, Dokos SAS and contributors
// For license information, please see license.txt

// ...existing code...
frappe.query_reports["Order book"] = {
    filters: [
        // Explicit Cost Center filter
        {
            fieldname: "cost_center",
            label: __("Centre de coût"),
            fieldtype: "Link",
            options: "Cost Center"
        },
        {
            fieldname: "custom_construction_manager",
            label: __("Responsable de chantier"),
            fieldtype: "Link",
            options: "User"
        },
        // Standard filters (status and per_billed handled server-side)
        ...frappe.get_meta("Sales Order").fields
            .filter(df => df.in_standard_filter && df.fieldname !== "status" && df.fieldname !== "transaction_date")
            .map(df => ({
                fieldname: df.fieldname,
                label: __(df.label),
                fieldtype: df.fieldtype,
                options: df.options,
                default: df.default
            })),
    ],
    // Color the Age column: <30 green, <100 orange, else red
    // Color the Status column using Sales Order listview indicator
    formatter: function(value, row, column, data, default_formatter) {
        let html = default_formatter(value, row, column, data);
        if (column.fieldname === "age" && value != null) {
            let color = value < 30 ? "green" : value < 100 ? "orange" : "red";
            html = `<span style="color:${color}">${value}</span>`;
        }
        if (column.fieldname === "status" && data) {
            const get_indicator = frappe.listview_settings['Sales Order']?.get_indicator;
            if (get_indicator) {
                const indicator = get_indicator(data);
                if (indicator) {
                    const [label, color] = indicator;
                    html = `<span class="indicator-pill ${color}">${label}</span>`;
                }
            }
        }
        if (column.fieldname === "custom_construction_status" && data) {
            const display = value ? value.replace(/\n/g, '<br>') : '<em style="color:#888">Cliquer pour modifier</em>';
            html = `<div class="editable-construction-status" data-name="${data.name}" style="cursor:pointer; min-height:20px;">${display}</div>`;
        }
        return html;
    },
    onload: function(report) {
        report.$report.on('click', '.editable-construction-status', function() {
            const name = $(this).data('name');
            const current_value = $(this).text() === 'Cliquer pour modifier' ? '' : $(this).html().replace(/<br>/g, '\n');

            const d = new frappe.ui.Dialog({
                title: __('Modifier le statut construction'),
                fields: [
                    { fieldname: 'status', fieldtype: 'Small Text', label: __('Statut construction'), default: current_value }
                ],
                primary_action_label: __('Enregistrer'),
                primary_action(values) {
                    frappe.call({
                        method: 'frappe.client.set_value',
                        args: {
                            doctype: 'Sales Order',
                            name: name,
                            fieldname: 'custom_construction_status',
                            value: values.status
                        },
                        callback: () => {
                            frappe.show_alert({ message: __('Statut mis à jour'), indicator: 'green' });
                            report.refresh();
                        }
                    });
                    d.hide();
                }
            });
            d.show();
        });
    }
};
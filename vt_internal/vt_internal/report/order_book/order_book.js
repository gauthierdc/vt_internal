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
        return html;
    }
};
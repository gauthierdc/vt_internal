import frappe

def safe_delete(doctype, name):
    try:
        # delete_doc gère les hooks & permissions proprement
        frappe.delete_doc(doctype, name, ignore_permissions=True, force=True)
    except frappe.DoesNotExistError:
        pass

def execute():
    # Supprimer Server Scripts
    servers = frappe.get_all("Server Script", filters={"reference_doctype": "Quotation"}, pluck="name")
    for name in servers:
        safe_delete("Server Script", name)

    # Supprimer Client Scripts
    clients = frappe.get_all("Client Script", filters={"dt": "Quotation"}, pluck="name")
    for name in clients:
        safe_delete("Client Script", name)

    frappe.logger().info("Removed Server/Client Scripts for Quotation")
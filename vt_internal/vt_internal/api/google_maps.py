import frappe


@frappe.whitelist()
def get_google_maps_api_key():
    """
    Return Google Maps JavaScript API key from Google Settings.

    This is safe to expose to the browser as long as the key is restricted
    to allowed HTTP referrers in Google Cloud Console.

    Response shape:
    { "enabled": bool, "api_key": str | None }
    """
    try:
        settings = frappe.get_single("Google Settings")
    except Exception:
        return {"enabled": False, "api_key": None}

    api_key = settings.api_key or frappe.db.get_single_value("Google Settings", "api_key")
    enabled = bool(getattr(settings, "enable", 0)) and bool(api_key)
    return {"enabled": enabled, "api_key": api_key if enabled else None}

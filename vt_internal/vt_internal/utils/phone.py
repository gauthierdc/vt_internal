"""Utilitaires téléphone (envoi SMS)."""


def is_french_landline(phone):
    """True si le numéro est un fixe français (préfixe 04).

    AllMySMS refuse les fixes (HTTP 400) ; on ne tente pas le SMS.
    On normalise d'abord (espaces, points, tirets) et on ramène +334 /
    00334 au format national 04 — même cas, même exclusion.
    """
    n = str(phone or "").replace(" ", "").replace(".", "").replace("-", "")
    if n.startswith("+33"):
        rest = n[3:]
        n = rest if rest.startswith("0") else "0" + rest
    elif n.startswith("0033"):
        rest = n[4:]
        n = rest if rest.startswith("0") else "0" + rest
    return n.startswith("04")

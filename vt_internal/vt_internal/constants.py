"""Constantes métier partagées (source unique de vérité).

Réutilisées côté back (events/api timesheet) et exposées au front via
`timesheet_state`. Évite les magic strings dupliqués.
"""

# --- Types d'activité (Activity Type) ---
ACTIVITY_ATELIER = "Atelier"
ACTIVITY_VISITE = "Visite technique"
ACTIVITY_CHANTIER = "Chantier"

# --- États de pointage du jour (dérivés, non stockés tels quels) ---
TASK_DAY_NOT_STARTED = "Day not started"
TASK_DAY_FINISHED = "Day finished"
TASK_PAUSE = "Pause"

# --- Statuts Fiche de travail ---
FT_STATUS_TODO = "À faire"
FT_STATUS_WAITING_FAB = "En attente de fabrication"
FT_STATUS_IN_PROGRESS = "En cours"
FT_STATUS_DONE = "Fait"

# Statuts qui passent automatiquement "En cours" dès qu'on pointe dessus.
FT_STATUSES_TO_START = (FT_STATUS_TODO, FT_STATUS_WAITING_FAB)

# --- Marqueurs d'avancement (par priorité décroissante) ---
AVANCEMENT_MARKERS = ("⚫️", "🔴", "🟠", "🟢")

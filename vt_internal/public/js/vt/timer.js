// Module partagé de pointage (timer feuilles de temps / fiches de travail).
// Remplace le helper `timer_api` et le bloc de boutons dupliqués dans
// visite_technique.js et fiche_de_travail.js. Chargé via vt_common.bundle.js.

frappe.provide("vt.timer");

vt.timer.GROUP = "⏱️";

// État de pointage du jour + actions autorisées (pilotées par le back).
vt.timer.get_state = () =>
    frappe.call({ method: "timesheet_state" }).then((r) => r.message);

// Poste une action de pointage. `toast` optionnel affiché en cas de succès.
vt.timer.post = (payload, toast) =>
    frappe.call({ method: "timesheet_post_api", args: payload }).then(() => {
        if (toast) frappe.show_alert({ message: toast, indicator: "green" }, 5);
    });

// Retire les boutons de pointage précédemment injectés (évite les doublons au refresh).
vt.timer._clear_buttons = (frm) => {
    (frm.__vt_timer_labels || []).forEach((lbl) => {
        frm.remove_custom_button(__(lbl), vt.timer.GROUP);
        frm.remove_custom_button(__(lbl)); // cas du bouton principal (hors groupe)
    });
    frm.__vt_timer_labels = [];
};

// Construit la charge utile propre envoyée au back pour une action.
vt.timer._payload = (action, extra) => {
    const p = { action: action.action, ...extra };
    if (action.activity_type) p.activity_type = action.activity_type;
    return p;
};

/**
 * Injecte les boutons de pointage dans un formulaire.
 * @param {object}   frm
 * @param {object}   [extra]  - champs ajoutés à chaque action (ex: {fiche_de_travail})
 * @param {function} [onDone] - callback(frm) après action (défaut: re-render des boutons)
 */
vt.timer.render_buttons = function (frm, extra = {}, onDone) {
    return vt.timer.get_state().then((state) => {
        vt.timer._clear_buttons(frm);

        state.actions.forEach((action) => {
            const run = () => {
                const doIt = () =>
                    vt.timer
                        .post(vt.timer._payload(action, extra), action.toast)
                        .then(() =>
                            onDone ? onDone(frm) : vt.timer.render_buttons(frm, extra, onDone)
                        );
                if (action.confirm) frappe.confirm(__(action.confirm), doIt);
                else doIt();
            };

            // Bouton principal → autonome ; sinon rangé dans le menu ⏱️.
            if (action.primary) frm.add_custom_button(__(action.label), run);
            else frm.add_custom_button(__(action.label), run, vt.timer.GROUP);

            frm.__vt_timer_labels.push(action.label);
        });

        return state;
    });
};

/**
 * Dialog « démarrer une tâche » (type d'activité + fiche + SAV).
 * @param {object} frm
 * @param {object} [opts.default_ft] - fiche de travail par défaut
 * @param {function} [opts.onDone]
 */
vt.timer.start_activity = function (frm, { default_ft, onDone } = {}) {
    frappe.prompt(
        [
            {
                label: "Type d'activité",
                fieldname: "activity_type",
                fieldtype: "Link",
                options: "Activity Type",
                default: "Chantier",
            },
            {
                label: "Fiche de travail",
                fieldname: "fiche_de_travail",
                fieldtype: "Link",
                options: "Fiche de travail",
                default: default_ft,
            },
            { label: "SAV", fieldname: "sav", fieldtype: "Check" },
        ],
        (values) => {
            vt.timer
                .post({
                    action: "start_construction",
                    fiche_de_travail: values.fiche_de_travail,
                    activity_type: values.activity_type,
                    sav: values.sav,
                })
                .then(() =>
                    onDone ? onDone(frm) : vt.timer.render_buttons(frm, { fiche_de_travail: frm.doc.name })
                );
        },
        "Démarrer une tâche",
        "Démarrer"
    );
};

// Widget « Ma journée » : bouton flottant en bas à droite qui déroule un
// mini tableau de bord de pointage (statut, fiches du jour, activités).
// Icônes vectorielles (jeu Lucide via frappe.utils.icon), dates en français.
// Entièrement défensif : toute erreur masque le widget sans impacter le Desk.

frappe.provide("vt.timer");

// DocTypes sur lesquels on propose un pointage contextuel « ce document ».
vt.timer.WIDGET_CONTEXT_DOCTYPES = ["Fiche de travail", "Visite Technique"];

vt.timer.widget = {
    $el: null,
    state: null,
    tick_interval: null,
    open: false,

    init() {
        try {
            if (vt.timer.widget.$el) return; // déjà monté
            if (!frappe.session || frappe.session.user === "Guest") return;

            vt.timer.widget.$el = $('<div class="vt-timer-widget" style="display:none"></div>').appendTo("body");

            // Fermer le panneau au clic en dehors du widget.
            $(document).on("click.vt_timer_widget", (e) => {
                if (vt.timer.widget.open && !$(e.target).closest(".vt-timer-widget").length) {
                    vt.timer.widget.open = false;
                    vt.timer.widget.render();
                }
            });

            // Re-rendu au changement de page : le bouton contextuel « pointer sur
            // ce document » dépend du formulaire ouvert (pas de nouvel appel back).
            if (frappe.router && frappe.router.on) {
                frappe.router.on("change", () => {
                    if (vt.timer.widget.state && vt.timer.widget.state.employee) {
                        vt.timer.widget.render();
                    }
                });
            }

            vt.timer.widget.refresh();
        } catch (e) {
            console.warn("vt.timer.widget init failed", e);
        }
    },

    refresh() {
        return vt.timer
            .get_state()
            .then((state) => {
                vt.timer.widget.state = state;
                if (!state || !state.employee) {
                    vt.timer.widget.$el && vt.timer.widget.$el.hide();
                    return;
                }
                vt.timer.widget.render();
            })
            .catch((e) => {
                console.warn("vt.timer.widget refresh failed", e);
                vt.timer.widget.$el && vt.timer.widget.$el.hide();
            });
    },

    // Icône vectorielle Lucide (couleur héritée du texte).
    ic(name) {
        try {
            return frappe.utils.icon(name, "sm", "", "", "", true);
        } catch (e) {
            return "";
        }
    },

    _dot(task) {
        const map = {
            "Day not started": "vt-timer-widget__dot--idle",
            "Day finished": "vt-timer-widget__dot--done",
            Pause: "vt-timer-widget__dot--pause",
        };
        return map[task] || "vt-timer-widget__dot--active";
    },

    _label(state) {
        const map = {
            "Day not started": "Journée non démarrée",
            "Day finished": "Journée terminée",
        };
        if (map[state.current_task]) return map[state.current_task];
        if (state.fiche_de_travail) return state.fiche_reference || state.fiche_de_travail;
        return state.current_task;
    },

    // Date du jour en français, sans dépendre de la locale moment.
    _french_date() {
        const jours = ["dimanche", "lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi"];
        const mois = [
            "janvier", "février", "mars", "avril", "mai", "juin",
            "juillet", "août", "septembre", "octobre", "novembre", "décembre",
        ];
        const d = new Date();
        return `${jours[d.getDay()]} ${d.getDate()} ${mois[d.getMonth()]}`;
    },

    // Sous-titre de la carte de statut (activité + heure de début).
    _subtitle(state) {
        const parts = [];
        if (state.fiche_de_travail && state.current_task) parts.push(state.current_task);
        const start = state.task_from_time || state.from_time;
        if (start && state.current_task !== "Day finished" && state.current_task !== "Day not started") {
            parts.push(`depuis ${moment(start).format("HH:mm")}`);
        }
        return parts.join(" · ");
    },

    // Formatte un nombre d'heures décimal en « 3h15 » / « 45min » / « 0min ».
    _fmt_hours(h) {
        const total = Math.round((h || 0) * 60);
        const hh = Math.floor(total / 60);
        const mm = total % 60;
        if (!hh) return `${mm}min`;
        return `${hh}h${String(mm).padStart(2, "0")}`;
    },

    // En-tête « Ma journée » : titre, date, statistiques du jour.
    _header(state) {
        const esc = frappe.utils.escape_html;
        const ic = vt.timer.widget.ic;
        const nb = (state.today_events || []).length;
        // La puce des heures pointées ouvre la feuille de temps du jour (si elle existe).
        const hours = `${ic("clock")} ${vt.timer.widget._fmt_hours(state.total_hours)} pointées`;
        const chips = [
            state.timesheet
                ? `<button class="vt-timer-widget__stat vt-timer-widget__stat--btn" title="Ouvrir la feuille de temps du jour">${hours}</button>`
                : `<span class="vt-timer-widget__stat">${hours}</span>`,
        ];
        if (nb) {
            chips.push(
                `<span class="vt-timer-widget__stat">${ic("calendar")} ${nb} événement${nb > 1 ? "s" : ""}</span>`
            );
        }
        return `
            <div class="vt-timer-widget__head">
                <div class="vt-timer-widget__head-top">
                    <span class="vt-timer-widget__head-title">Ma journée</span>
                    <span class="vt-timer-widget__head-date">${esc(vt.timer.widget._french_date())}</span>
                </div>
                <div class="vt-timer-widget__stats">${chips.join("")}</div>
            </div>`;
    },

    // Document actuellement ouvert dans le Desk, si c'est une fiche/visite.
    _open_doc() {
        try {
            const r = frappe.get_route();
            if (r && r[0] === "Form" && vt.timer.WIDGET_CONTEXT_DOCTYPES.includes(r[1]) && r[2]) {
                return { doctype: r[1], name: r[2] };
            }
        } catch (e) {
            /* pas de route exploitable */
        }
        return null;
    },

    // Items du panneau, chacun rangé dans un groupe.
    _menu_actions() {
        const state = vt.timer.widget.state;
        const items = [];
        const refresh = () => vt.timer.widget.refresh();
        const finished = state.current_task === "Day finished";

        // Événements planifiés aujourd'hui (fiche / visite / autre).
        // Clic sur le libellé = ouvrir l'élément · clic sur « play » = démarrer le pointage.
        (state.today_events || []).forEach((ev) => {
            const time = ev.starts_on ? moment(ev.starts_on).format("HH:mm") : "";
            const prefix = time ? `${time} · ` : "";
            let main, open_run, start_run, active = false;

            if (ev.kind === "fiche") {
                const ref = ev.fiche_reference || ev.fiche;
                main = `${ev.subject || ref}${ev.fiche_status ? ` — ${ev.fiche_status}` : ""}`;
                active = ev.fiche === state.fiche_de_travail;
                open_run = () => frappe.set_route("Form", "Fiche de travail", ev.fiche);
                start_run = active
                    ? null
                    : () =>
                          vt.timer
                              .post({
                                  action: "start_construction",
                                  fiche_de_travail: ev.fiche,
                                  activity_type: "Chantier",
                              })
                              .then(refresh);
            } else if (ev.kind === "visite") {
                main = ev.subject || ev.visite;
                open_run = () => frappe.set_route("Form", "Visite Technique", ev.visite);
                start_run = () =>
                    vt.timer
                        .post({ action: "start_construction", activity_type: "Visite technique", project: ev.project })
                        .then(refresh);
            } else {
                main = ev.subject || ev.event;
                open_run = () => frappe.set_route("Form", "Event", ev.event);
                start_run = null; // agenda simple : pas de pointage
            }

            items.push({
                label: `${prefix}${main}`,
                title: `${time ? time + " — " : ""}Ouvrir`,
                group: "today",
                active,
                run: open_run, // clic principal → ouvre l'élément
                start_run,
                maps: ev.maps || null, // adresse pour Google Maps
            });
        });

        // (La feuille de temps du jour est accessible via un bouton discret de l'en-tête.)

        // Pointage contextuel sur le document ouvert dans le Desk (fiche ou visite).
        const doc = vt.timer.widget._open_doc();
        if (doc && !finished && doc.name !== state.fiche_de_travail) {
            const same = typeof cur_frm !== "undefined" && cur_frm && cur_frm.doc && cur_frm.doc.name === doc.name;
            if (doc.doctype === "Fiche de travail") {
                const ref = same ? cur_frm.doc["référence_pièce"] || doc.name : doc.name;
                items.push({
                    label: `Pointer sur cette fiche : ${ref}`,
                    icon: "play",
                    group: "context",
                    run: () => vt.timer.start_activity(null, { default_ft: doc.name, onDone: refresh }),
                });
            } else {
                const project = same ? cur_frm.doc.projet : null;
                items.push({
                    label: `Pointer sur cette visite : ${doc.name}`,
                    icon: "play",
                    group: "context",
                    run: () =>
                        vt.timer
                            .post({ action: "start_construction", activity_type: "Visite technique", project })
                            .then(refresh),
                });
            }
        }

        // Actions génériques pilotées par le back (icône fournie par le back).
        (state.actions || []).forEach((a) => {
            let group = "activity";
            if (a.action === "start_break") group = "break";
            else if (a.action === "stop_day") group = "danger";
            items.push({
                label: a.label,
                icon: a.icon,
                group,
                run: () => {
                    const doIt = () => vt.timer.post(vt.timer._payload(a, {})).then(refresh);
                    a.confirm ? frappe.confirm(__(a.confirm), doIt) : doIt();
                },
            });
        });

        // Démarrer un chrono rattaché à une fiche (choix via dialog).
        if (!finished) {
            items.push({
                label: "Démarrer sur une fiche de travail…",
                icon: "briefcase",
                group: "activity",
                run: () => vt.timer.start_activity(null, { onDone: refresh }),
            });
        }
        return items;
    },

    render() {
        const state = vt.timer.widget.state;
        const $el = vt.timer.widget.$el;
        if (!state) return;

        const esc = frappe.utils.escape_html;
        const ic = vt.timer.widget.ic;
        const items = vt.timer.widget._menu_actions();
        const idx = items.map((it, i) => ({ ...it, i }));
        const of = (g) => idx.filter((it) => it.group === g);

        const btn = (it, cls) =>
            `<button class="btn vt-timer-widget__item ${cls}" data-idx="${it.i}"${
                it.title ? ` title="${esc(it.title)}"` : ""
            }>${it.icon ? `<span class="vt-timer-widget__ic">${ic(it.icon)}</span>` : ""}<span class="vt-timer-widget__txt">${esc(
                it.label
            )}</span></button>`;

        // --- Carte de statut ---
        const subtitle = vt.timer.widget._subtitle(state);
        const statusCard = `
            <div class="vt-timer-widget__status">
                <span class="vt-timer-widget__dot vt-timer-widget__dot--lg ${vt.timer.widget._dot(state.current_task)}"></span>
                <div class="vt-timer-widget__status-body">
                    <div class="vt-timer-widget__status-title">${esc(vt.timer.widget._label(state))}</div>
                    <div class="vt-timer-widget__status-sub">
                        ${subtitle ? esc(subtitle) : ""}
                        <span class="vt-timer-widget__chrono"></span>
                    </div>
                </div>
            </div>`;

        // --- Sections ---
        let body = "";

        const today = of("today");
        if (today.length) {
            body += `<div class="vt-timer-widget__section-title">Événements du jour</div>`;
            body += today
                .map((it) => {
                    const main = btn(it, `vt-timer-widget__item--today${it.active ? " is-active" : ""}`);
                    // Bouton Maps (si adresse connue).
                    const mapsBtn = it.maps
                        ? `<button class="btn vt-timer-widget__item vt-timer-widget__item--mapsbtn" data-idx="${it.i}" data-maps="1" title="Ouvrir dans Google Maps">${ic(
                              "navigation"
                          )}</button>`
                        : "";
                    // Bouton « play » (démarrer le pointage) seulement pour fiche/visite.
                    const startBtn =
                        it.start_run || it.active
                            ? `<button class="btn vt-timer-widget__item vt-timer-widget__item--iconbtn${
                                  it.active ? " is-active" : ""
                              }" data-idx="${it.i}" data-start="1" title="${
                                  it.active ? "Pointage en cours" : "Démarrer le pointage"
                              }">${ic(it.active ? "check" : "play")}</button>`
                            : "";
                    return `<div class="vt-timer-widget__row">${main}${mapsBtn}${startBtn}</div>`;
                })
                .join("");
        }

        const open = of("open");
        if (open.length) {
            body += `<div class="vt-timer-widget__quick">${open
                .map((it) => btn(it, "vt-timer-widget__item--open"))
                .join("")}</div>`;
        }

        of("context").forEach((it) => {
            body += btn(it, "vt-timer-widget__item--primary");
        });

        const activity = of("activity");
        if (activity.length) {
            body += `<div class="vt-timer-widget__section-title">Activités</div>`;
            body += activity.map((it) => btn(it, "vt-timer-widget__item--activity")).join("");
        }

        const footer = [...of("break"), ...of("danger")];
        if (footer.length) {
            body += `<div class="vt-timer-widget__footer">${of("break")
                .map((it) => btn(it, "vt-timer-widget__item--break"))
                .join("")}${of("danger")
                .map((it) => btn(it, "vt-timer-widget__item--danger"))
                .join("")}</div>`;
        }

        $el.html(`
            <div class="vt-timer-widget__panel" ${vt.timer.widget.open ? "" : "hidden"}>
                ${vt.timer.widget._header(state)}
                ${statusCard}
                <div class="vt-timer-widget__actions">
                    ${body || `<div class="vt-timer-widget__empty text-muted">Aucune action disponible</div>`}
                </div>
            </div>
            <div class="vt-timer-widget__bar">
                <button class="vt-timer-widget__calbtn" title="Ouvrir le calendrier" aria-label="Calendrier">${ic(
                    "calendar"
                )}</button>
                <button class="vt-timer-widget__toggle">
                    <span class="vt-timer-widget__dot ${vt.timer.widget._dot(state.current_task)}"></span>
                    <span class="vt-timer-widget__label">${esc(vt.timer.widget._label(state))}</span>
                    <span class="vt-timer-widget__chrono vt-timer-widget__chrono--toggle"></span>
                    <span class="vt-timer-widget__caret">${ic(vt.timer.widget.open ? "chevron-down" : "chevron-up")}</span>
                </button>
            </div>
        `).show();

        // Bouton calendrier dédié : accès direct à la vue calendrier.
        $el.find(".vt-timer-widget__calbtn").off("click").on("click", (e) => {
            e.stopPropagation();
            vt.timer.widget.open = false;
            frappe.set_route("List", "Event", "Calendar");
        });

        // La puce des heures pointées ouvre la feuille de temps du jour.
        $el.find(".vt-timer-widget__stat--btn").off("click").on("click", (e) => {
            e.stopPropagation();
            vt.timer.widget.open = false;
            if (state.timesheet) frappe.set_route("Form", "Timesheet", state.timesheet);
        });

        // stopPropagation : sinon le re-render détache le noeud cliqué et le
        // handler « clic extérieur » sur document refermerait aussitôt le panneau.
        $el.find(".vt-timer-widget__toggle").off("click").on("click", (e) => {
            e.stopPropagation();
            vt.timer.widget.open = !vt.timer.widget.open;
            vt.timer.widget.render();
        });

        $el.find(".vt-timer-widget__item").off("click").on("click", function (e) {
            e.stopPropagation();
            const it = items[$(this).data("idx")];
            vt.timer.widget.open = false;
            if ($(this).data("maps") && it.maps) {
                window.open(
                    `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(it.maps)}`,
                    "_blank"
                );
            } else if ($(this).data("start") && it.start_run) {
                it.start_run();
            } else {
                it.run();
            }
        });

        vt.timer.widget._start_chrono();
    },

    _start_chrono() {
        clearInterval(vt.timer.widget.tick_interval);
        const state = vt.timer.widget.state;
        const start = state.task_from_time || state.from_time;
        const $chrono = vt.timer.widget.$el.find(".vt-timer-widget__chrono");

        if (!start || state.current_task === "Day finished") {
            $chrono.text("");
            return;
        }

        const tick = () => {
            const mins = Math.max(0, moment().diff(moment(start), "minutes"));
            const h = Math.floor(mins / 60);
            const m = mins % 60;
            $chrono.text(h ? `${h}h${String(m).padStart(2, "0")}` : `${m}min`);
        };
        tick();
        vt.timer.widget.tick_interval = setInterval(tick, 30000);
    },
};

$(document).ready(() => vt.timer.widget.init());

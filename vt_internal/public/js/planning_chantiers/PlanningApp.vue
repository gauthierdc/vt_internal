<template>
	<div class="vpc-root" :class="{ 'vpc-busy': store.loading && data }" @mousemove="onTipMove" @mouseleave="tip.show = false">
		<!-- Barre de chargement -->
		<div v-if="store.loading" class="vpc-loadbar"><div class="bar"></div></div>

		<!-- Modale riche flottante (survol d'un jalon) -->
		<div v-if="tip.show && tip.ms" class="vpc-tip" :style="{ left: tip.x + 'px', top: tip.y + 'px' }">
			<div class="vpc-tip-head" :style="{ background: typeMeta(tip.ms.type).bg, color: typeMeta(tip.ms.type).color }">
				<span class="ic">{{ typeMeta(tip.ms.type).icon }}</span>
				<span class="lbl">{{ typeMeta(tip.ms.type).label }}</span>
				<span class="vpc-tip-state" :class="tipState(tip.ms).cls">{{ tipState(tip.ms).txt }}</span>
			</div>
			<div class="vpc-tip-title">{{ tip.ms.title }}</div>
			<div class="vpc-tip-ref">{{ tip.ms.ref }}</div>
			<div class="vpc-tip-grid">
				<template v-if="tip.ms.type === 'po'">
					<span>{{ __('Échéance') }}</span><b>{{ fmtDate(tip.ms.date) }}</b>
					<span>{{ __('Montant') }}</span><b>{{ fmtMoney(tip.ms.amount) }}</b>
					<span>{{ __('Reçu') }}</span><b>{{ tip.ms.received_qty }} / {{ tip.ms.qty }}</b>
					<span>{{ __('Lignes') }}</span><b>{{ tip.ms.nb_lines }}</b>
				</template>
				<template v-else-if="tip.ms.type === 'fab'">
					<span>{{ __('Fin prévue') }}</span><b>{{ fmtDate(tip.ms.date) }}</b>
					<span>{{ __('Statut') }}</span><b>{{ tip.ms.status }}</b>
					<span>{{ __('Coût') }}</span><b>{{ fmtMoney(tip.ms.amount) }}</b>
				</template>
				<template v-else-if="tip.ms.type === 'delivery'">
					<span>{{ __('Date de livraison') }}</span><b>{{ fmtDate(tip.ms.date) }}</b>
					<span>{{ __('Statut commande') }}</span><b>{{ (orderStatus(tip.ms) || {}).label || tip.ms.status }}</b>
					<span>{{ __('Livré') }}</span><b>{{ tip.ms.per_delivered }}%</b>
					<span>{{ __('Montant') }}</span><b>{{ fmtMoney(tip.ms.amount) }}</b>
				</template>
				<template v-else-if="isEv(tip.ms.type)">
					<span v-if="tip.ms.employee_name">{{ __('Employé') }}</span><b v-if="tip.ms.employee_name">{{ tip.ms.employee_name }}</b>
					<span>{{ __('Début') }}</span><b>{{ fmtDateTime(tip.ms.starts_on) }}</b>
					<span v-if="tip.ms.ends_on">{{ __('Fin') }}</span><b v-if="tip.ms.ends_on">{{ fmtDateTime(tip.ms.ends_on) }}</b>
					<span v-if="tip.ms.linked_name">{{ typeMeta(tip.ms.type).label }}</span><b v-if="tip.ms.linked_name">{{ tip.ms.linked_name }}</b>
					<span v-if="tip.ms.category">{{ __('Catégorie') }}</span><b v-if="tip.ms.category">{{ tip.ms.category }}</b>
				</template>
				<template v-else-if="tip.ms.type === 'reception'">
					<span>{{ __('Réceptionné le') }}</span><b>{{ fmtDate(tip.ms.date) }}</b>
					<span v-if="tip.ms.status">{{ __('Statut') }}</span><b v-if="tip.ms.status">{{ tip.ms.status }}</b>
					<span v-if="tip.ms.date_levee_reserve">{{ __('Levée réserve') }}</span><b v-if="tip.ms.date_levee_reserve">{{ fmtDate(tip.ms.date_levee_reserve) }}</b>
				</template>
			</div>
			<div class="vpc-tip-foot">{{ __('Cliquer pour ouvrir') }} · {{ docLabel(tip.ms.doctype) }}</div>
		</div>

		<!-- Barre de période -->
		<div class="vpc-periodbar">
			<button class="vpc-nav" data-tip="Reculer de 4 semaines" @click="store.shiftWeeks(-4)">«</button>
			<button class="vpc-nav" data-tip="Reculer d'une semaine" @click="store.shiftWeeks(-1)">‹</button>
			<button class="vpc-today" @click="store.goToday()">{{ __("Aujourd'hui") }}</button>
			<button class="vpc-nav" data-tip="Avancer d'une semaine" @click="store.shiftWeeks(1)">›</button>
			<button class="vpc-nav" data-tip="Avancer de 4 semaines" @click="store.shiftWeeks(4)">»</button>
			<span v-if="data" class="vpc-period-lbl">{{ fmtDate(data.period.start_date) }} → {{ fmtDate(data.period.end_date) }}</span>
			<div class="vpc-weeks-sel vpc-gran-sel">
				<button :class="{ active: store.filters.granularity === 'week' }" @click="setGranularity('week')">{{ __('Semaine') }}</button>
				<button :class="{ active: store.filters.granularity === 'day' }" @click="setGranularity('day')">{{ __('Jour') }}</button>
			</div>
			<div class="vpc-weeks-sel">
				<button v-for="w in weekOptions" :key="w" :class="{ active: store.filters.weeks === w }" @click="setWeeks(w)">{{ w }} {{ __('sem.') }}</button>
			</div>
			<span class="vpc-refreshing" :class="{ show: store.loading }">{{ __('actualisation…') }}</span>
		</div>

		<!-- Filtres globaux -->
		<div class="vpc-filters" v-if="data">
			<DropSelect icon="🏢" :model-value="store.filters.company || ''" :all-label="__('Toutes les sociétés')"
				:options="data.meta.companies.map((c) => ({ value: c, label: c }))"
				@update:model-value="(v) => setFilter('company', v)" />
			<DropSelect v-if="data.meta.cost_centers.length" icon="🏦" :model-value="store.filters.cost_center || ''"
				:all-label="__('Tous les centres de coût')" :options="data.meta.cost_centers"
				@update:model-value="(v) => setFilter('cost_center', v)" />
			<DropSelect v-if="data.meta.conducteurs.length" icon="👷" :model-value="store.filters.conducteur || ''"
				:all-label="__('Tous les conducteurs')" :options="data.meta.conducteurs"
				@update:model-value="(v) => setFilter('conducteur', v)" />
			<DropSelect v-if="data.meta.responsables && data.meta.responsables.length" icon="🧑‍💼" :model-value="store.filters.responsable || ''"
				:all-label="__('Tous les responsables')" :options="data.meta.responsables"
				@update:model-value="(v) => setFilter('responsable', v)" />
			<label class="vpc-check"><input type="checkbox" :checked="store.filters.only_active" @change="toggleActive($event)" /> {{ __('Chantiers actifs seulement') }}</label>
		</div>

		<!-- KPIs -->
		<div class="vpc-kpis" v-if="data">
			<div class="vpc-kpi"><div class="v">{{ data.summary.nb_projects }}</div><div class="l">{{ __('Chantiers planifiés') }}</div></div>
			<div class="vpc-kpi po"><div class="v">{{ data.summary.nb_po }}</div><div class="l">🛒 {{ __('Réceptions à venir') }}</div></div>
			<div class="vpc-kpi fab"><div class="v">{{ data.summary.nb_fab }}</div><div class="l">🏭 {{ __('Fabrications à finir') }}</div></div>
			<div class="vpc-kpi delivery"><div class="v">{{ data.summary.nb_delivery }}</div><div class="l">🚚 {{ __('Livraisons prévues') }}</div></div>
			<div class="vpc-kpi danger"><div class="v">{{ data.summary.nb_overdue }}</div><div class="l">⚠️ {{ __('Jalons en retard') }}</div></div>
			<div class="vpc-kpi"><div class="v">{{ fmtCompact(data.summary.reste_a_facturer) }}</div><div class="l">{{ __('Reste à facturer') }}</div></div>
		</div>

		<!-- Barre d'outils -->
		<div class="vpc-toolbar" v-if="data">
			<input class="vpc-search" v-model="search" :placeholder="__('Rechercher un chantier, client, statut…')" />
			<div class="vpc-types">
				<button v-for="(t, key) in typeDefs" :key="key" class="vpc-type-toggle" :class="{ off: !typeFilter[key] }"
					:style="typeFilter[key] ? { background: t.bg, color: t.color } : {}"
					@click="typeFilter[key] = !typeFilter[key]">{{ t.icon }} {{ t.label }}</button>
			</div>
			<label class="vpc-check"><input type="checkbox" v-model="onlyOverdue" /> {{ __('En retard uniquement') }}</label>
			<span class="vpc-count">{{ visibleRows.length }} / {{ data.rows.length }} {{ __('chantiers') }}</span>
		</div>

		<!-- États -->
		<template v-if="store.loading && !data">
			<div class="vpc-skel" v-for="n in 8" :key="n"></div>
		</template>
		<div v-else-if="store.error" class="vpc-error">{{ store.error }}</div>
		<div v-else-if="data && !visibleRows.length" class="vpc-empty">
			{{ __('Aucun chantier avec un jalon sur cette période.') }}
			<div class="vpc-empty-sub">{{ __('Essayez d’élargir la période ou de retirer des filtres.') }}</div>
		</div>

		<!-- Grille -->
		<div v-else-if="data" class="vpc-grid-wrap">
			<table class="vpc-grid" :class="{ day: data.period.granularity === 'day' }" :style="{ '--nweeks': data.weeks.length }">
				<thead>
					<tr>
						<th class="vpc-corner">{{ __('Chantier') }}</th>
						<th v-for="w in data.weeks" :key="w.index" class="vpc-wk" :class="{ current: w.is_current, past: w.is_past }">
							<div class="vpc-wk-num">{{ w.top }}</div>
							<div class="vpc-wk-date">{{ w.bottom }}</div>
						</th>
					</tr>
				</thead>
				<tbody>
					<tr v-for="r in displayRows" :key="r.project">
						<th class="vpc-rowhead" @click="openProject(r.project)" :data-tip="__('Ouvrir la fiche chantier')">
							<div class="vpc-rh-top">
								<span class="vpc-rh-name">{{ r.project }}</span>
								<span class="vpc-rh-badges">
									<span
										v-if="r.nb_incidents"
										class="vpc-rh-inc" :class="{ closed: !r.nb_incidents_ouverts }"
										:data-tip="incidentTip(r)"
										@click.stop="openIncidents(r)"
									>⚠️ {{ r.nb_incidents }}</span>
									<span v-if="r.nb_overdue" class="vpc-rh-late" :data-tip="r.nb_overdue + ' jalon(s) en retard'">⏰ {{ r.nb_overdue }}</span>
								</span>
							</div>
							<div class="vpc-rh-client">{{ r.customer }}</div>
							<div class="vpc-rh-meta">
								<span
									v-if="r.construction_status_so"
									class="vpc-rh-status" :class="{ empty: !r.construction_status }"
									:data-tip="(r.construction_status ? __('Statut du chantier') + ' : ' + r.construction_status + ' — ' : '') + __('cliquer pour modifier')"
									@click.stop="editConstructionStatus(r)"
								>{{ r.construction_status || __('＋ statut de chantier') }}</span>
								<span v-if="r.conducteur_nom" class="vpc-rh-cm">👷 {{ r.conducteur_nom }}</span>
								<span v-if="r.responsable_nom" class="vpc-rh-cm" :data-tip="__('Responsable de chantier')">🧑‍💼 {{ r.responsable_nom }}</span>
							</div>
							<div class="vpc-rh-fact" v-if="r.total_sold" :data-tip="fmtMoney(r.billed) + ' facturé / ' + fmtMoney(r.total_sold) + ' commandé'">
								<div class="bar"><div class="fill" :style="{ width: Math.min(r.pct_facture, 100) + '%' }"></div></div>
								<span class="txt">{{ r.pct_facture }}% · {{ fmtCompact(r.total_sold) }}</span>
							</div>
						</th>
						<td v-for="w in data.weeks" :key="w.index" class="vpc-cell" :class="{ current: w.is_current, past: w.is_past }">
							<button
								v-for="(m, i) in cellMs(r, w.index)" :key="i"
								class="vpc-chip" :class="[m.type, { done: m.done, overdue: m.overdue }]"
								:style="chipStyle(m)"
								@click="store.openDoc(m.doctype, m.ref)"
								@mouseenter="showTip(m, $event)" @mousemove="moveTip($event)" @mouseleave="tip.show = false"
							>
								<span class="ci">{{ typeMeta(m.type).icon }}</span>
								<span class="ct">{{ chipLabel(m) }}</span>
								<span v-if="m.done" class="cd">✓</span>
							</button>
						</td>
					</tr>
				</tbody>
			</table>
			<div v-if="visibleRows.length > displayRows.length" class="vpc-more">
				<button @click="limit += 100">{{ __('Afficher plus') }} ({{ visibleRows.length - displayRows.length }} {{ __('restants') }})</button>
			</div>
		</div>
	</div>
</template>

<script>
import DropSelect from "./DropSelect.vue";
import { fmtMoney, fmtCompact, fmtDate, fmtDateTime, MILESTONE_TYPES, isEventLike, salesOrderStatus, ORDER_STATUS_COLORS } from "./helpers.js";

export default {
	name: "PlanningApp",
	components: { DropSelect },
	props: { store: Object },
	data() {
		return {
			search: "",
			onlyOverdue: false,
			typeFilter: { po: true, fab: true, delivery: true, vt: true, ft: true, event: true, reception: true },
			typeDefs: {
				po: { icon: "🛒", label: __("Récept. fournisseur"), color: MILESTONE_TYPES.po.color, bg: MILESTONE_TYPES.po.bg },
				fab: { icon: "🏭", label: __("Fabrications"), color: MILESTONE_TYPES.fab.color, bg: MILESTONE_TYPES.fab.bg },
				delivery: { icon: "🚚", label: __("Livraisons"), color: MILESTONE_TYPES.delivery.color, bg: MILESTONE_TYPES.delivery.bg },
				vt: { icon: "🔍", label: __("Visites tech."), color: MILESTONE_TYPES.vt.color, bg: MILESTONE_TYPES.vt.bg },
				ft: { icon: "📋", label: __("Fiches de travail"), color: MILESTONE_TYPES.ft.color, bg: MILESTONE_TYPES.ft.bg },
				event: { icon: "📅", label: __("Événements"), color: MILESTONE_TYPES.event.color, bg: MILESTONE_TYPES.event.bg },
				reception: { icon: "✅", label: __("Récept. chantier"), color: MILESTONE_TYPES.reception.color, bg: MILESTONE_TYPES.reception.bg },
			},
			limit: 100,
			tip: { show: false, ms: null, x: 0, y: 0 },
		};
	},
	computed: {
		data() { return this.store.data; },
		visibleRows() {
			if (!this.data) return [];
			const q = this.search.trim().toLowerCase();
			const tf = this.typeFilter;
			const allTypes = Object.values(tf).every(Boolean);
			return this.data.rows.filter((r) => {
				if (q && !((r.project + " " + r.customer + " " + (r.construction_status || "") + " " + (r.conducteur_nom || "") + " " + (r.responsable_nom || "")).toLowerCase().includes(q))) return false;
				// Jalons visibles selon les filtres de type / retard.
				const vis = r.milestones.filter((m) => (allTypes || tf[m.type]) && (!this.onlyOverdue || m.overdue));
				return vis.length > 0;
			});
		},
		displayRows() { return this.visibleRows.slice(0, this.limit); },
		weekOptions() { return this.store.filters.granularity === "day" ? [1, 2, 3, 4] : [8, 14, 20, 26]; },
	},
	methods: {
		fmtMoney, fmtCompact, fmtDate, fmtDateTime,
		typeMeta(t) { return MILESTONE_TYPES[t] || { icon: "•", label: t, color: "#607d8b", bg: "rgba(96,125,139,.12)" }; },
		isEv(t) { return isEventLike(t); },
		docLabel(dt) { return { "Event": __("Événement"), "Sales Order": __("Commande client"), "Purchase Order": __("Commande fournisseur"), "Fabrication VT": __("Fabrication"), "Work Completion Receipt": __("Réception de chantier") }[dt] || dt; },
		setWeeks(w) { this.store.filters.weeks = w; this.store.reload(); },
		setGranularity(g) {
			if (this.store.filters.granularity === g) return;
			this.store.filters.granularity = g;
			// Adapte la fenêtre pour garder un nombre de colonnes lisible.
			if (g === "day" && this.store.filters.weeks > 4) this.store.filters.weeks = 3;
			if (g === "week" && this.store.filters.weeks < 6) this.store.filters.weeks = 14;
			this.store.reload();
		},
		setFilter(key, v) { this.store.filters[key] = v || null; this.store.reload(); },
		toggleActive(e) { this.store.filters.only_active = e.target.checked; this.store.reload(); },
		openProject(name) { this.store.openProject(name); },
		// Édition rapide du statut de chantier (texte libre sur la commande la
		// plus récente), comme l'ancien rapport Order book.
		editConstructionStatus(r) {
			const so = r.construction_status_so;
			if (!so) { frappe.show_alert({ message: __("Aucune commande liée à modifier"), indicator: "orange" }); return; }
			const d = new frappe.ui.Dialog({
				title: __("Statut du chantier") + " · " + r.project,
				fields: [{ fieldname: "status", fieldtype: "Small Text", label: __("Statut du chantier"), default: r.construction_status || "" }],
				primary_action_label: __("Enregistrer"),
				primary_action: (values) => {
					frappe.call({
						method: "frappe.client.set_value",
						args: { doctype: "Sales Order", name: so, fieldname: "custom_construction_status", value: values.status || "" },
						callback: () => {
							frappe.show_alert({ message: __("Statut mis à jour"), indicator: "green" });
							r.construction_status = (values.status || "").trim();
							d.hide();
						},
					});
				},
			});
			d.show();
		},
		incidentTip(r) {
			const n = r.nb_incidents, o = r.nb_incidents_ouverts;
			return `${n} ${__('incident(s) qualité')} (${o} ${__('ouvert(s)')}) — ${n === 1 ? __("cliquer pour ouvrir l'incident") : __('cliquer pour voir la liste')}`;
		},
		openIncidents(r) {
			const inc = r.incidents || [];
			if (!inc.length) return;
			if (inc.length === 1) { this.store.openDoc("Quality Incident", inc[0].name); return; }
			frappe.route_options = { project: r.project };
			frappe.set_route("List", "Quality Incident");
		},
		// Jalons d'une cellule (ligne × semaine), filtrés par type / retard.
		cellMs(r, weekIndex) {
			const tf = this.typeFilter;
			const allTypes = Object.values(tf).every(Boolean);
			return r.milestones.filter((m) => m.week === weekIndex && (allTypes || tf[m.type]) && (!this.onlyOverdue || m.overdue));
		},
		// Statut de commande (VOS libellés métier) pour un jalon livraison.
		orderStatus(m) { return m && m.type === "delivery" ? salesOrderStatus(m.so) : null; },
		chipStyle(m) {
			const t = this.typeMeta(m.type);
			if (m.done) return {};
			// Livraison : on colore selon VOTRE statut de commande.
			const os = this.orderStatus(m);
			if (os) {
				const c = ORDER_STATUS_COLORS[os.color] || { color: t.color, bg: t.bg };
				const style = { background: c.bg, color: c.color };
				if (m.overdue) style.borderColor = "rgba(198,40,40,.5)";
				return style;
			}
			if (m.overdue) return { background: "rgba(198,40,40,.14)", color: "#c62828", borderColor: "rgba(198,40,40,.5)" };
			return { background: t.bg, color: t.color };
		},
		chipLabel(m) {
			switch (m.type) {
				case "po": return this.fmtCompact(m.amount);
				case "fab": return this.trunc(m.title, 12);
				case "delivery": { const os = this.orderStatus(m); return this.trunc(os && os.label ? os.label : m.title, 14); }
				case "vt":
				case "ft":
				case "event": return this.trunc(m.employee_name || m.title, 14);
				case "reception": return __("reçu");
			}
			return "";
		},
		trunc(s, n) { s = s || ""; return s.length > n ? s.slice(0, n - 1) + "…" : s; },
		shortDate(d) {
			const dt = new Date(d + "T00:00:00");
			return new Intl.DateTimeFormat("fr-FR", { day: "2-digit", month: "2-digit" }).format(dt);
		},
		tipState(m) {
			if (m.done) return { cls: "ok", txt: __("Fait") };
			if (m.overdue) return { cls: "late", txt: __("En retard") };
			return { cls: "soon", txt: __("À venir") };
		},
		// --- Modale flottante ---
		showTip(m, e) { this.tip.ms = m; this.tip.show = true; this.moveTip(e); },
		moveTip(e) {
			const w = 300, h = 210;
			let x = e.clientX + 16, y = e.clientY + 16;
			if (x + w > window.innerWidth) x = e.clientX - w - 16;
			if (y + h > window.innerHeight) y = window.innerHeight - h - 12;
			this.tip.x = x; this.tip.y = y;
		},
		// Infobulle simple sur les autres éléments [data-tip] (réutilise la modale ? non).
		onTipMove(e) {
			// Ne gère que le masquage quand on quitte un chip ; les [data-tip] hors
			// chips utilisent le title natif via aria — on garde la modale riche
			// pilotée par showTip/moveTip uniquement.
			const chip = e.target.closest(".vpc-chip");
			if (!chip) this.tip.show = false;
		},
	},
};
</script>

<style scoped>
.vpc-root { padding: 4px 2px 40px; font-family: var(--font-stack, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif); color: var(--text-color, #1f272e); position: relative; }
.vpc-error { padding: 40px; text-align: center; color: var(--red-500, #c62828); }
.vpc-empty { padding: 50px; text-align: center; color: var(--text-muted, #6c7680); }
.vpc-empty-sub { font-size: 12px; margin-top: 6px; opacity: .8; }

/* Barre de chargement */
.vpc-loadbar { position: sticky; top: 0; height: 3px; background: var(--control-bg, #eef1f3); overflow: hidden; border-radius: 3px; z-index: 30; margin-bottom: 6px; }
.vpc-loadbar .bar { position: absolute; height: 100%; width: 35%; background: var(--blue-500, #1976d2); border-radius: 3px; animation: vpc-slide 1.1s ease-in-out infinite; }
@keyframes vpc-slide { 0% { left: -35%; } 60% { left: 100%; } 100% { left: 100%; } }
.vpc-busy .vpc-grid-wrap, .vpc-busy .vpc-kpis { opacity: .5; pointer-events: none; transition: opacity .15s; }

/* Barre de période */
.vpc-periodbar { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin: 2px 2px 14px; }
.vpc-nav { width: 30px; height: 30px; border: 1px solid var(--border-color, #e2e6ea); background: var(--control-bg, #fff); color: var(--text-color, #1f272e); border-radius: 8px; font-size: 16px; line-height: 1; cursor: pointer; }
.vpc-nav:hover { border-color: var(--blue-400, #64b5f6); color: var(--blue-600, #1565c0); }
.vpc-today { padding: 6px 14px; border: 1px solid var(--border-color, #e2e6ea); background: var(--control-bg, #fff); color: var(--blue-600, #1565c0); border-radius: 8px; font-size: 13px; font-weight: 560; cursor: pointer; }
.vpc-today:hover { border-color: var(--blue-400, #64b5f6); }
.vpc-period-lbl { font-size: 13px; font-weight: 600; margin-left: 6px; }
.vpc-weeks-sel { display: inline-flex; gap: 3px; background: var(--control-bg, #eef1f3); padding: 3px; border-radius: 9px; margin-left: 4px; }
.vpc-weeks-sel button { border: none; background: transparent; padding: 5px 10px; border-radius: 7px; font-size: 12px; font-weight: 540; color: var(--text-muted, #6c7680); cursor: pointer; }
.vpc-weeks-sel button.active { background: var(--card-bg, #fff); color: var(--blue-600, #1565c0); box-shadow: 0 1px 3px rgba(0,0,0,.12); }
.vpc-refreshing { font-size: 12px; color: var(--blue-500, #1976d2); opacity: 0; transition: opacity .15s; margin-left: auto; display: inline-flex; align-items: center; gap: 4px; }
.vpc-refreshing.show { opacity: 1; }
.vpc-refreshing::before { content: ""; width: 11px; height: 11px; border: 2px solid currentColor; border-right-color: transparent; border-radius: 50%; display: inline-block; animation: vpc-spin .7s linear infinite; }
@keyframes vpc-spin { to { transform: rotate(360deg); } }

/* Filtres */
.vpc-filters { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; margin: 0 2px 14px; }
.vpc-check { display: flex; align-items: center; gap: 6px; font-size: 13px; color: var(--text-muted, #6c7680); cursor: pointer; }

/* KPIs */
.vpc-kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin-bottom: 14px; }
.vpc-kpi { background: var(--card-bg, #fff); border: 1px solid var(--border-color, #e2e6ea); border-radius: 12px; padding: 12px 14px; }
.vpc-kpi .v { font-size: 24px; font-weight: 720; line-height: 1.1; }
.vpc-kpi .l { font-size: 11px; text-transform: uppercase; letter-spacing: .03em; color: var(--text-muted, #6c7680); font-weight: 600; margin-top: 4px; }
.vpc-kpi.po { border-left: 3px solid #1565c0; }
.vpc-kpi.fab { border-left: 3px solid #6a3fb0; }
.vpc-kpi.delivery { border-left: 3px solid #2e7d32; }
.vpc-kpi.danger { border-left: 3px solid #c62828; }
.vpc-kpi.danger .v { color: #c62828; }

/* Toolbar */
.vpc-toolbar { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; margin-bottom: 10px; }
.vpc-search { flex: 1; min-width: 200px; padding: 7px 12px; border: 1px solid var(--border-color, #e2e6ea); border-radius: 8px; background: var(--control-bg, #fff); color: var(--text-color, #1f272e); font-size: 13px; }
.vpc-types { display: inline-flex; gap: 5px; flex-wrap: wrap; }
.vpc-type-toggle { display: inline-flex; align-items: center; gap: 4px; padding: 5px 10px; border-radius: 999px; font-size: 12px; font-weight: 600; cursor: pointer; border: 1px solid transparent; }
.vpc-type-toggle.off { background: transparent !important; color: var(--text-muted, #9aa4ad) !important; border-color: var(--border-color, #e2e6ea); text-decoration: line-through; }
.vpc-count { font-size: 12px; color: var(--text-muted, #9aa4ad); margin-left: auto; }

/* Grille */
.vpc-grid-wrap { overflow-x: auto; border: 1px solid var(--border-color, #e2e6ea); border-radius: 12px; background: var(--card-bg, #fff); }
.vpc-grid { border-collapse: separate; border-spacing: 0; width: 100%; }
.vpc-grid th, .vpc-grid td { border-bottom: 1px solid var(--border-color, #f0f2f4); }
.vpc-corner { position: sticky; left: 0; top: 0; z-index: 4; background: var(--card-bg, #fff); width: 230px; min-width: 230px; text-align: left; padding: 10px 12px; font-size: 11px; text-transform: uppercase; letter-spacing: .03em; color: var(--text-muted, #6c7680); border-right: 1px solid var(--border-color, #e2e6ea); }
.vpc-wk { min-width: 92px; width: 92px; padding: 8px 6px; text-align: center; background: var(--card-bg, #fff); position: sticky; top: 0; z-index: 1; }
.vpc-wk-num { font-size: 12px; font-weight: 700; }
.vpc-wk-date { font-size: 10px; color: var(--text-muted, #9aa4ad); }
.vpc-wk.current { background: rgba(25,118,210,.08); }
.vpc-wk.current .vpc-wk-num { color: var(--blue-600, #1565c0); }
.vpc-wk.past { background: var(--control-bg, #fafbfc); }
/* Mode jour : colonnes plus étroites */
.vpc-grid.day .vpc-wk { min-width: 62px; width: 62px; }
.vpc-grid.day .vpc-cell { min-width: 62px; }

.vpc-rowhead { position: sticky; left: 0; z-index: 2; background: var(--card-bg, #fff); width: 230px; min-width: 230px; text-align: left; padding: 9px 12px; border-right: 1px solid var(--border-color, #e2e6ea); cursor: pointer; vertical-align: top; }
.vpc-rowhead:hover { background: var(--control-bg, #f7f9fa); }
.vpc-rh-top { display: flex; align-items: center; justify-content: space-between; gap: 6px; }
.vpc-rh-name { font-weight: 620; color: var(--blue-600, #1565c0); font-size: 13px; }
.vpc-rh-badges { display: inline-flex; align-items: center; gap: 4px; flex: none; }
.vpc-rh-late { font-size: 10px; font-weight: 700; color: #c62828; white-space: nowrap; }
.vpc-rh-inc { font-size: 10px; font-weight: 700; color: #e65100; background: rgba(245,124,0,.16); padding: 1px 6px; border-radius: 5px; white-space: nowrap; cursor: pointer; }
.vpc-rh-inc:hover { background: rgba(245,124,0,.32); }
.vpc-rh-inc.closed { color: var(--text-muted, #9aa4ad); background: var(--control-bg, #eef1f3); }
.vpc-rh-client { font-size: 11px; color: var(--text-muted, #6c7680); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 206px; }
.vpc-rh-meta { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 3px; }
.vpc-rh-status { font-size: 10px; font-weight: 600; background: rgba(245,124,0,.14); color: #e65100; padding: 1px 6px; border-radius: 5px; max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; cursor: pointer; }
.vpc-rh-status:hover { background: rgba(245,124,0,.28); }
.vpc-rh-status.empty { background: var(--control-bg, #eef1f3); color: var(--text-muted, #9aa4ad); font-weight: 500; font-style: italic; }
.vpc-rh-status.empty:hover { background: var(--border-color, #e2e6ea); color: var(--text-color, #1f272e); }
.vpc-rh-cm { font-size: 10px; color: var(--text-muted, #9aa4ad); }
.vpc-rh-fact { margin-top: 5px; }
.vpc-rh-fact .bar { height: 5px; background: var(--control-bg, #eef1f3); border-radius: 3px; overflow: hidden; }
.vpc-rh-fact .fill { height: 100%; background: #1976d2; }
.vpc-rh-fact .txt { font-size: 10px; color: var(--text-muted, #9aa4ad); }

.vpc-cell { vertical-align: top; padding: 4px; min-width: 92px; }
.vpc-cell.current { background: rgba(25,118,210,.04); }
.vpc-cell.past { background: var(--control-bg, #fafbfc); }
.vpc-chip { display: flex; align-items: center; gap: 3px; width: 100%; margin-bottom: 3px; padding: 3px 6px; border-radius: 6px; font-size: 11px; font-weight: 600; cursor: pointer; border: 1px solid transparent; text-align: left; }
.vpc-chip:last-child { margin-bottom: 0; }
.vpc-chip .ci { flex: none; font-size: 11px; }
.vpc-chip .ct { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.vpc-chip .cd { flex: none; opacity: .8; }
.vpc-chip.done { background: var(--control-bg, #eef1f3) !important; color: var(--text-muted, #9aa4ad) !important; border-color: transparent; }
.vpc-chip.overdue { border-style: solid; }
.vpc-chip:hover { filter: brightness(.96); box-shadow: 0 1px 4px rgba(0,0,0,.12); }

.vpc-more { padding: 12px; text-align: center; }
.vpc-more button { padding: 7px 16px; border: 1px solid var(--border-color, #e2e6ea); background: var(--control-bg, #fff); border-radius: 8px; font-size: 13px; cursor: pointer; color: var(--blue-600, #1565c0); }

/* Modale riche flottante */
.vpc-tip { position: fixed; z-index: 9999; width: 290px; pointer-events: none; background: var(--card-bg, #fff); border: 1px solid var(--border-color, #e2e6ea); border-radius: 10px; box-shadow: 0 10px 40px rgba(0,0,0,.22); overflow: hidden; }
.vpc-tip-head { display: flex; align-items: center; gap: 6px; padding: 8px 12px; font-size: 12px; font-weight: 700; }
.vpc-tip-head .lbl { flex: 1; }
.vpc-tip-state { font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 999px; }
.vpc-tip-state.ok { background: rgba(46,125,50,.16); color: #2e7d32; }
.vpc-tip-state.late { background: rgba(198,40,40,.16); color: #c62828; }
.vpc-tip-state.soon { background: rgba(25,118,210,.14); color: #1565c0; }
.vpc-tip-title { padding: 10px 12px 2px; font-size: 14px; font-weight: 700; color: var(--text-color, #1f272e); }
.vpc-tip-ref { padding: 0 12px 8px; font-size: 11px; color: var(--text-muted, #9aa4ad); }
.vpc-tip-grid { display: grid; grid-template-columns: auto 1fr; gap: 3px 12px; padding: 0 12px 10px; font-size: 12px; }
.vpc-tip-grid span { color: var(--text-muted, #6c7680); }
.vpc-tip-grid b { text-align: right; color: var(--text-color, #1f272e); }
.vpc-tip-foot { padding: 7px 12px; background: var(--control-bg, #f7f9fa); font-size: 10px; color: var(--text-muted, #9aa4ad); border-top: 1px solid var(--border-color, #f0f2f4); }

/* Skeletons */
.vpc-skel { height: 54px; border-radius: 10px; margin-bottom: 8px; background: linear-gradient(90deg, var(--control-bg, #eef1f3), var(--border-color, #e4e8eb), var(--control-bg, #eef1f3)); background-size: 200% 100%; animation: vpc-sh 1.2s infinite; }
@keyframes vpc-sh { to { background-position: -200% 0; } }
</style>

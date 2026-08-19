<template>
	<div :class="{ 'is-mobile': isMobile }">
		<div v-if="open" class="vtc-scrim" @click="close"></div>
		<transition :name="isMobile ? 'vtc-sheet' : 'vtc-drawer'">
			<section v-if="open" class="vtc-detail" role="dialog" aria-modal="true">
				<div class="vtc-detail-grip" v-if="isMobile"></div>
				<div class="vtc-detail-head">
					<span class="vtc-swatch" :style="{ background: (detail && detail.color) || '#1e88e5' }"></span>
					<h2 class="vtc-detail-title">{{ (detail && detail.subject) || title }}</h2>
					<button class="vtc-icon ghost" :aria-label="__('Fermer')" @click="close">
						<svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18" /></svg>
					</button>
				</div>

				<template v-if="loading">
					<div class="vtc-skel"></div>
					<div class="vtc-skel short"></div>
				</template>

				<template v-else-if="detail">
					<p class="vtc-when">{{ whenText }}</p>
					<div class="vtc-tags" v-if="detail.event_type">
						<span class="vtc-tag">{{ detail.event_type }}</span>
					</div>

					<div v-if="eventDescHtml" class="vtc-block">
						<div class="vtc-block-label">{{ __("Note de l'événement") }}</div>
						<div class="vtc-desc" v-html="eventDescHtml"></div>
					</div>
					<div v-if="linkedDescHtml" class="vtc-block">
						<div class="vtc-block-label">{{ __("Description") }} · {{ linkedLabel }}</div>
						<div class="vtc-desc linked" v-html="linkedDescHtml"></div>
					</div>

					<button
						v-if="(detail.vt || detail.fdt) && showStart"
						class="vtc-action primary"
						:disabled="working"
						@click="startTimer"
					>
						<span class="ic">▶</span>
						{{ detail.fdt ? __('Démarrer le chrono (chantier)') : __('Démarrer le chrono (visite)') }}
					</button>

					<a v-if="detail.address_display" class="vtc-action" :href="mapsUrl(detail.address_display)" target="_blank" rel="noopener">
						<span class="ic">📍</span>{{ detail.address_display }}
					</a>
					<a v-if="detail.phone" class="vtc-action" :href="`tel:${detail.phone}`">
						<span class="ic">📞</span>{{ detail.phone }}
					</a>

					<div class="vtc-links" v-if="detail.fdt || detail.vt">
						<button v-if="detail.fdt" class="vtc-chip" @click="openForm('Fiche de travail', detail.fdt)">🔧 {{ __('Fiche de travail') }}</button>
						<button v-if="detail.vt" class="vtc-chip" @click="openForm('Visite Technique', detail.vt)">🔍 {{ __('Visite technique') }}</button>
					</div>

					<button class="vtc-action subtle" @click="openForm('Event', detail.name)">
						{{ __("Ouvrir l'événement") }} →
					</button>
				</template>
			</section>
		</transition>
	</div>
</template>

<script setup>
import { ref, computed, watch, onUnmounted } from "vue";

const props = defineProps({ store: Object });

const DETAIL = "vt_internal.vt_internal.api.event_calendar.get_event_detail";

const open = ref(false);
const loading = ref(false);
const detail = ref(null);
const title = ref("");
const working = ref(false);
const currentTask = ref(null); // état de la journée (via timesheet_html_block)
const currentFdt = ref(null); // FDT actuellement chronométrée (si activité en cours)

// "Démarrer le chrono" : masqué quand on fait DÉJÀ cette activité.
const showStart = computed(() => {
	const ct = currentTask.value;
	if (ct === "Day finished") return false;
	const d = detail.value || {};
	if (d.fdt) {
		// Chantier : masquer seulement si on chronomètre déjà CE chantier.
		return !(ct === "Chantier" && currentFdt.value === d.fdt);
	}
	// Visite : masquer si on est déjà en visite technique.
	return ct !== "Visite technique";
});

const isMobile = ref(window.matchMedia("(max-width: 768px)").matches);
const mq = window.matchMedia("(max-width: 768px)");
const onMq = (e) => (isMobile.value = e.matches);
mq.addEventListener("change", onMq);
onUnmounted(() => mq.removeEventListener("change", onMq));

// Helpers
const cap = (s) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : s);
const mapsUrl = (a) => `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(a)}`;
const parseDt = (s) => (s ? new Date(s.replace(" ", "T")) : null);
const sameDay = (a, b) => a.toDateString() === b.toDateString();

const whenText = computed(() => {
	const d = detail.value;
	if (!d) return "";
	const s = parseDt(d.starts_on);
	const e = parseDt(d.ends_on);
	if (!s) return "";
	const dateF = new Intl.DateTimeFormat("fr-FR", { weekday: "long", day: "numeric", month: "long" });
	const timeF = new Intl.DateTimeFormat("fr-FR", { hour: "2-digit", minute: "2-digit" });
	if (d.all_day) return cap(dateF.format(s));
	let out = `${cap(dateF.format(s))} · ${timeF.format(s)}`;
	if (e) out += sameDay(s, e) ? ` – ${timeF.format(e)}` : ` → ${cap(dateF.format(e))} ${timeF.format(e)}`;
	return out;
});
// Descriptions en HTML (rich text), rendues telles quelles comme dans le
// formulaire Event. Renvoie "" si le contenu est vide (ex: "<div><br></div>").
const cleanHtml = (html) => {
	if (!html) return "";
	const plain = html.replace(/<[^>]*>/g, "").replace(/&nbsp;/g, " ").trim();
	return plain ? html : "";
};
const eventDescHtml = computed(() => cleanHtml(detail.value && detail.value.event_description));
const linkedDescHtml = computed(() => cleanHtml(detail.value && detail.value.linked_description));
const linkedLabel = computed(() => {
	const d = detail.value || {};
	return d.fdt ? __("Fiche de travail") : d.vt ? __("Visite technique") : __("Lié");
});

// Ouverture pilotée par le store (store.eventId + store.nonce)
watch(
	() => props.store && props.store.nonce,
	() => {
		const id = props.store && props.store.eventId;
		if (!id) return;
		title.value = (props.store && props.store.title) || "";
		open.value = true;
		loading.value = true;
		detail.value = null;
		currentTask.value = null;
		currentFdt.value = null;
		frappe
			.xcall(DETAIL, { name: id })
			.then((d) => {
				detail.value = d;
			})
			.catch(() => {
				frappe.show_alert({ message: __("Impossible de charger l'événement"), indicator: "red" });
				open.value = false;
			})
			.finally(() => (loading.value = false));
		// État de la journée (pour afficher les bons boutons pause / terminer…)
		frappe
			.call({ method: "timesheet_html_block" })
			.then((r) => {
				const m = r.message || {};
				currentTask.value = m.current_task || null;
				currentFdt.value = m.fiche_de_travail || null;
			})
			.catch(() => {});
	}
);

function close() {
	open.value = false;
}
function openForm(dt, name) {
	close();
	frappe.set_route("Form", dt, name);
}
// Enveloppe timesheet_post_api (même logique que timer_api de la Fiche de travail).
function timerApi(args, message) {
	working.value = true;
	return frappe
		.call({ method: "timesheet_post_api", args })
		.then(() => {
			frappe.show_alert({ message, indicator: "green" }, 5);
			window.location.reload(); // comme timer_api de la Fiche de travail
		})
		.catch(() => {
			frappe.show_alert({ message: __("Une erreur est survenue"), indicator: "red" }, 5);
			working.value = false;
		});
}

function startTimer() {
	const d = detail.value;
	if (!d) return;
	const args = d.fdt
		? { action: "start_construction", activity_type: "Chantier", fiche_de_travail: d.fdt }
		: { action: "start_construction", activity_type: "Visite technique" };
	timerApi(args, __("Tâche commencée"));
}
</script>

<style scoped>
.vtc-scrim { position: fixed; inset: 0; background: rgba(12, 18, 25, 0.32); z-index: 1029; backdrop-filter: blur(1px); }
.vtc-detail {
	position: fixed;
	z-index: 1030;
	background: var(--fg-color, #fff);
	display: flex;
	flex-direction: column;
	gap: 12px;
	padding: 20px;
	overflow-y: auto;
	top: 0; left: 0; bottom: 0;
	width: min(420px, 94vw);
	border-right: 1px solid var(--border-color, #e2e6ea);
	box-shadow: 10px 0 40px rgba(0, 0, 0, 0.16);
	font-family: var(--font-stack, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif);
}
.is-mobile .vtc-detail {
	top: auto; left: 0; right: 0; bottom: 0;
	width: auto;
	max-height: 82vh;
	border-right: none;
	border-radius: 20px 20px 0 0;
	box-shadow: 0 -10px 40px rgba(0, 0, 0, 0.2);
	padding-bottom: max(20px, env(safe-area-inset-bottom));
}
.vtc-detail-grip { width: 40px; height: 4px; border-radius: 2px; background: var(--border-color, #d1d8dd); margin: -6px auto 4px; }
.vtc-detail-head { display: flex; align-items: flex-start; gap: 10px; }
.vtc-swatch { width: 14px; height: 14px; border-radius: 4px; margin-top: 5px; flex: none; }
.vtc-detail-title { margin: 0; font-size: 20px; font-weight: 680; line-height: 1.25; color: var(--text-color, #1f272e); flex: 1; }
.vtc-icon {
	display: inline-flex; align-items: center; justify-content: center;
	width: 34px; height: 34px; border-radius: 9px; border: 1px solid transparent;
	background: transparent; color: var(--text-color, #1f272e); cursor: pointer;
}
.vtc-icon svg { width: 20px; height: 20px; fill: none; stroke: currentColor; stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
.vtc-icon:hover { background: var(--control-bg, #f4f5f6); }
.vtc-when { margin: 0; font-size: 14px; color: var(--text-muted, #6c7680); text-transform: capitalize; }
.vtc-tags { display: flex; flex-wrap: wrap; gap: 6px; }
.vtc-tag { font-size: 12px; font-weight: 600; padding: 3px 10px; border-radius: 999px; background: var(--control-bg, #eef1f3); color: var(--text-muted, #6c7680); }
.vtc-block { display: flex; flex-direction: column; gap: 5px; }
.vtc-block-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; color: var(--text-muted, #6c7680); font-weight: 600; }
.vtc-desc { margin: 0; font-size: 13.5px; line-height: 1.5; color: var(--text-color, #1f272e); background: var(--control-bg, #f6f7f8); border-radius: 10px; padding: 10px 12px; max-height: 180px; overflow-y: auto; }
.vtc-desc.linked { background: color-mix(in srgb, #1e88e5 7%, var(--control-bg, #f6f7f8)); border-left: 3px solid #1e88e5; border-radius: 4px 10px 10px 4px; }
.vtc-desc :deep(p) { margin: 0 0 6px; }
.vtc-desc :deep(p:last-child) { margin-bottom: 0; }
.vtc-desc :deep(img) { max-width: 100%; height: auto; border-radius: 6px; }
.vtc-desc :deep(ul), .vtc-desc :deep(ol) { margin: 4px 0; padding-left: 18px; }
.vtc-desc :deep(a) { color: #1e88e5; }
.vtc-action {
	display: flex; align-items: center; gap: 10px; width: 100%;
	padding: 12px 14px; border-radius: 11px; font-size: 14px; font-weight: 560;
	text-decoration: none; cursor: pointer;
	border: 1px solid var(--border-color, #e2e6ea); background: var(--card-bg, #fff);
	color: var(--text-color, #1f272e); text-align: left; transition: background 0.12s;
}
.vtc-action .ic { flex: none; font-size: 15px; }
.vtc-action:hover { background: var(--control-bg, #f4f5f6); }
.vtc-action.primary { background: #1e88e5; border-color: #1e88e5; color: #fff; justify-content: center; font-weight: 640; }
.vtc-action.primary:disabled { opacity: 0.6; cursor: default; }
.vtc-action.subtle { justify-content: center; color: var(--text-muted, #6c7680); border-style: dashed; }
.vtc-links { display: flex; flex-wrap: wrap; gap: 8px; }
.vtc-chip {
	flex: 1; min-width: 130px; padding: 10px 12px; border-radius: 10px;
	border: 1px solid var(--border-color, #e2e6ea); background: var(--card-bg, #fff);
	color: var(--text-color, #1f272e); font-size: 13px; font-weight: 560; cursor: pointer;
}
.vtc-chip:hover { background: var(--control-bg, #f4f5f6); }
.vtc-skel { height: 16px; border-radius: 6px; background: linear-gradient(90deg, var(--control-bg, #eef1f3), var(--border-color, #e2e6ea), var(--control-bg, #eef1f3)); background-size: 200% 100%; animation: vtc-shimmer 1.2s infinite; }
.vtc-skel.short { width: 60%; }
@keyframes vtc-shimmer { to { background-position: -200% 0; } }
.vtc-drawer-enter-active, .vtc-drawer-leave-active { transition: transform 0.24s ease; }
.vtc-drawer-enter-from, .vtc-drawer-leave-to { transform: translateX(-100%); }
.vtc-sheet-enter-active, .vtc-sheet-leave-active { transition: transform 0.26s ease; }
.vtc-sheet-enter-from, .vtc-sheet-leave-to { transform: translateY(100%); }
@media (prefers-reduced-motion: reduce) {
	.vtc-drawer-enter-active, .vtc-drawer-leave-active, .vtc-sheet-enter-active, .vtc-sheet-leave-active { transition: none; }
	.vtc-skel { animation: none; }
}
</style>

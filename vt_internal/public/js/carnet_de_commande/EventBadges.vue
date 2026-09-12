<template>
	<div class="vcc-events" v-if="events.length">
		<button
			v-for="ev in events"
			:key="ev.name"
			class="vcc-ev"
			:class="[ev.kind, { past: ev.past }]"
			:style="badgeStyle(ev)"
			:data-tip="evTip(ev)"
			@click.stop="$emit('open', ev.name)"
		>
			<span class="ic">{{ meta(ev).icon }}</span>
			<span>{{ meta(ev).label }}</span>
			<span v-if="ev.starts_on" class="dt">{{ fmtDateShort(ev.starts_on) }}</span>
		</button>
	</div>
	<span v-else class="vcc-muted">—</span>
</template>

<script>
import { EVENT_KIND_META, fmtDateShort } from "./helpers.js";

export default {
	name: "EventBadges",
	props: { events: { type: Array, default: () => [] } },
	emits: ["open"],
	methods: {
		fmtDateShort,
		meta(ev) {
			return EVENT_KIND_META[ev.kind] || EVENT_KIND_META.event;
		},
		badgeStyle(ev) {
			const m = this.meta(ev);
			return { background: m.color, color: "#fff" };
		},
		evTip(ev) {
			const m = this.meta(ev);
			return ev.subject ? `${m.label} — ${ev.subject}` : m.label;
		},
	},
};
</script>

<style scoped>
.vcc-events { display: flex; flex-wrap: wrap; gap: 4px; min-width: 140px; }
.vcc-ev {
	display: inline-flex; align-items: center; gap: 4px;
	border: none; border-radius: 999px; padding: 2px 8px;
	font-size: 11px; font-weight: 700; cursor: pointer; font-family: inherit;
}
.vcc-ev.past { opacity: .55; }
.vcc-ev:hover { filter: brightness(.94); }
.vcc-muted { color: var(--text-muted, #9aa4ad); }
</style>

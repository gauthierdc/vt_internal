<template>
	<div class="ds">
		<button class="ds-btn" :class="{ on: !!modelValue }" @click.stop="open = !open">
			<span v-if="icon" class="ds-ic">{{ icon }}</span>
			<span class="ds-lbl">{{ currentLabel }}</span>
			<span class="ds-caret">▾</span>
		</button>
		<template v-if="open">
			<div class="ds-backdrop" @click="open = false"></div>
			<div class="ds-pop">
				<button class="ds-opt all" :class="{ sel: !modelValue }" @click="pick('')">{{ allLabel }}</button>
				<button
					v-for="o in options" :key="o.value"
					class="ds-opt" :class="{ sel: o.value === modelValue }"
					@click="pick(o.value)"
				>{{ o.label }}</button>
				<div v-if="!options.length" class="ds-empty">{{ emptyLabel }}</div>
			</div>
		</template>
	</div>
</template>

<script>
// Menu déroulant simple mono-sélection, stylé comme le reste de la vue
// (bouton + popup), pour remplacer les <select> natifs du navigateur.
export default {
	name: "DropSelect",
	props: {
		modelValue: { default: "" },
		options: { type: Array, default: () => [] }, // [{ value, label }]
		allLabel: { type: String, default: "Tous" },
		icon: { type: String, default: "" },
		emptyLabel: { type: String, default: "—" },
	},
	emits: ["update:modelValue"],
	data() {
		return { open: false };
	},
	computed: {
		currentLabel() {
			if (!this.modelValue) return this.allLabel;
			const o = this.options.find((x) => x.value === this.modelValue);
			return o ? o.label : this.modelValue;
		},
	},
	methods: {
		pick(v) {
			this.open = false;
			this.$emit("update:modelValue", v);
		},
	},
};
</script>

<style scoped>
.ds { position: relative; }
.ds-btn { display: inline-flex; align-items: center; gap: 6px; padding: 7px 12px; border: 1px solid var(--border-color, #e2e6ea); border-radius: 8px; background: var(--control-bg, #fff); color: var(--text-color, #1f272e); font-size: 13px; cursor: pointer; max-width: 220px; }
.ds-btn.on { border-color: var(--blue-400, #64b5f6); color: var(--blue-600, #1565c0); font-weight: 560; }
.ds-lbl { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.ds-caret { color: var(--text-muted, #9aa4ad); font-size: 10px; margin-left: 2px; }
.ds-backdrop { position: fixed; inset: 0; z-index: 20; }
.ds-pop { position: absolute; top: calc(100% + 4px); left: 0; z-index: 21; min-width: 200px; max-height: 320px; overflow-y: auto; background: var(--card-bg, #fff); border: 1px solid var(--border-color, #e2e6ea); border-radius: 10px; box-shadow: 0 8px 30px rgba(0, 0, 0, .16); padding: 6px; }
.ds-opt { display: block; width: 100%; text-align: left; padding: 7px 10px; border: none; background: transparent; border-radius: 7px; font-size: 13px; cursor: pointer; color: var(--text-color, #1f272e); }
.ds-opt:hover { background: var(--control-bg, #f4f5f6); }
.ds-opt.sel { color: var(--blue-600, #1565c0); font-weight: 600; }
.ds-opt.all { color: var(--blue-600, #1565c0); border-bottom: 1px solid var(--border-color, #eef1f3); border-radius: 0; margin-bottom: 4px; }
.ds-empty { padding: 12px; font-size: 12px; color: var(--text-muted, #9aa4ad); text-align: center; }
</style>

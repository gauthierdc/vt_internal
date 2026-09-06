import assert from "node:assert/strict";
import test from "node:test";
import {
	DESK_MOBILE_MAX_PX,
	installDeskMobileScrollGuard,
	isDeskOverlayOpen,
	isDocumentOverflowLocked,
	isMobileDeskViewport,
	restoreDeskPageScroll,
	shouldRestoreDeskPageScroll,
} from "./vt_desk_mobile_scroll.js";

test("isMobileDeskViewport matches the desk phone breakpoint", () => {
	assert.equal(isMobileDeskViewport(375), true);
	assert.equal(isMobileDeskViewport(DESK_MOBILE_MAX_PX - 1), true);
	assert.equal(isMobileDeskViewport(DESK_MOBILE_MAX_PX), false);
	assert.equal(isMobileDeskViewport(1280), false);
	assert.equal(isMobileDeskViewport("nope"), false);
});

test("shouldRestoreDeskPageScroll unlocks only a stuck lock without an open overlay", () => {
	assert.equal(
		shouldRestoreDeskPageScroll({
			mobile: true,
			overlayOpen: false,
			overflowLocked: true,
			force: false,
		}),
		true
	);
	assert.equal(
		shouldRestoreDeskPageScroll({
			mobile: true,
			overlayOpen: true,
			overflowLocked: true,
			force: false,
		}),
		false
	);
	assert.equal(
		shouldRestoreDeskPageScroll({
			mobile: false,
			overlayOpen: false,
			overflowLocked: true,
			force: false,
		}),
		false
	);
	assert.equal(
		shouldRestoreDeskPageScroll({
			mobile: true,
			overlayOpen: true,
			overflowLocked: true,
			force: true,
		}),
		true
	);
	assert.equal(
		shouldRestoreDeskPageScroll({
			mobile: true,
			overlayOpen: false,
			overflowLocked: false,
			force: true,
		}),
		false
	);
});

function lockedDoc({ overlayOpened = false, closeSidebar = false, modalOpen = false } = {}) {
	const nodes = [];
	if (overlayOpened) {
		nodes.push({ sel: ".overlay-sidebar.opened", el: { classList: { contains: () => true } } });
	}
	if (closeSidebar) {
		nodes.push({ sel: ".close-sidebar", el: { classList: {} } });
	}
	return {
		documentElement: { style: { overflowY: "hidden" } },
		body: {
			style: { overflow: "hidden", overflowY: "hidden" },
			classList: {
				contains(name) {
					return modalOpen && name === "modal-open";
				},
			},
		},
		querySelector(sel) {
			const hit = nodes.find((n) => n.sel === sel);
			return hit ? hit.el : null;
		},
	};
}

test("isDeskOverlayOpen sees list overlay, backdrop and modal-open", () => {
	assert.equal(isDeskOverlayOpen(lockedDoc()), false);
	assert.equal(isDeskOverlayOpen(lockedDoc({ overlayOpened: true })), true);
	assert.equal(isDeskOverlayOpen(lockedDoc({ closeSidebar: true })), true);
	assert.equal(isDeskOverlayOpen(lockedDoc({ modalOpen: true })), true);
});

test("restoreDeskPageScroll clears a stuck lock when the overlay is gone", () => {
	const root = lockedDoc();
	assert.equal(isDocumentOverflowLocked(root), true);
	const out = restoreDeskPageScroll(root, { width: 390 });
	assert.equal(out.restored, true);
	assert.equal(out.overlayOpen, false);
	assert.equal(root.documentElement.style.overflowY, "");
	assert.equal(root.body.style.overflow, "");
});

test("restoreDeskPageScroll keeps the lock while the list overlay is open", () => {
	const root = lockedDoc({ overlayOpened: true });
	const out = restoreDeskPageScroll(root, { width: 390 });
	assert.equal(out.restored, false);
	assert.equal(out.overlayOpen, true);
	assert.equal(root.documentElement.style.overflowY, "hidden");
});

test("restoreDeskPageScroll does not touch desktop unless forced", () => {
	const root = lockedDoc();
	const skipped = restoreDeskPageScroll(root, { width: 1280 });
	assert.equal(skipped.restored, false);
	assert.equal(root.documentElement.style.overflowY, "hidden");

	const forced = restoreDeskPageScroll(root, { width: 1280, force: true });
	assert.equal(forced.restored, true);
	assert.equal(root.documentElement.style.overflowY, "");
});

test("installDeskMobileScrollGuard restores on close_sidebar and skips open overlay", () => {
	const root = lockedDoc({ overlayOpened: true });
	const proto = {
		close_sidebar() {
			return "closed";
		},
	};
	const { tick } = installDeskMobileScrollGuard({
		doc: root,
		pageProto: proto,
		getWidth: () => 390,
	});
	assert.equal(proto.__vt_mobile_scroll, true);
	assert.equal(tick(false).restored, false);

	root.querySelector = () => null;
	assert.equal(proto.close_sidebar(), "closed");
	assert.equal(root.documentElement.style.overflowY, "");
});

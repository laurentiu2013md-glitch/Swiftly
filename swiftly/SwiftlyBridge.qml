// SPDX-License-Identifier: GPL-3.0-only
import QtQuick
import Quickshell
import Quickshell.Io

Scope {
    id: bridge
    property alias config: adapter
    property var indices: ({})
    signal settingsRequested()

    FileView {
        id: file
        path: (Quickshell.env("XDG_CONFIG_HOME") || Quickshell.env("HOME") + "/.config")
              + "/swiftly/config.json"
        watchChanges: true
        onFileChanged: reload()
        atomicWrites: true
        onLoadFailed: error => console.error("Swiftly config load failed:", error)
        JsonAdapter {
            id: adapter
            property int schemaVersion: 1
            property var theme: ({})
            property var interaction: ({})
            property var gestures: ({})
            property var stacks: []
        }
    }

    function stackFor(stackId) {
        return adapter.stacks.find(s => s.id === stackId);
    }
    function indexFor(stackId) {
        const s = stackFor(stackId);
        if (!s || !s.widgets || s.widgets.length === 0) return 0;
        const i = Object.prototype.hasOwnProperty.call(indices, stackId)
                ? indices[stackId] : s.initialIndex;
        return Math.max(0, Math.min(Math.floor(Number(i) || 0), s.widgets.length - 1));
    }
    function step(stackId, delta) {
        const s = stackFor(stackId);
        if (!s || !s.enabled || !s.widgets || s.widgets.length === 0) return;
        const n = s.widgets.length;
        const i = indexFor(stackId) + delta;
        const next = adapter.interaction.wrap ? (i % n + n) % n : Math.max(0, Math.min(i, n - 1));
        // A null prototype also makes valid IDs such as __proto__ ordinary keys.
        const copy = Object.assign(Object.create(null), indices);
        copy[stackId] = next;
        indices = copy;
    }
    // Call only from the settings GUI's explicit Save action. Reassign whole
    // var objects/arrays before calling; mutating a nested member emits no signal.
    function saveConfig() { file.writeAdapter(); }

    IpcHandler {
        target: "swiftly"
        function next(stackId: string): void { bridge.step(stackId, 1); }
        function previous(stackId: string): void { bridge.step(stackId, -1); }
        function index(stackId: string): int { return bridge.indexFor(stackId); }
        function settings(): void { bridge.settingsRequested(); }
        function swipe(direction: string, fingers: int): void {
            const g = adapter.gestures;
            // Stale compositor bindings are ignored until the helper is rerun.
            if (!g.enabled || g.fingers !== fingers) return;
            if (direction === g.nextDirection) bridge.step(g.targetStack, 1);
            else if (direction === g.previousDirection) bridge.step(g.targetStack, -1);
        }
    }
}

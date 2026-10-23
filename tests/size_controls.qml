import QtQuick
import Quickshell
import QtTest
import "gui"
ShellRoot {
    id: root
    property int phase: 0
    property int ticks: 0
    property string before: ""
    SwiftlyBridge { id: bridge }
    SwiftlySettings { id: settings; bridge: bridge }
    FloatingWindow {
        id: cardWindow
        visible: true
        implicitWidth: bridge.config.stacks.length ? bridge.config.stacks[0].size.width : 400
        implicitHeight: bridge.config.stacks.length ? bridge.config.stacks[0].size.height : 240
        TestCase { id: input; name: "ResizeControls"; when: false }
    }
    function check(ok, message) {
        if (!ok) { console.error("FAIL " + message); Qt.exit(1); }
    }
    function enterSize(name, value) {
        const spin = input.findChild(settings.contentItem, name);
        check(!!spin, "size control exists: " + name);
        spin.contentItem.forceActiveFocus();
        input.keyClick(Qt.Key_A, Qt.ControlModifier);
        for (const char of String(value)) input.keyClick(char);
        input.keyClick(Qt.Key_Return);
    }
    Timer {
        interval: 150; repeat: true; running: true
        onTriggered: {
            root.ticks++;
            if (root.ticks > 60) { console.error("FAIL timeout"); Qt.exit(1); return; }
            if (!bridge.config.stacks.length) return;
            if (root.phase === 0) {
                settings.visible = true;
                root.before = JSON.stringify(bridge.config.stacks);
                root.phase++;
            } else if (root.phase === 1) {
                root.check(settings.draftWidth === 400 && settings.draftHeight === 240, "loads saved dimensions");
                root.enterSize("widgetWidth", 640);
                root.enterSize("widgetHeight", 320);
                root.enterSize("widgetX", 24);
                root.enterSize("widgetY", 60);
                settings.draftAnchor = "bottom-left";
                root.check(settings.draftWidth === 640 && settings.draftHeight === 320, "typed values update drafts");
                root.check(JSON.stringify(bridge.config.stacks) === root.before, "draft edits do not resize before Save");
                const save = input.findChild(settings.contentItem, "saveAnimation");
                input.mouseClick(save);
                root.phase++;
            } else if (root.phase === 2) {
                if (settings.status !== "Saved") return;
                root.check(bridge.config.stacks[0].size.width === 640 && bridge.config.stacks[0].size.height === 320, "Save updates stack geometry");
                root.check(bridge.config.stacks[0].position.anchor === "bottom-left"
                    && bridge.config.stacks[0].position.x === 24 && bridge.config.stacks[0].position.y === 60,
                    "Save updates corner and offsets");
                root.check(cardWindow.implicitWidth === 640 && cardWindow.implicitHeight === 320, "live size binding follows saved dimensions");
                const current = JSON.stringify(bridge.config.stacks);
                root.check(!bridge.saveSettings("fade", 220, settings.draftStackId, 0, 320), "reject zero width");
                root.check(JSON.stringify(bridge.config.stacks) === current, "invalid size leaves config untouched");
                root.check(!bridge.saveSettings("fade", 220, settings.draftStackId, 640, 320,
                    {anchor: "bottom-left", x: -1, y: 60}), "reject negative offsets");
                root.check(JSON.stringify(bridge.config.stacks) === current, "invalid location leaves config untouched");
                settings.close(); settings.visible = true;
                root.check(settings.draftWidth === 640 && settings.draftHeight === 320, "reopen loads saved dimensions");
                root.check(settings.draftAnchor === "bottom-left" && settings.draftX === 24 && settings.draftY === 60,
                    "reopen loads saved location");
                settings.draftWidth = 700;
                settings.close(); settings.visible = true;
                root.check(settings.draftWidth === 640, "closing without Save discards draft");
                const save = input.findChild(settings.contentItem, "saveAnimation");
                root.check(save.y + save.height <= save.parent.height + 1, "Save remains within layout");
                console.log("PASS: typed dimensions, Save persistence, live resize, validation and discard");
                Qt.quit();
            }
        }
    }
}

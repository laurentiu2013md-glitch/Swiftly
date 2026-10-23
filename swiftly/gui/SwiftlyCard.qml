pragma ComponentBehavior: Bound
// SPDX-License-Identifier: GPL-3.0-only
import QtQuick
import QtQuick.Controls

Rectangle {
    id: card
    required property var bridge
    required property var stack
    readonly property var widgets: stack.widgets || []
    readonly property int selectedIndex: bridge.indexFor(stack.id)
    readonly property string preset: bridge.animationPreset
    readonly property int duration: preset === "none" ? 0 : bridge.animationDuration
    readonly property var theme: bridge.config.theme
    readonly property real switchZoneStart: width * 0.9
    readonly property alias switchArea: switching
    property alias widgetRepeater: faces
    signal settingsRequested()
    implicitWidth: 340
    implicitHeight: 200
    color: theme.background || "#E6222632"
    radius: Math.max(0, Math.min(Number(stack.cornerRadius) || 0, width / 2, height / 2))
    border.color: theme.border || "#33FFFFFF"
    border.width: 1
    clip: true

    function inSwitchZone(x) { return width > 0 && x >= switchZoneStart && x < width; }
    function scrollAt(x, delta) {
        if (!inSwitchZone(x) || !bridge.config.interaction.scrollEnabled || delta === 0) return false;
        bridge.step(stack.id, (delta < 0 ? 1 : -1) * (bridge.config.interaction.scrollInvert ? -1 : 1));
        return true;
    }
    function swipeFrom(x, dx, dy) {
        if (!inSwitchZone(x) || !bridge.config.interaction.swipeEnabled) return false;
        const delta = Math.abs(dx) >= Math.abs(dy) ? dx : dy;
        const threshold = Math.max(1, Number(bridge.config.interaction.swipeThreshold) || 48);
        if (Math.abs(delta) < threshold) return false;
        bridge.step(stack.id, delta < 0 ? 1 : -1);
        return true;
    }

    Item {
        anchors.fill: parent
        anchors.margins: 22
        anchors.rightMargin: card.width * 0.1 + 10
        Repeater {
            id: faces
            model: card.widgets
            delegate: WidgetFace {
                required property int index
                required property var modelData
                widget: modelData
                theme: card.theme
                width: parent.width
                height: parent.height
                enabled: index === card.selectedIndex
                visible: opacity > 0
                opacity: index === card.selectedIndex ? 1 : 0
                x: card.preset === "slide" && index !== card.selectedIndex
                        ? (index < card.selectedIndex ? -24 : 24) : 0
                scale: card.preset === "zoom" && index !== card.selectedIndex ? 0.9 : 1
                Behavior on opacity { NumberAnimation { duration: card.duration; easing.type: Easing.OutCubic } }
                Behavior on x { NumberAnimation { duration: card.duration; easing.type: Easing.OutCubic } }
                Behavior on scale { NumberAnimation { duration: card.duration; easing.type: Easing.OutCubic } }
            }
        }
        Label {
            anchors.centerIn: parent
            visible: card.widgets.length === 0
            text: "No widgets"
            color: card.theme.muted || "#FFAFB7CC"
        }
    }

    // Only this physical strip accepts local switching input. A swipe may leave
    // the strip after starting here; it is evaluated against its starting point.
    MouseArea {
        id: switching
        objectName: "switchingStrip"
        x: card.switchZoneStart
        width: card.width - x
        height: card.height
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton
        preventStealing: true
        property real startX: 0
        property real startY: 0
        onEntered: card.bridge.pointerStackId = card.stack.id
        onExited: { if (card.bridge.pointerStackId === card.stack.id) card.bridge.pointerStackId = ""; }
        onPressed: mouse => { startX = mouse.x; startY = mouse.y; }
        onReleased: mouse => card.swipeFrom(x + startX, mouse.x - startX, mouse.y - startY)
        onWheel: wheel => {
            const delta = wheel.angleDelta.y || wheel.angleDelta.x || wheel.pixelDelta.y || wheel.pixelDelta.x;
            if (!wheelCooldown.running && card.scrollAt(x + wheel.x, delta)) wheelCooldown.start();
            wheel.accepted = !!card.bridge.config.interaction.scrollEnabled;
        }
        Timer { id: wheelCooldown; interval: 140 }
        Rectangle {
            anchors.fill: parent
            radius: card.radius
            color: card.theme.accent || "#FFAEC6FF"
            opacity: switching.containsMouse ? 0.16 : 0.035
            Behavior on opacity { NumberAnimation { duration: 120 } }
        }
        Column {
            anchors.centerIn: parent
            spacing: 6
            Repeater {
                model: card.widgets.length
                Rectangle {
                    required property int index
                    width: 4
                    height: index === card.selectedIndex ? 16 : 4
                    radius: 2
                    color: card.theme.accent || "#FFAEC6FF"
                    opacity: index === card.selectedIndex ? 1 : 0.35
                }
            }
        }
    }
    Component.onDestruction: {
        if (bridge.pointerStackId === stack.id) bridge.pointerStackId = "";
    }
    ToolButton {
        anchors.left: parent.left
        anchors.bottom: parent.bottom
        anchors.margins: 4
        text: "⚙"
        font.pixelSize: 15
        Accessible.name: "Animation settings"
        onClicked: card.settingsRequested()
    }
}

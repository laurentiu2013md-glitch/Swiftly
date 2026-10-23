// SPDX-License-Identifier: GPL-3.0-only
import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Window {
    id: settings
    required property var bridge
    property string draftPreset: "fade"
    property int draftDuration: 220
    property string status: ""
    property bool saving: false
    title: "Swiftly · Animation"
    width: 420
    height: 350
    minimumWidth: 380
    minimumHeight: 330
    visible: false
    color: bridge.config.theme.background || "#FF222632"
    onVisibleChanged: {
        if (visible) {
            draftPreset = bridge.animationPreset;
            draftDuration = bridge.animationDuration;
            status = "";
            requestActivate();
        }
    }
    function apply() {
        status = "Saving…";
        saving = true;
        if (!bridge.saveAnimation(draftPreset, draftDuration)) {
            status = "Choose an animation preset.";
            saving = false;
        }
    }
    Connections {
        target: settings.bridge
        function onConfigSaved() { settings.status = "Saved"; settings.saving = false; }
        function onConfigSaveFailed(message) { settings.status = message; settings.saving = false; }
    }
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 24
        spacing: 14
        Label { text: "Widget animation"; font.pixelSize: 24; font.bold: true; color: settings.bridge.config.theme.foreground || "white" }
        Label { text: "Animation preset"; color: settings.bridge.config.theme.foreground || "white" }
        ComboBox {
            id: presetBox
            objectName: "animationPreset"
            Layout.fillWidth: true
            model: ["Fade", "Slide", "Zoom", "None"]
            currentIndex: settings.bridge.animationPresets.indexOf(settings.draftPreset)
            onActivated: index => settings.draftPreset = settings.bridge.animationPresets[index]
            Accessible.name: "Animation preset"
        }
        RowLayout {
            Label { text: "Duration (ms)"; color: settings.bridge.config.theme.foreground || "white" }
            Item { Layout.fillWidth: true }
            SpinBox {
                objectName: "animationDuration"
                from: 0
                to: 2000
                stepSize: 20
                value: settings.draftDuration
                enabled: settings.draftPreset !== "none"
                onValueModified: settings.draftDuration = value
                Accessible.name: "Animation duration in milliseconds"
            }
        }
        Label {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: "Scroll or start a swipe in the rightmost 10% of a card to switch widgets."
            color: settings.bridge.config.theme.muted || "#FFAFB7CC"
        }
        Label { text: settings.status; color: settings.bridge.config.theme.accent || "#FFAEC6FF" }
        RowLayout {
            Item { Layout.fillWidth: true }
            Button { text: "Close"; onClicked: settings.close() }
            Button { objectName: "saveAnimation"; text: "Save"; enabled: !settings.saving; onClicked: settings.apply() }
        }
    }
}

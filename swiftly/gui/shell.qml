pragma ComponentBehavior: Bound
// SPDX-License-Identifier: GPL-3.0-only
import QtQuick
import Quickshell

ShellRoot {
    id: shell
    SwiftlyBridge {
        id: runtimeBridge
        requirePointerZone: true
        widgetsReady: widgetPanels.instances.length === config.stacks.filter(s => s.enabled).length
                && widgetPanels.instances.every(p => p.widgetView.widgetRepeater.count === (p.modelData.widgets || []).length)
        onSettingsRequested: settings.visible = true
    }
    SwiftlySettings { id: settings; bridge: runtimeBridge }
    Variants {
        id: widgetPanels
        model: runtimeBridge.config.stacks.filter(stack => stack.enabled)
        delegate: PanelWindow {
            id: panel
            required property var modelData
            readonly property alias widgetView: widgetCard
            readonly property var position: modelData.position || {}
            readonly property string anchor: position.anchor || "top-right"
            screen: Quickshell.screens.find(screen => screen.name === modelData.monitor) || Quickshell.screens[0]
            implicitWidth: Math.max(120, Number((modelData.size || {}).width) || 340)
            implicitHeight: Math.max(100, Number((modelData.size || {}).height) || 144)
            color: "transparent"
            exclusionMode: ExclusionMode.Normal
            exclusiveZone: 0
            // Transparent/read-only widget content must not block the desktop.
            mask: Region { item: widgetCard.switchArea }
            anchors {
                top: panel.anchor.startsWith("top")
                bottom: panel.anchor.startsWith("bottom")
                left: panel.anchor.endsWith("left")
                right: panel.anchor.endsWith("right")
            }
            margins {
                top: Math.max(0, Number(panel.position.y) || 0)
                bottom: Math.max(0, Number(panel.position.y) || 0)
                left: Math.max(0, Number(panel.position.x) || 0)
                right: Math.max(0, Number(panel.position.x) || 0)
            }
            SwiftlyCard {
                id: widgetCard
                anchors.fill: parent
                bridge: runtimeBridge
                stack: panel.modelData
                onSettingsRequested: settings.visible = true
            }
        }
    }
}

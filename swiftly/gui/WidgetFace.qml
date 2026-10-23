// SPDX-License-Identifier: GPL-3.0-only
import QtQuick
import QtQuick.Controls
import Quickshell.Services.Mpris

Item {
    id: face
    required property var widget
    required property var theme
    property date now: new Date()
    readonly property var player: Mpris.players.values.length ? Mpris.players.values[0] : null
    Timer { interval: 1000; running: face.visible; repeat: true; onTriggered: face.now = new Date() }
    Column {
        anchors.verticalCenter: parent.verticalCenter
        width: parent.width
        spacing: 8
        Label {
            width: parent.width
            color: face.theme.muted || "#FFAFB7CC"
            text: face.widget.type === "clock" ? "TODAY" : face.widget.type === "calendar" ? "CALENDAR" : face.widget.type === "media" ? "NOW PLAYING" : "WIDGET"
            font.pixelSize: 11
            font.letterSpacing: 2
        }
        Label {
            width: parent.width
            wrapMode: Text.Wrap
            maximumLineCount: 2
            elide: Text.ElideRight
            color: face.theme.foreground || "#FFF5F7FF"
            font.pixelSize: face.widget.type === "clock" ? 42 : 24
            font.weight: Font.DemiBold
            text: {
                if (face.widget.type === "clock") return Qt.formatTime(face.now, (face.widget.options || {}).format || "HH:mm");
                if (face.widget.type === "calendar") return Qt.formatDate(face.now, "dddd, d MMMM");
                if (face.widget.type === "media") return face.player ? face.player.trackTitle || "Unknown title" : "No player connected";
                return "Unavailable widget";
            }
        }
        Label {
            width: parent.width
            elide: Text.ElideRight
            color: face.theme.muted || "#FFAFB7CC"
            font.pixelSize: 13
            text: face.widget.type === "media" ? (face.player ? face.player.trackArtist : "Open a media player to see its track") : Qt.formatDate(face.now, "yyyy")
        }
    }
}

#!/bin/bash
# Удалить фоновую службу
PLIST="$HOME/Library/LaunchAgents/com.calmveritas.admin.plist"
launchctl unload "$PLIST" 2>/dev/null
rm -f "$PLIST"
echo "Служба удалена."

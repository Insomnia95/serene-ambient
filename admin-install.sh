#!/bin/bash
# Установить admin как фоновую службу macOS
# Запуск: bash admin-install.sh

PLIST_SRC="$HOME/Calm-veritas/admin-service.plist"
PLIST_DST="$HOME/Library/LaunchAgents/com.calmveritas.admin.plist"

cp "$PLIST_SRC" "$PLIST_DST"
launchctl unload "$PLIST_DST" 2>/dev/null
launchctl load "$PLIST_DST"

echo ""
echo "Служба запущена. Дашборд: http://localhost:8080"
echo "Работает в фоне и стартует автоматически при каждом входе в систему."
echo ""
echo "Остановить:   launchctl unload ~/Library/LaunchAgents/com.calmveritas.admin.plist"
echo "Запустить:    launchctl load   ~/Library/LaunchAgents/com.calmveritas.admin.plist"
echo "Удалить:      bash admin-uninstall.sh"

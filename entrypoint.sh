#!/bin/sh

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🛠  LOADING PLUGINS..."

PLUGIN_COUNT=0

for file in plugins/*.py; do
    if [ -f "$file" ]; then
        NAME=$(basename "$file")
        case "$NAME" in
            __*) ;;
            *)
                echo "✅ Successfully Loaded: $NAME"
                PLUGIN_COUNT=$((PLUGIN_COUNT+1))
            ;;
        esac
    fi
done

echo "🎉 Total $PLUGIN_COUNT Plugins Loaded!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 🔥 FIX: Wait 30 seconds before starting to prevent FloodWait
echo "⏳ Waiting 30 seconds before starting bot..."
sleep 30

# Bot start
python bot.py

#!/bin/bash
# Quick Debug Mode Toggle Script

echo "🐛 MetaLex Debug Mode Toggle"
echo "=============================="
echo ""

# Check current status
if grep -q "DEBUG_MODE=true" .env 2>/dev/null; then
    CURRENT="ENABLED"
    NEW_STATE="false"
    ACTION="DISABLE"
else
    CURRENT="DISABLED"
    NEW_STATE="true"
    ACTION="ENABLE"
fi

echo "Current status: $CURRENT"
echo ""
echo "Options:"
echo "  1) $ACTION debug mode"
echo "  2) View current logs"
echo "  3) View logs in real-time (Ctrl+C to exit)"
echo "  4) Exit"
echo ""
read -p "Choose option (1-4): " choice

case $choice in
    1)
        echo ""
        echo "📝 Updating .env file..."
        sed -i '' "s/DEBUG_MODE=.*/DEBUG_MODE=$NEW_STATE/" .env 2>/dev/null || \
        echo "DEBUG_MODE=$NEW_STATE" >> .env
        
        echo "🔄 Restarting backend..."
        pkill -f uvicorn
        sleep 2
        
        cd /Users/namangaur/SIH_26034
        rm -f /tmp/metalex_backend.log
        python3 -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload > /tmp/metalex_backend.log 2>&1 &
        
        echo "✅ Backend restarted with debug mode: $NEW_STATE"
        sleep 4
        
        # Verify
        if grep -q "DEBUG MODE ENABLED" /tmp/metalex_backend.log 2>/dev/null; then
            echo "✅ Debug mode is now ENABLED"
        else
            echo "✅ Debug mode is now DISABLED"
        fi
        
        echo ""
        echo "📊 Backend health:"
        curl -s http://localhost:8000/api/health | python3 -m json.tool 2>/dev/null || echo "⚠️  Backend still starting..."
        ;;
    2)
        echo ""
        echo "📋 Last 30 log lines:"
        echo "===================="
        tail -30 /tmp/metalex_backend.log 2>/dev/null || echo "No logs found"
        ;;
    3)
        echo ""
        echo "📊 Watching logs in real-time (Ctrl+C to stop)..."
        echo "================================================"
        tail -f /tmp/metalex_backend.log 2>/dev/null || echo "No logs found"
        ;;
    4)
        echo "Exiting..."
        exit 0
        ;;
    *)
        echo "Invalid option"
        exit 1
        ;;
esac

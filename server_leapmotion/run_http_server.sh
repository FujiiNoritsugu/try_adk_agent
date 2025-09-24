#!/bin/bash

# Leap Motion HTTP Server Launch Script

# Activate virtual environment if exists
if [ -d "../venv" ]; then
    echo "Activating virtual environment..."
    source ../venv/bin/activate
elif [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Default settings
HOST="0.0.0.0"
PORT=8001

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --host)
            HOST="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --reload)
            RELOAD="--reload"
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --host HOST    Host to bind to (default: 0.0.0.0)"
            echo "  --port PORT    Port to listen on (default: 8001)"
            echo "  --reload       Enable auto-reload for development"
            echo "  --help         Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "==========================================="
echo "  Leap Motion HTTP MCP Server"
echo "==========================================="
echo "Host: $HOST"
echo "Port: $PORT"
echo ""
echo "Endpoints:"
echo "  GET  http://$HOST:$PORT/"
echo "  GET  http://$HOST:$PORT/health"
echo "  GET  http://$HOST:$PORT/leap-data"
echo "  GET  http://$HOST:$PORT/touch-input"
echo "  POST http://$HOST:$PORT/gesture-mapping"
echo "  GET  http://$HOST:$PORT/gesture-mappings"
echo "==========================================="
echo ""

# Run the server
python server_http.py --host "$HOST" --port "$PORT" $RELOAD
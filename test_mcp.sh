#!/bin/bash
# Test script for MCP Transaction Analyzer

echo "Testing MCP Transaction Analyzer..."

# Start the MCP server in background
docker-compose exec -d mcp-transaction-analyzer python3 server.py

# Wait a moment for server to start
sleep 2

# Test the MCP protocol
echo "Testing MCP protocol..."
RESPONSE=$(docker-compose exec -T mcp-transaction-analyzer python3 server.py << 'EOF'
{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "test", "version": "1.0"}}}
{"jsonrpc": "2.0", "method": "notifications/initialized"}
{"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
EOF
)

echo "MCP Response:"
echo "$RESPONSE"

# Check if tools are listed
if echo "$RESPONSE" | grep -q "analyze_spending"; then
    echo "✅ Tools listed successfully"
else
    echo "❌ Tools not found in response"
fi

echo "Test complete!"
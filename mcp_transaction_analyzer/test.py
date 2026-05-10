#!/usr/bin/env python3
"""
Test script for MCP Transaction Analyzer

This script tests the MCP server functionality by simulating tool calls
and resource requests.
"""

import asyncio
import json
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server import (
    handle_analyze_spending,
    handle_categorize_transactions,
    handle_detect_anomalies,
    handle_compare_periods
)

async def test_tools():
    """Test all MCP tools"""
    print("🧪 Testing MCP Transaction Analyzer Tools\n")

    # Test analyze_spending
    print("1. Testing analyze_spending...")
    try:
        result = await handle_analyze_spending({})
        print("✅ analyze_spending: OK")
        print(f"   Result: {result[0].text[:100]}...\n")
    except Exception as e:
        print(f"❌ analyze_spending: FAILED - {e}\n")

    # Test categorize_transactions
    print("2. Testing categorize_transactions...")
    try:
        result = await handle_categorize_transactions({})
        print("✅ categorize_transactions: OK")
        print(f"   Result: {result[0].text[:100]}...\n")
    except Exception as e:
        print(f"❌ categorize_transactions: FAILED - {e}\n")

    # Test detect_anomalies
    print("3. Testing detect_anomalies...")
    try:
        result = await handle_detect_anomalies({})
        print("✅ detect_anomalies: OK")
        print(f"   Result: {result[0].text[:100]}...\n")
    except Exception as e:
        print(f"❌ detect_anomalies: FAILED - {e}\n")

    # Test compare_periods
    print("4. Testing compare_periods...")
    try:
        result = await handle_compare_periods({"period1_start": "2024-01-01", "period1_end": "2024-01-31", "period2_start": "2024-02-01", "period2_end": "2024-02-28"})
        print("✅ compare_periods: OK")
        print(f"   Result: {result[0].text[:100]}...\n")
    except Exception as e:
        print(f"❌ compare_periods: FAILED - {e}\n")

async def test_resources():
    """Test MCP resources"""
    print("📊 Testing MCP Resources\n")

    # Test schema resource
    print("1. Testing transaction schema...")
    try:
        schema = await get_transaction_schema()
        print("✅ Schema resource: OK")
        print(f"   Schema: {schema[:200]}...\n")
    except Exception as e:
        print(f"❌ Schema resource: FAILED - {e}\n")

    # Test stats resource
    print("2. Testing transaction stats...")
    try:
        stats = await get_transaction_stats()
        print("✅ Stats resource: OK")
        print(f"   Stats: {stats[:200]}...\n")
    except Exception as e:
        print(f"❌ Stats resource: FAILED - {e}\n")

async def main():
    """Run all tests"""
    print("🚀 MCP Transaction Analyzer Test Suite")
    print("=" * 50)

    # Check if we have data
    print("⚠️  Note: Tests require transaction data in MinIO bucket")
    print("   Make sure you've run the data pipeline first\n")

    await test_tools()
    await test_resources()

    print("✨ Test suite completed!")
    print("\n💡 To run the MCP server:")
    print("   python server.py")
    print("\n💡 To integrate with Claude Desktop, see README.md")

if __name__ == "__main__":
    asyncio.run(main())
#!/usr/bin/env python3
"""
Test MCP vibration server functionality
"""

import asyncio
import json
import subprocess
import time
from typing import Dict, Any

async def send_mcp_request(command: str, params: Dict[str, Any]) -> Dict[str, Any]:
    """Send a request to the MCP server"""
    request = {
        "jsonrpc": "2.0",
        "method": f"tools/call",
        "params": {
            "name": command,
            "arguments": params
        },
        "id": 1
    }
    
    # MCPサーバープロセスを起動
    process = subprocess.Popen(
        ["python", "mcp_servers/vibration_server.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # リクエストを送信
    process.stdin.write(json.dumps(request) + "\n")
    process.stdin.flush()
    
    # レスポンスを読み取り
    response_line = process.stdout.readline()
    
    # プロセスを終了
    process.terminate()
    
    try:
        return json.loads(response_line)
    except json.JSONDecodeError:
        return {"error": "Failed to parse response", "raw": response_line}

async def test_vibration_flow():
    """Test the complete vibration flow"""
    print("=== MCP Vibration Server Test ===\n")
    
    # 1. Initialize Arduino
    print("1. Initializing Arduino...")
    init_params = {
        "host": "192.168.43.166",
        "port": 80
    }
    
    # 直接vibration_server.pyの関数を呼び出してテスト
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    from mcp_servers.vibration_server import (
        initialize_arduino, 
        generate_vibration_pattern, 
        control_vibration,
        InitializeArduinoArgs,
        GenerateVibrationArgs,
        ControlVibrationArgs
    )
    
    # Arduino初期化
    init_args = InitializeArduinoArgs(**init_params)
    result = await initialize_arduino(init_args)
    print(f"Result: {result[0].text}\n")
    
    # 2. Generate vibration pattern
    print("2. Generating vibration pattern...")
    pattern_params = {
        "joy": 5,
        "fun": 2,
        "anger": 0,
        "sad": 0
    }
    
    pattern_args = GenerateVibrationArgs(**pattern_params)
    result = await generate_vibration_pattern(pattern_args)
    pattern_result = json.loads(result[0].text)
    print(f"Result: {json.dumps(pattern_result, indent=2)}\n")
    
    # 3. Control vibration
    print("3. Sending vibration control...")
    control_args = ControlVibrationArgs(vibration_settings=pattern_result)
    result = await control_vibration(control_args)
    print(f"Result: {result[0].text}\n")
    
    # Wait for vibration to complete
    print("Waiting for vibration to complete...")
    await asyncio.sleep(3)
    
    # Test another pattern
    print("\n4. Testing another pattern (sad)...")
    pattern_params = {
        "joy": 0,
        "fun": 0,
        "anger": 0,
        "sad": 4
    }
    
    pattern_args = GenerateVibrationArgs(**pattern_params)
    result = await generate_vibration_pattern(pattern_args)
    pattern_result = json.loads(result[0].text)
    print(f"Pattern: {json.dumps(pattern_result, indent=2)}\n")
    
    control_args = ControlVibrationArgs(vibration_settings=pattern_result)
    result = await control_vibration(control_args)
    print(f"Control result: {result[0].text}\n")

if __name__ == "__main__":
    asyncio.run(test_vibration_flow())
#!/usr/bin/env python3
"""Test MCP server's save_interaction functionality"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

# Import directly from MCP server
from mcp_servers.vectorsearch_server import save_interaction, SaveInteractionArgs

import asyncio

async def test_save():
    """Test saving an interaction"""
    args = SaveInteractionArgs(
        touched_area="頭",
        data=0.7,
        gesture_type="pat",
        hand_velocity=180.0,
        joy=4.5,
        fun=3.5,
        anger=0.2,
        sad=0.1,
        response_text="テスト用の応答: 優しく撫でてくれてありがとう!",
        session_id="test_mcp_session_001"
    )

    print("[TEST] Calling save_interaction with args:")
    print(f"  Area: {args.touched_area}")
    print(f"  Intensity: {args.data}")
    print(f"  Response: {args.response_text}")

    result = await save_interaction(args)

    print("\n[TEST] Result:")
    for content in result:
        print(content.text)

if __name__ == "__main__":
    asyncio.run(test_save())

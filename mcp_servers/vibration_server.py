#!/usr/bin/env python3
"""MCP server for vibration control based on emotions with Arduino integration"""

import asyncio
import json
import sys
import os
from typing import Any, Dict, List, Optional
from mcp.server import Server
from mcp.types import TextContent, Tool
from pydantic import BaseModel, Field

# Add parent and src directories to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from src.devices import ArduinoController, VibrationPatternGenerator


class GenerateVibrationArgs(BaseModel):
    """Arguments for generate_vibration_pattern tool"""
    joy: int = Field(description="喜びの感情値 (0-5)", ge=0, le=5)
    fun: int = Field(description="楽しさの感情値 (0-5)", ge=0, le=5)
    anger: int = Field(description="怒りの感情値 (0-5)", ge=0, le=5)
    sad: int = Field(description="悲しみの感情値 (0-5)", ge=0, le=5)


class ControlVibrationArgs(BaseModel):
    """Arguments for control_vibration tool"""
    vibration_settings: Dict[str, Any] = Field(description="振動設定の辞書")


class InitializeArduinoArgs(BaseModel):
    """Arguments for initialize_arduino tool"""
    host: str = Field(description="ArduinoのIPアドレス")
    port: int = Field(description="ポート番号", default=80)


class SendArduinoVibrationArgs(BaseModel):
    """Arguments for sending vibration pattern to Arduino"""
    pattern_type: str = Field(description="振動パターンタイプ (pulse, wave, burst, fade)")
    intensity: float = Field(description="振動強度 (0.0-1.0)", ge=0.0, le=1.0)
    duration_ms: int = Field(description="振動持続時間（ミリ秒）", ge=0)
    repeat_count: int = Field(description="繰り返し回数", ge=1, default=1)


app = Server("vibration-server")

# Global Arduino controller instance
arduino_controller: Optional[ArduinoController] = None


async def generate_vibration_pattern(arguments: GenerateVibrationArgs) -> List[TextContent]:
    """感情パラメータに基づいて振動パターンを生成します"""
    
    # 基本振動パターンの定義
    vibration_patterns = {
        "joy": {
            "pattern": "pulse",
            "intensity_base": 0.6,
            "frequency_base": 2.0,  # Hz
            "duration_base": 0.5,  # seconds
            "description": "軽快でリズミカルな振動",
        },
        "fun": {
            "pattern": "wave",
            "intensity_base": 0.7,
            "frequency_base": 3.0,
            "duration_base": 0.3,
            "description": "楽しい波打つような振動",
        },
        "anger": {
            "pattern": "burst",
            "intensity_base": 0.9,
            "frequency_base": 5.0,
            "duration_base": 0.2,
            "description": "強く断続的な振動",
        },
        "sad": {
            "pattern": "fade",
            "intensity_base": 0.4,
            "frequency_base": 1.0,
            "duration_base": 1.0,
            "description": "ゆっくりとした弱い振動",
        },
    }
    
    # 感情値の辞書
    emotions = {
        "joy": arguments.joy, 
        "fun": arguments.fun, 
        "anger": arguments.anger, 
        "sad": arguments.sad
    }
    
    # 最も強い感情を見つける
    max_emotion = max(emotions.items(), key=lambda x: x[1])
    dominant_emotion, emotion_value = max_emotion
    
    # 感情値が0の場合は振動なし
    if emotion_value == 0:
        result = {
            "vibration_enabled": False,
            "pattern": "none",
            "intensity": 0,
            "frequency": 0,
            "duration": 0,
            "description": "振動なし",
        }
        return [TextContent(type="text", text=json.dumps(result))]
    
    # 基本パターンを取得
    base_pattern = vibration_patterns[dominant_emotion]
    
    # 感情の強さに応じて調整
    emotion_multiplier = 0.2 + (emotion_value / 5) * 0.8
    
    # 複数の感情が高い場合の調整
    mixed_emotions = [
        emo for emo, val in emotions.items() 
        if emo != dominant_emotion and val >= 3
    ]
    
    # 混合パターンの作成
    if mixed_emotions:
        pattern_type = f"{base_pattern['pattern']}_mixed"
        intensity_adjustment = 1.1
        frequency_adjustment = 1.2
    else:
        pattern_type = base_pattern["pattern"]
        intensity_adjustment = 1.0
        frequency_adjustment = 1.0
    
    # 最終的な振動設定
    result = {
        "vibration_enabled": True,
        "pattern": pattern_type,
        "intensity": min(
            base_pattern["intensity_base"] * emotion_multiplier * intensity_adjustment,
            1.0,
        ),
        "frequency": base_pattern["frequency_base"] * emotion_multiplier * frequency_adjustment,
        "duration": base_pattern["duration_base"] * emotion_multiplier,
        "dominant_emotion": dominant_emotion,
        "mixed_emotions": mixed_emotions,
        "description": base_pattern["description"],
        "emotion_level": emotion_value,
    }
    
    return [TextContent(type="text", text=json.dumps(result))]


async def control_vibration(arguments: ControlVibrationArgs) -> List[TextContent]:
    """振動設定に基づいて実際の振動制御コマンドを生成し、Arduinoに送信します"""
    global arduino_controller
    
    vibration_settings = arguments.vibration_settings
    
    if not vibration_settings.get("vibration_enabled", False):
        # 振動を停止
        if arduino_controller and arduino_controller.is_connected:
            await arduino_controller.stop()
        result = {"command": "STOP", "message": "振動を停止します", "arduino_sent": True}
        return [TextContent(type="text", text=json.dumps(result))]
    
    # パターンに応じたコマンドの生成
    pattern = vibration_settings["pattern"]
    intensity = vibration_settings["intensity"]  # 0.0-1.0の範囲
    frequency = vibration_settings["frequency"]
    duration = int(vibration_settings["duration"] * 1000)  # ミリ秒に変換
    
    # パターンタイプの簡略化（mixed → 通常のパターン）
    base_pattern = pattern.replace("_mixed", "")
    
    # VibrationPatternGeneratorを使用してパターンを生成
    vibration_pattern = VibrationPatternGenerator.create_custom_pattern(
        pattern_type=base_pattern,
        intensity=intensity,
        duration_ms=duration,
        repeat_count=int(frequency)
    )
    
    # Arduinoに送信
    arduino_sent = False
    arduino_response = None
    
    if arduino_controller is None or not arduino_controller.is_connected:
        arduino_response = {"error": "Arduinoが初期化されていません"}
    else:
        try:
            arduino_sent = await arduino_controller.send_pattern(vibration_pattern)
            arduino_response = {"success": arduino_sent}
        except Exception as e:
            arduino_response = {"error": str(e)}
    
    # コマンド生成（後方互換性のため）
    intensity_255 = int(intensity * 255)
    command_map = {
        "pulse": f"PULSE:{intensity_255},{frequency},{duration}",
        "wave": f"WAVE:{intensity_255},{frequency},{duration}",
        "burst": f"BURST:{intensity_255},{frequency},{duration}",
        "fade": f"FADE:{intensity_255},{frequency},{duration}",
    }
    
    command = command_map.get(base_pattern, f"DEFAULT:{intensity_255},{frequency},{duration}")
    
    result = {
        "command": command,
        "message": f"{vibration_settings.get('description', '振動パターン')}を実行します",
        "details": {
            "pattern": pattern,
            "intensity": intensity,
            "frequency": frequency,
            "duration": duration,
            "emotion": vibration_settings.get("dominant_emotion", "unknown"),
        },
        "arduino_sent": arduino_sent,
        "arduino_pattern": vibration_pattern.to_dict() if vibration_pattern else None,
        "arduino_response": arduino_response
    }
    
    return [TextContent(type="text", text=json.dumps(result))]


async def initialize_arduino(arguments: InitializeArduinoArgs) -> List[TextContent]:
    """ArduinoをWiFi経由で初期化します"""
    global arduino_controller
    
    try:
        # 既存の接続を閉じる
        if arduino_controller and arduino_controller.is_connected:
            await arduino_controller.disconnect()
        
        # 新しいArduinoコントローラーを作成
        arduino_controller = ArduinoController(
            "haptic_device",
            host=arguments.host,
            port=arguments.port
        )
        
        connected = await arduino_controller.connect()
        
        if connected:
            # ステータス取得
            status = await arduino_controller.get_status()
            
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "message": "Arduino haptic deviceの初期化に成功しました",
                    "host": arguments.host,
                    "port": arguments.port,
                    "status": status
                })
            )]
        else:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": f"Arduino haptic deviceに接続できませんでした ({arguments.host}:{arguments.port})"
                })
            )]
    except Exception as e:
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": f"初期化中にエラーが発生しました: {str(e)}"
            })
        )]


async def send_arduino_vibration(arguments: SendArduinoVibrationArgs) -> List[TextContent]:
    """Arduinoに振動パターンを送信します"""
    global arduino_controller
    
    # Arduinoコントローラーの確認
    if arduino_controller is None or not arduino_controller.is_connected:
        return [TextContent(
            type="text", 
            text=json.dumps({
                "success": False,
                "error": "Arduinoが接続されていません。initialize_arduinoを実行してください"
            })
        )]
    
    try:
        # VibrationPatternGeneratorを使用してパターンを生成
        vibration_pattern = VibrationPatternGenerator.create_custom_pattern(
            pattern_type=arguments.pattern_type,
            intensity=arguments.intensity,
            duration_ms=arguments.duration_ms,
            repeat_count=arguments.repeat_count
        )
        
        # Arduinoに送信
        success = await arduino_controller.send_pattern(vibration_pattern)
        
        if success:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": True,
                    "message": f"振動パターン '{arguments.pattern_type}' を送信しました",
                    "pattern": vibration_pattern.to_dict()
                })
            )]
        else:
            return [TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": "振動パターンの送信に失敗しました"
                })
            )]
            
    except Exception as e:
        return [TextContent(
            type="text",
            text=json.dumps({
                "success": False,
                "error": f"エラーが発生しました: {str(e)}"
            })
        )]


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available tools"""
    return [
        Tool(
            name="generate_vibration_pattern",
            description="感情パラメータに基づいて振動パターンを生成します",
            inputSchema=GenerateVibrationArgs.model_json_schema(),
        ),
        Tool(
            name="control_vibration",
            description="振動設定に基づいて実際の振動制御コマンドを生成し、Arduinoに送信します",
            inputSchema=ControlVibrationArgs.model_json_schema(),
        ),
        Tool(
            name="initialize_arduino",
            description="Arduino haptic deviceをWiFi経由で初期化します",
            inputSchema=InitializeArduinoArgs.model_json_schema(),
        ),
        Tool(
            name="send_arduino_vibration",
            description="Arduinoに振動パターンを直接送信します",
            inputSchema=SendArduinoVibrationArgs.model_json_schema(),
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Call a tool by name"""
    if name == "generate_vibration_pattern":
        args = GenerateVibrationArgs(**arguments)
        return await generate_vibration_pattern(args)
    elif name == "control_vibration":
        args = ControlVibrationArgs(**arguments)
        return await control_vibration(args)
    elif name == "initialize_arduino":
        args = InitializeArduinoArgs(**arguments)
        return await initialize_arduino(args)
    elif name == "send_arduino_vibration":
        args = SendArduinoVibrationArgs(**arguments)
        return await send_arduino_vibration(args)
    else:
        raise ValueError(f"Unknown tool: {name}")


async def main():
    """Run the MCP server"""
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
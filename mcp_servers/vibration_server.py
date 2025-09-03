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
    
    # VibrationPatternGeneratorを使用してパターンを生成
    pattern = VibrationPatternGenerator.from_emotion_values(
        joy=arguments.joy,
        fun=arguments.fun,
        anger=arguments.anger,
        sad=arguments.sad
    )
    
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
    if emotion_value == 0 or not pattern.steps:
        result = {
            "vibration_enabled": False,
            "pattern": "none",
            "intensity": 0,
            "frequency": 0,
            "duration": 0,
            "description": "振動なし",
            "vibration_pattern": None
        }
        return [TextContent(type="text", text=json.dumps(result))]
    
    # パターンタイプと説明を設定
    pattern_descriptions = {
        "joy": "軽快でリズミカルな振動",
        "fun": "楽しい波打つような振動",
        "anger": "強く断続的な振動",
        "sad": "ゆっくりとした弱い振動",
    }
    
    # パターンから平均強度と合計時間を計算
    avg_intensity = sum(step.intensity for step in pattern.steps) / len(pattern.steps)
    total_duration = sum(step.duration for step in pattern.steps) + pattern.interval * (len(pattern.steps) - 1)
    
    # 最終的な振動設定
    result = {
        "vibration_enabled": True,
        "pattern": dominant_emotion,
        "intensity": avg_intensity,
        "frequency": pattern.repeat_count,  # repeat_countを周波数として使用
        "duration": total_duration / 1000.0,  # ミリ秒から秒に変換
        "dominant_emotion": dominant_emotion,
        "mixed_emotions": [
            emo for emo, val in emotions.items() 
            if emo != dominant_emotion and val >= 3
        ],
        "description": pattern_descriptions.get(dominant_emotion, "カスタム振動パターン"),
        "emotion_level": emotion_value,
        "vibration_pattern": pattern.to_dict()  # 実際のパターンデータを含める
    }
    
    return [TextContent(type="text", text=json.dumps(result))]


async def control_vibration(arguments: ControlVibrationArgs) -> List[TextContent]:
    """振動設定に基づいて実際の振動制御コマンドを生成し、Arduinoに送信します"""
    global arduino_controller
    
    vibration_settings = arguments.vibration_settings
    
    # デバッグログ
    print(f"[DEBUG] control_vibration received settings: {json.dumps(vibration_settings, indent=2)}")
    
    if not vibration_settings.get("vibration_enabled", False):
        # 振動を停止
        if arduino_controller and arduino_controller.is_connected:
            await arduino_controller.stop()
        result = {"command": "STOP", "message": "振動を停止します", "arduino_sent": True}
        return [TextContent(type="text", text=json.dumps(result))]
    
    # 既に生成されたパターンがある場合はそれを使用
    if "vibration_pattern" in vibration_settings and vibration_settings["vibration_pattern"]:
        vibration_pattern_dict = vibration_settings["vibration_pattern"]
        # 辞書からVibrationPatternオブジェクトを再構築
        from src.devices.vibration_patterns import VibrationPattern, VibrationStep
        steps = [
            VibrationStep(
                intensity=step["intensity"] / 100.0,  # 100スケールから0-1スケールに変換
                duration=step["duration"]
            )
            for step in vibration_pattern_dict["steps"]
        ]
        vibration_pattern = VibrationPattern(
            steps=steps,
            interval=vibration_pattern_dict.get("interval", 50),
            repeat_count=vibration_pattern_dict.get("repeat_count", 1)
        )
    else:
        # 後方互換性のため、パターンがない場合は生成
        pattern = vibration_settings.get("pattern", "pulse")
        intensity = vibration_settings.get("intensity", 0.5)
        frequency = vibration_settings.get("frequency", 1)
        duration = int(vibration_settings.get("duration", 1) * 1000)
        
        vibration_pattern = VibrationPatternGenerator.create_custom_pattern(
            pattern_type=pattern,
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
            # デバッグ: 送信するパターンをログ出力
            pattern_dict = vibration_pattern.to_dict()
            print(f"[DEBUG] Sending pattern to Arduino: {json.dumps(pattern_dict, indent=2)}")
            
            arduino_sent = await arduino_controller.send_pattern(vibration_pattern)
            arduino_response = {"success": arduino_sent}
            print(f"[DEBUG] Arduino send result: {arduino_sent}")
        except Exception as e:
            arduino_response = {"error": str(e)}
            print(f"[DEBUG] Arduino send error: {str(e)}")
    
    result = {
        "message": f"{vibration_settings.get('description', '振動パターン')}を実行します",
        "details": {
            "pattern": vibration_settings.get("pattern", "unknown"),
            "dominant_emotion": vibration_settings.get("dominant_emotion", "unknown"),
            "emotion_level": vibration_settings.get("emotion_level", 0),
        },
        "arduino_sent": arduino_sent,
        "arduino_pattern": vibration_pattern.to_dict() if vibration_pattern else None,
        "arduino_response": arduino_response
    }
    
    return [TextContent(type="text", text=json.dumps(result))]


async def initialize_arduino(arguments: InitializeArduinoArgs) -> List[TextContent]:
    """ArduinoをWiFi経由で初期化します"""
    global arduino_controller
    
    print(f"[DEBUG] Initializing Arduino at {arguments.host}:{arguments.port}")
    
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
        print(f"[DEBUG] Arduino connection result: {connected}")
        
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
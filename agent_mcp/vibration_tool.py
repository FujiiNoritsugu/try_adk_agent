"""
Direct vibration control tool for ADK Web
"""

import asyncio
import json
from typing import Dict, Any
from google.adk.tools import FunctionTool
import sys
import os

# Add parent directories to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

from src.devices import ArduinoController, VibrationPatternGenerator

# Global Arduino controller
arduino_controller = None
arduino_initialized = False

async def initialize_arduino_direct(host: str = "192.168.43.166", port: int = 80) -> Dict[str, Any]:
    """Arduino haptic deviceを初期化します"""
    global arduino_controller, arduino_initialized
    
    try:
        # 既存の接続を閉じる
        if arduino_controller and arduino_controller.is_connected:
            await arduino_controller.disconnect()
        
        # 新しいコントローラーを作成
        arduino_controller = ArduinoController(
            "haptic_device",
            host=host,
            port=port
        )
        
        connected = await arduino_controller.connect()
        
        if connected:
            arduino_initialized = True
            status = await arduino_controller.get_status()
            return {
                "success": True,
                "message": "Arduino初期化成功",
                "status": status
            }
        else:
            return {
                "success": False,
                "error": "Arduino接続失敗"
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

async def generate_vibration_pattern_direct(
    joy: int,
    fun: int,
    anger: int,
    sad: int
) -> Dict[str, Any]:
    """感情値から振動パターンを生成します"""
    
    # パターンを生成
    pattern = VibrationPatternGenerator.from_emotion_values(
        joy=joy,
        fun=fun,
        anger=anger,
        sad=sad
    )
    
    # 最も強い感情を見つける
    emotions = {"joy": joy, "fun": fun, "anger": anger, "sad": sad}
    dominant_emotion, emotion_value = max(emotions.items(), key=lambda x: x[1])
    
    if emotion_value == 0 or not pattern.steps:
        return {
            "vibration_enabled": False,
            "pattern": None,
            "message": "振動なし"
        }
    
    return {
        "vibration_enabled": True,
        "pattern": pattern.to_dict(),
        "dominant_emotion": dominant_emotion,
        "emotion_level": emotion_value,
        "message": f"{dominant_emotion}パターン生成完了"
    }

async def send_vibration_direct(pattern_dict: Dict[str, Any]) -> Dict[str, Any]:
    """振動パターンをArduinoに送信します"""
    global arduino_controller, arduino_initialized
    
    # 初期化チェック
    if not arduino_initialized:
        # 自動初期化を試みる
        init_result = await initialize_arduino_direct()
        if not init_result["success"]:
            return init_result
    
    if not arduino_controller or not arduino_controller.is_connected:
        return {
            "success": False,
            "error": "Arduino未接続"
        }
    
    try:
        # パターンを再構築
        from src.devices.vibration_patterns import VibrationPattern, VibrationStep
        
        steps = [
            VibrationStep(
                intensity=step["intensity"] / 100.0,
                duration=step["duration"]
            )
            for step in pattern_dict["steps"]
        ]
        
        pattern = VibrationPattern(
            steps=steps,
            interval=pattern_dict.get("interval", 50),
            repeat_count=pattern_dict.get("repeat_count", 1)
        )
        
        # 送信
        success = await arduino_controller.send_pattern(pattern)
        
        return {
            "success": success,
            "message": "振動パターン送信完了" if success else "送信失敗"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

# エクスポート
vibration_tools = [
    FunctionTool(initialize_arduino_direct),
    FunctionTool(generate_vibration_pattern_direct),
    FunctionTool(send_vibration_direct)
]
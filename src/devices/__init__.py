"""
Device control modules for haptic feedback
"""

from .base_controller import BaseController, BaseControllerManager
from .arduino_controller import ArduinoController, ArduinoManager
from .vibration_patterns import (
    VibrationStep,
    VibrationPattern,
    EmotionType,
    EmotionVibrationPatterns,
    VibrationPatternGenerator
)

__all__ = [
    'BaseController',
    'BaseControllerManager',
    'ArduinoController',
    'ArduinoManager',
    'VibrationStep',
    'VibrationPattern',
    'EmotionType',
    'EmotionVibrationPatterns',
    'VibrationPatternGenerator'
]
"""
Vibration pattern definitions and generators
"""

from dataclasses import dataclass
from typing import List, Dict, Any
from enum import Enum


@dataclass
class VibrationStep:
    """Single step in a vibration pattern"""
    intensity: float  # 0.0-1.0
    duration: int    # milliseconds
    
    def to_dict(self, intensity_scale: int = 100) -> Dict[str, int]:
        """Convert to dictionary format for device"""
        return {
            "intensity": int(self.intensity * intensity_scale),
            "duration": self.duration
        }


@dataclass
class VibrationPattern:
    """Complete vibration pattern"""
    steps: List[VibrationStep]
    interval: int = 50  # milliseconds between steps
    repeat_count: int = 1
    
    def to_dict(self, intensity_scale: int = 100) -> Dict[str, Any]:
        """Convert to dictionary format for device"""
        return {
            "steps": [step.to_dict(intensity_scale) for step in self.steps],
            "interval": self.interval,
            "repeat_count": self.repeat_count
        }


class EmotionType(Enum):
    """Emotion types for vibration patterns"""
    JOY = "joy"
    ANGER = "anger"
    SORROW = "sorrow"
    PLEASURE = "pleasure"
    NEUTRAL = "neutral"


class EmotionVibrationPatterns:
    """Predefined vibration patterns for emotions"""
    
    @staticmethod
    def joy() -> VibrationPattern:
        """Light, rhythmic pattern for joy"""
        return VibrationPattern(
            steps=[
                VibrationStep(0.6, 100),
                VibrationStep(0.0, 50),
                VibrationStep(0.8, 150),
                VibrationStep(0.0, 50),
                VibrationStep(0.6, 100),
            ],
            interval=50,
            repeat_count=2
        )
        
    @staticmethod
    def anger() -> VibrationPattern:
        """Intense, rapid pattern for anger"""
        return VibrationPattern(
            steps=[
                VibrationStep(0.9, 200),
                VibrationStep(0.0, 30),
                VibrationStep(1.0, 150),
                VibrationStep(0.0, 30),
                VibrationStep(0.8, 200),
            ],
            interval=20,
            repeat_count=3
        )
        
    @staticmethod
    def sorrow() -> VibrationPattern:
        """Slow, gentle pattern for sorrow"""
        return VibrationPattern(
            steps=[
                VibrationStep(0.8, 500),
                VibrationStep(0.6, 300),
                VibrationStep(0.4, 200),
            ],
            interval=100,
            repeat_count=2
        )
        
    @staticmethod
    def pleasure() -> VibrationPattern:
        """Smooth, moderate pattern for pleasure"""
        return VibrationPattern(
            steps=[
                VibrationStep(0.6, 300),
                VibrationStep(0.8, 400),
                VibrationStep(0.7, 300),
                VibrationStep(0.5, 200),
            ],
            interval=50,
            repeat_count=1
        )
        
    @staticmethod
    def neutral() -> VibrationPattern:
        """Simple notification pattern"""
        return VibrationPattern(
            steps=[
                VibrationStep(0.5, 200),
            ],
            interval=0,
            repeat_count=1
        )
        
    @staticmethod
    def get_pattern(emotion: EmotionType) -> VibrationPattern:
        """Get pattern for emotion type"""
        patterns = {
            EmotionType.JOY: EmotionVibrationPatterns.joy,
            EmotionType.ANGER: EmotionVibrationPatterns.anger,
            EmotionType.SORROW: EmotionVibrationPatterns.sorrow,
            EmotionType.PLEASURE: EmotionVibrationPatterns.pleasure,
            EmotionType.NEUTRAL: EmotionVibrationPatterns.neutral,
        }
        return patterns.get(emotion, EmotionVibrationPatterns.neutral)()


class VibrationPatternGenerator:
    """Generate dynamic vibration patterns based on emotion parameters"""
    
    @staticmethod
    def from_emotion_values(joy: int, fun: int, anger: int, sad: int) -> VibrationPattern:
        """
        Generate pattern from emotion values (0-5 scale)
        
        Args:
            joy: Joy level (0-5)
            fun: Fun level (0-5)
            anger: Anger level (0-5)
            sad: Sadness level (0-5)
            
        Returns:
            VibrationPattern based on dominant emotion
        """
        # Find dominant emotion
        emotions = {
            "joy": joy,
            "fun": fun,
            "anger": anger,
            "sad": sad
        }
        
        dominant = max(emotions.items(), key=lambda x: x[1])
        emotion_name, emotion_value = dominant
        
        # No vibration if all emotions are zero
        if emotion_value == 0:
            return VibrationPattern(steps=[], interval=0, repeat_count=0)
            
        # Map to emotion types
        emotion_map = {
            "joy": EmotionType.JOY,
            "fun": EmotionType.PLEASURE,
            "anger": EmotionType.ANGER,
            "sad": EmotionType.SORROW
        }
        
        # Get base pattern
        base_pattern = EmotionVibrationPatterns.get_pattern(
            emotion_map.get(emotion_name, EmotionType.NEUTRAL)
        )
        
        # Scale intensity based on emotion value (1-5 → 0.2-1.0)
        intensity_scale = 0.2 + (emotion_value / 5) * 0.8
        
        # Adjust pattern intensity
        adjusted_steps = []
        for step in base_pattern.steps:
            adjusted_steps.append(
                VibrationStep(
                    min(step.intensity * intensity_scale, 1.0),
                    step.duration
                )
            )
            
        # Adjust repeat count based on emotion intensity
        repeat_scale = 1 + (emotion_value - 1) // 2  # 1-2 at low, 2-3 at high
        
        return VibrationPattern(
            steps=adjusted_steps,
            interval=base_pattern.interval,
            repeat_count=base_pattern.repeat_count * repeat_scale
        )
        
    @staticmethod
    def create_custom_pattern(
        pattern_type: str,
        intensity: float,
        duration_ms: int,
        repeat_count: int = 1
    ) -> VibrationPattern:
        """
        Create custom pattern by type
        
        Args:
            pattern_type: Type of pattern (pulse, wave, burst, fade)
            intensity: Base intensity (0.0-1.0)
            duration_ms: Total duration in milliseconds
            repeat_count: Number of repetitions
            
        Returns:
            Custom VibrationPattern
        """
        intensity = max(0.0, min(1.0, intensity))  # Clamp to valid range
        
        if pattern_type == "pulse":
            # ON/OFF pattern
            return VibrationPattern(
                steps=[
                    VibrationStep(intensity, duration_ms // 2),
                    VibrationStep(0.0, duration_ms // 2)
                ],
                interval=50,
                repeat_count=repeat_count
            )
            
        elif pattern_type == "wave":
            # Gradual increase/decrease
            return VibrationPattern(
                steps=[
                    VibrationStep(intensity * 0.3, duration_ms // 3),
                    VibrationStep(intensity * 0.7, duration_ms // 3),
                    VibrationStep(intensity, duration_ms // 3)
                ],
                interval=50,
                repeat_count=repeat_count
            )
            
        elif pattern_type == "burst":
            # Short intense bursts
            return VibrationPattern(
                steps=[
                    VibrationStep(intensity, 100),
                    VibrationStep(0.0, 50)
                ],
                interval=30,
                repeat_count=repeat_count * 3  # More repetitions for burst
            )
            
        elif pattern_type == "fade":
            # Gradually decreasing
            return VibrationPattern(
                steps=[
                    VibrationStep(intensity, duration_ms // 2),
                    VibrationStep(intensity * 0.5, duration_ms // 4),
                    VibrationStep(intensity * 0.2, duration_ms // 4)
                ],
                interval=50,
                repeat_count=repeat_count
            )
            
        else:
            # Default simple pattern
            return VibrationPattern(
                steps=[VibrationStep(intensity, duration_ms)],
                interval=0,
                repeat_count=repeat_count
            )
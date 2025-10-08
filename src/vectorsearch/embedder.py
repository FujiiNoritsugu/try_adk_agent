#!/usr/bin/env python3
"""
Embedding Generator for TouchInput and Emotion data
Uses Vertex AI Text Embedding API to convert interactions to vectors
"""

import os
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

try:
    from vertexai.language_models import TextEmbeddingModel
    import vertexai
    VERTEXAI_AVAILABLE = True
except ImportError:
    VERTEXAI_AVAILABLE = False
    logging.warning("Vertex AI SDK not installed. Install with: pip install google-cloud-aiplatform")


logger = logging.getLogger(__name__)


@dataclass
class TouchInput:
    """触覚入力データ"""
    data: float
    touched_area: str
    gesture_type: Optional[str] = None
    hand_velocity: Optional[float] = None
    leap_confidence: Optional[float] = None


@dataclass
class Emotion:
    """感情値"""
    joy: float
    fun: float
    anger: float
    sad: float


@dataclass
class InteractionRecord:
    """インタラクション記録"""
    id: str
    timestamp: str
    input: TouchInput
    emotion: Emotion
    response_text: str
    embedding: Optional[List[float]] = None
    session_id: Optional[str] = None

    def to_dict(self) -> Dict:
        """辞書に変換"""
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
            "input": {
                "data": self.input.data,
                "touched_area": self.input.touched_area,
                "gesture_type": self.input.gesture_type,
                "hand_velocity": self.input.hand_velocity,
                "leap_confidence": self.input.leap_confidence,
            },
            "emotion": {
                "joy": self.emotion.joy,
                "fun": self.emotion.fun,
                "anger": self.emotion.anger,
                "sad": self.emotion.sad,
            },
            "response_text": self.response_text,
            "embedding": self.embedding,
        }


class EmotionEmbedder:
    """感情履歴のEmbedding生成クラス"""

    def __init__(self, project_id: Optional[str] = None, location: str = "us-central1"):
        """
        Initialize the embedder

        Args:
            project_id: GCP Project ID (defaults to env var)
            location: GCP region for Vertex AI
        """
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = location
        self.model = None

        if not VERTEXAI_AVAILABLE:
            logger.warning("Vertex AI not available. Using mock embeddings.")
            return

        if not self.project_id:
            logger.warning("GOOGLE_CLOUD_PROJECT not set. Using mock embeddings.")
            return

        try:
            # Initialize Vertex AI
            vertexai.init(project=self.project_id, location=self.location)
            self.model = TextEmbeddingModel.from_pretrained("textembedding-gecko@003")
            logger.info("Vertex AI Text Embedding initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Vertex AI: {e}")
            logger.warning("Falling back to mock embeddings")

    def create_embedding_text(self,
                             input_data: TouchInput,
                             emotion: Emotion,
                             response_text: str) -> str:
        """
        Create text representation for embedding

        Args:
            input_data: Touch input data
            emotion: Emotion values
            response_text: Generated response text

        Returns:
            Formatted text for embedding
        """
        # 感情の強度を文字列化
        dominant_emotion = max(
            [("joy", emotion.joy), ("fun", emotion.fun),
             ("anger", emotion.anger), ("sad", emotion.sad)],
            key=lambda x: x[1]
        )[0]

        # 強度レベル
        intensity_level = "弱い" if input_data.data < 0.3 else "中程度" if input_data.data < 0.7 else "強い"

        # Embedding用のテキストを生成
        text = f"""触覚入力: 部位={input_data.touched_area}, 強度={intensity_level}({input_data.data:.2f})"""

        if input_data.gesture_type:
            text += f", ジェスチャー={input_data.gesture_type}"

        if input_data.hand_velocity:
            velocity_desc = "遅い" if input_data.hand_velocity < 100 else "普通" if input_data.hand_velocity < 200 else "速い"
            text += f", 速度={velocity_desc}"

        text += f"\n感情: {dominant_emotion}が優勢, 喜び={emotion.joy:.1f}, 楽しさ={emotion.fun:.1f}, 怒り={emotion.anger:.1f}, 悲しみ={emotion.sad:.1f}"
        text += f"\n応答: {response_text}"

        return text

    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector from text

        Args:
            text: Text to embed

        Returns:
            Embedding vector (768 dimensions)
        """
        if not self.model:
            # Mock embedding for testing
            logger.warning("Using mock embedding (768 dimensions of zeros)")
            return [0.0] * 768

        try:
            embeddings = self.model.get_embeddings([text])
            return embeddings[0].values
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            return [0.0] * 768

    def create_interaction_record(self,
                                 input_data: TouchInput,
                                 emotion: Emotion,
                                 response_text: str,
                                 session_id: Optional[str] = None) -> InteractionRecord:
        """
        Create a complete interaction record with embedding

        Args:
            input_data: Touch input data
            emotion: Emotion values
            response_text: Generated response text
            session_id: Optional session identifier

        Returns:
            Complete interaction record with embedding
        """
        # Generate unique ID
        timestamp = datetime.utcnow()
        record_id = f"interaction_{timestamp.strftime('%Y%m%d_%H%M%S')}_{hash(response_text) % 10000:04d}"

        # Create embedding text
        embedding_text = self.create_embedding_text(input_data, emotion, response_text)

        # Generate embedding
        embedding = self.generate_embedding(embedding_text)

        # Create record
        record = InteractionRecord(
            id=record_id,
            timestamp=timestamp.isoformat() + "Z",
            input=input_data,
            emotion=emotion,
            response_text=response_text,
            embedding=embedding,
            session_id=session_id
        )

        logger.info(f"Created interaction record: {record_id}")
        logger.debug(f"Embedding text: {embedding_text}")

        return record


# Example usage
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Create embedder
    embedder = EmotionEmbedder()

    # Example data
    touch_input = TouchInput(
        data=0.6,
        touched_area="頭",
        gesture_type="tap",
        hand_velocity=150.5,
        leap_confidence=0.9
    )

    emotion = Emotion(
        joy=4.0,
        fun=3.0,
        anger=0.5,
        sad=0.3
    )

    response_text = "優しく頭を触ってくれて嬉しいな"

    # Create record
    record = embedder.create_interaction_record(
        input_data=touch_input,
        emotion=emotion,
        response_text=response_text,
        session_id="test_session_001"
    )

    print(f"\nRecord ID: {record.id}")
    print(f"Embedding dimensions: {len(record.embedding)}")
    print(f"First 10 values: {record.embedding[:10]}")

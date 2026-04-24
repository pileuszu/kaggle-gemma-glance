import os
import mediapipe as mp
from mediapipe.tasks.python import genai
from PySide6.QtCore import QObject, Signal, Slot

class LLMWorker(QObject):
    response_ready = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, model_path="assets/models/gemma-4-e2b.tflite"):
        super().__init__()
        self.model_path = model_path
        self.llm = None
        self._initialize_llm()

    def _initialize_llm(self):
        if not os.path.exists(self.model_path):
            # We can't proceed without the model.
            # In a real app, we'd trigger a download here.
            print(f"Error: Model not found at {self.model_path}")
            return

        try:
            # MediaPipe LLM Inference API
            options = genai.LlmInferenceOptions(
                base_options=mp.tasks.BaseOptions(model_asset_path=self.model_path),
                max_tokens=128,
                top_k=40,
                temperature=0.7,
                random_seed=42
            )
            self.llm = genai.LlmInference.create_from_options(options)
            print("Gemma 4 E2B Engine initialized successfully.")
        except Exception as e:
            self.error_occurred.emit(str(e))
            print(f"Failed to initialize LLM: {e}")

    @Slot(str)
    def analyze_context(self, context_text):
        if not self.llm:
            self.error_occurred.emit("LLM not initialized.")
            return

        # Prompt engineering for Gemma 4 E2B
        prompt = (
            f"당신은 어려운 용어를 쉽게 설명해주는 전문가입니다. "
            f"다음 문장에서 마우스가 위치한 단어의 의미를 초등학생도 이해할 수 있게 한 문장으로 설명해주세요.\n"
            f"문맥: {context_text}\n"
            f"설명:"
        )

        try:
            response = self.llm.generate_response(prompt)
            self.response_ready.emit(response.strip())
        except Exception as e:
            self.error_occurred.emit(str(e))

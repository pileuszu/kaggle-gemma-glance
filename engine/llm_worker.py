import os
import threading
import json
import numpy as np
import onnxruntime as ort
from PySide6.QtCore import QObject, Signal, Slot
from transformers import AutoConfig, AutoProcessor, GenerationConfig

class LLMWorker(QObject):
    response_ready = Signal(str)
    partial_response = Signal(str)
    error_occurred = Signal(str)

    def __init__(self):
        super().__init__()
        self.vision_session = None
        self.embed_session = None
        self.decoder_session = None
        self.processor = None
        self.config = None
        self.generation_config = None
        self.stop_requested = False
        self.lock = threading.Lock()

    def _initialize_llm(self):
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            model_dir = os.path.join(base_dir, "assets", "models", "onnx")
            onnx_dir = os.path.join(model_dir, "onnx")
            
            if not os.path.exists(model_dir):
                raise FileNotFoundError(f"모델 디렉토리를 찾을 수 없습니다: {model_dir}")

            print(f"[Gemma] 저수준 세션 로드 시작: {model_dir}")
            
            # 1. Config 및 Processor 로드
            self.processor = AutoProcessor.from_pretrained(model_dir)
            self.config = AutoConfig.from_pretrained(model_dir)
            self.generation_config = GenerationConfig.from_pretrained(model_dir)
            
            # 2. ONNX 세션 로드 (사용자 요청에 따라 CPU 전용 설정)
            providers = ['CPUExecutionProvider']
            
            self.vision_session = ort.InferenceSession(os.path.join(onnx_dir, "vision_encoder_q4.onnx"), providers=providers)
            self.embed_session = ort.InferenceSession(os.path.join(onnx_dir, "embed_tokens_q4.onnx"), providers=providers)
            self.decoder_session = ort.InferenceSession(os.path.join(onnx_dir, "decoder_model_merged_q4.onnx"), providers=providers)
            
            print(f"[Gemma] 모든 세션 로드 완료 (가속: {self.decoder_session.get_providers()[0]})")
        except Exception as e:
            self.error_occurred.emit(f"모델 초기화 실패: {str(e)}")

    def stop(self):
        self.stop_requested = True

    def analyze_multimodal(self, image, unused_title=""):
        if not self.decoder_session: return
        if not self.lock.acquire(blocking=False): return
        
        self.stop_requested = False
        try:
            # 1. 입력 메시지 구성
            prompt = "이미지 중앙에 겹쳐진 반투명한 빨간색 원이 가리키는 단어가 무엇인지 한국어로 설명해주세요."
            messages = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": prompt}]}]
            
            # 2. 전처리 (이미지를 명시적으로 전달하여 이미지 토큰 생성 강제)
            prompt_text = self.processor.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
            inputs = self.processor(text=[prompt_text], images=[image], return_tensors="pt")
            
            # 프로세서가 생성한 모든 키와 그 형태를 로그로 출력
            print("--- 프로세서 출력 정보 ---")
            for k, v in inputs.items():
                shape = v.shape if hasattr(v, 'shape') else 'no shape'
                print(f"Key: {k}, Shape: {shape}")
            print("-------------------------")
            
            input_ids = inputs["input_ids"].numpy()
            attention_mask = inputs["attention_mask"].numpy()
            position_ids = np.cumsum(attention_mask, axis=-1) - 1
            pixel_values = inputs["pixel_values"].numpy() if "pixel_values" in inputs else None
            # 이름 매핑: image_position_ids -> pixel_position_ids
            pixel_position_ids = inputs.get("image_position_ids", inputs.get("pixel_position_ids", None))
            if pixel_position_ids is not None: pixel_position_ids = pixel_position_ids.numpy()
            
            print(f"[디버그] 전처리 완료. input_ids 크기: {input_ids.shape}, 이미지 데이터: {pixel_values.shape if pixel_values is not None else 'None'}, 위치 ID: {pixel_position_ids.shape if pixel_position_ids is not None else 'None'}")
            
            image_token_id = self.config.image_token_id
            eos_token_ids = self.generation_config.eos_token_id
            if isinstance(eos_token_ids, int): eos_token_ids = [eos_token_ids]

            # 3. 임베딩 및 비전 특징 추출
            inputs_embeds, per_layer_inputs = self.embed_session.run(None, {"input_ids": input_ids})
            
            if pixel_values is not None:
                print(f"[디버그] 비전 특징 추출 중... (입력 형태: {pixel_values.shape})")
                vision_inputs = {"pixel_values": pixel_values}
                if pixel_position_ids is not None:
                    vision_inputs["pixel_position_ids"] = pixel_position_ids
                
                image_features = self.vision_session.run(["image_features"], vision_inputs)[0]
                print(f"[디버그] 비전 특징 추출 완료: {image_features.shape}")
                
                # 이미지 토큰 위치 찾기 및 교체
                mask = (input_ids == image_token_id).reshape(-1)
                num_image_tokens = np.sum(mask)
                print(f"[디버그] 발견된 이미지 토큰 수: {num_image_tokens}")
                
                if num_image_tokens > 0:
                    flat_embeds = inputs_embeds.reshape(-1, inputs_embeds.shape[-1])
                    
                    # Gemma 4의 경우, 이미지 특징(2520개 등)이 이미지 토큰(보통 다수) 위치에 순차적으로 들어갑니다.
                    # 만약 이미지 토큰 수가 부족하다면, 모델 아키텍처에 따라 토큰 위치를 확장해야 할 수 있습니다.
                    if len(image_features) >= num_image_tokens:
                        flat_embeds[mask] = image_features[:num_image_tokens]
                        print(f"[디버그] 이미지 특징 {num_image_tokens}개 주입 성공")
                    else:
                        # 특징이 더 적을 경우 (드문 케이스)
                        flat_embeds[mask][:len(image_features)] = image_features
                        print(f"[경고] 이미지 특징 일부만 주입됨 ({len(image_features)}/{num_image_tokens})")
                    
                    inputs_embeds = flat_embeds.reshape(inputs_embeds.shape)
                else:
                    print("[경고] input_ids 내에서 이미지 토큰을 찾을 수 없습니다. 분석 품질이 저하될 수 있습니다.")
                    print(f"[디버그] 현재 input_ids: {input_ids}")
                    print(f"[디버그] 타겟 image_token_id: {image_token_id}")

            # 4. 생성 루프 준비
            batch_size = input_ids.shape[0]
            num_logits_to_keep = np.array(1, dtype=np.int64)
            
            # KV 캐시 초기화
            past_key_values = {
                inp.name: np.zeros(
                    [batch_size, inp.shape[1], 0, inp.shape[3]],
                    dtype=np.float32 if inp.type == "tensor(float)" else np.float16,
                )
                for inp in self.decoder_session.get_inputs()
                if inp.name.startswith("past_key_values")
            }

            full_response = ""
            max_new_tokens = 512
            
            # 5. 생성 루프 시작
            for i in range(max_new_tokens):
                if self.stop_requested: break
                
                # 디코더 실행
                decoder_inputs = {
                    "inputs_embeds": inputs_embeds,
                    "attention_mask": attention_mask,
                    "per_layer_inputs": per_layer_inputs,
                    "position_ids": position_ids,
                    "num_logits_to_keep": num_logits_to_keep,
                    **past_key_values
                }
                
                outputs = self.decoder_session.run(None, decoder_inputs)
                logits = outputs[0]
                present_key_values = outputs[1:]
                
                # 다음 토큰 선택
                next_token_id = logits[:, -1].argmax(-1, keepdims=True)
                
                # 토큰 디코딩 및 전송
                text = self.processor.decode(next_token_id[0], skip_special_tokens=True)
                full_response += text
                self.partial_response.emit(text)
                
                # 종료 조건 확인
                if np.isin(next_token_id, eos_token_ids).any():
                    break
                
                # 다음 단계 준비 (KV 캐시 업데이트)
                inputs_embeds, per_layer_inputs = self.embed_session.run(None, {"input_ids": next_token_id})
                attention_mask = np.concatenate([attention_mask, np.ones_like(next_token_id)], axis=-1)
                position_ids = position_ids[:, -1:] + 1
                
                # KV 캐시 딕셔너리 업데이트
                for j, key in enumerate(past_key_values):
                    past_key_values[key] = present_key_values[j]

            if not self.stop_requested:
                self.response_ready.emit(full_response.strip())
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error_occurred.emit(f"분석 중 오류 발생: {str(e)}")
        finally:
            self.lock.release()

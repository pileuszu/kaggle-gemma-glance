import kagglehub
import os
import shutil

def download_gemma():
    print("Gemma 4 E2B 모델 다운로드를 시작합니다...")
    try:
        # 공식 경로 (실제 경로 확인 필요)
        path = kagglehub.model_download("google/gemma-4/transformers/gemma-4-e2b-it")
        
        target_dir = "assets/models"
        if not os.path.exists(target_dir):
            os.makedirs(target_dir)
            
        # .tflite 파일을 찾아서 이동
        found = False
        for root, dirs, files in os.walk(path):
            for file in files:
                if file.endswith(".tflite"):
                    shutil.copy(os.path.join(root, file), os.path.join(target_dir, "gemma-4-e2b.tflite"))
                    print(f"모델 파일이 {target_dir}/gemma-4-e2b.tflite 로 복사되었습니다.")
                    found = True
                    break
        
        if not found:
            print("경고: 다운로드된 폴더에서 .tflite 파일을 찾을 수 없습니다. 수동으로 확인이 필요합니다.")
            print(f"다운로드 경로: {path}")
            
    except Exception as e:
        print(f"다운로드 중 오류 발생: {e}")
        print("Kaggle 로그인 상태를 확인하거나 라이선스 동의 여부를 확인하세요.")

if __name__ == "__main__":
    download_gemma()

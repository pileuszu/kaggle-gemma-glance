import kagglehub
import os
import shutil

def download_gemma_onnx():
    print("Gemma 4 E2B ONNX 모델 다운로드를 시작합니다...")
    try:
        # 공식 ONNX 경로
        path = kagglehub.model_download("google/gemma-4/onnx/gemma-4-e2b-it-onnx")
        
        target_dir = "assets/models/onnx"
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
        
        os.makedirs(target_dir, exist_ok=True)
            
        # 다운로드된 모든 파일을 target_dir로 복사/이동
        print(f"다운로드 완료. 파일을 {target_dir} 로 구성 중...")
        
        for item in os.listdir(path):
            s = os.path.join(path, item)
            d = os.path.join(target_dir, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
            else:
                shutil.copy2(s, d)
        
        print("Gemma 4 ONNX 모델 구성이 완료되었습니다!")
        print(f"위치: {os.path.abspath(target_dir)}")
            
    except Exception as e:
        print(f"다운로드 중 오류 발생: {e}")
        print("Kaggle 로그인 상태를 확인하거나 라이선스 동의 여부를 확인하세요.")

if __name__ == "__main__":
    download_gemma_onnx()

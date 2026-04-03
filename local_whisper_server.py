import os
import sys
import logging
import tempfile
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_dependencies():
    try:
        import fastapi
        import uvicorn
        import whisper
        return True
    except ImportError as e:
        logger.error(f"缺少依赖: {e}")
        logger.error("请运行: pip install fastapi uvicorn python-multipart openai-whisper")
        return False

def main():
    if not check_dependencies():
        sys.exit(1)
    
    from fastapi import FastAPI, UploadFile, File
    from fastapi.responses import JSONResponse
    import uvicorn
    import whisper
    
    app = FastAPI(title="Local Whisper API")
    
    whisper_model = None
    
    def get_model():
        nonlocal whisper_model
        if whisper_model is None:
            logger.info("加载 Whisper 模型 (small)...")
            whisper_model = whisper.load_model("small")
            logger.info("模型加载完成")
        return whisper_model
    
    @app.on_event("startup")
    async def startup_event():
        logger.info("启动本地 Whisper API 服务...")
        get_model()
        logger.info("服务已启动: http://127.0.0.1:7860")
    
    @app.post("/api/transcribe")
    async def transcribe_audio(file: UploadFile = File(...)):
        try:
            model = get_model()
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                content = await file.read()
                tmp.write(content)
                tmp_path = tmp.name
            
            logger.info(f"正在识别音频: {file.filename or 'unknown'}")
            
            result = model.transcribe(tmp_path)
            
            text = result.get("text", "")
            
            try:
                os.unlink(tmp_path)
            except:
                pass
            
            logger.info(f"识别完成: {text[:50]}...")
            
            return {"text": text}
            
        except Exception as e:
            logger.error(f"识别错误: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": str(e)}
            )
    
    @app.get("/")
    async def root():
        return {"status": "running", "model": "whisper-small"}
    
    print("=" * 60)
    print("本地 Whisper API 服务")
    print("=" * 60)
    print()
    print("提供本地语音识别服务，无需网络连接。")
    print()
    print("使用方法:")
    print("  1. 启动此服务: python local_whisper_server.py")
    print("  2. 在主应用设置中启用 '使用本地 Whisper 模型'")
    print("  3. 主应用将使用此本地服务进行语音识别")
    print()
    print("API 端点:")
    print("  POST /api/transcribe - 上传音频文件进行识别")
    print("  GET / - 健康检查")
    print()
    print("服务地址: http://127.0.0.1:7860")
    print("=" * 60)
    print()
    
    uvicorn.run(app, host="127.0.0.1", port=7860, log_level="info")

if __name__ == "__main__":
    main()

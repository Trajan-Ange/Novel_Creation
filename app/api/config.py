"""API configuration endpoints."""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.services.llm import save_config

router = APIRouter(prefix="/api/config", tags=["config"])


class ConfigUpdate(BaseModel):
    api_key: str = ""
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 4096


@router.get("")
async def get_config(request: Request):
    """Return current config with API key masked."""
    config = dict(request.app.state.llm.config)
    if config.get("api_key"):
        key = config["api_key"]
        config["api_key"] = key[:8] + "****" + key[-4:] if len(key) > 12 else "****"
    config["is_configured"] = request.app.state.llm.is_configured()
    return config


@router.put("")
async def update_config(request: Request, body: ConfigUpdate):
    """Update LLM configuration and save to config.json."""
    config = body.model_dump()
    if not config.get("api_key"):
        existing = request.app.state.llm.config
        config["api_key"] = existing.get("api_key", "")
    save_config(request.app.state.config_path, config)
    request.app.state.llm.update_config(config)
    return {"success": True, "message": "配置已保存"}


@router.post("/test")
async def test_connection(request: Request):
    """Test the LLM connection."""
    llm = request.app.state.llm
    if not llm.is_configured():
        raise HTTPException(status_code=422, detail={"success": False, "error": "请先配置 API 密钥和地址"})
    try:
        response = await llm.chat(
            system_prompt="You are a helpful assistant.",
            user_message="Reply with just the word 'OK'.",
            max_tokens=10,
            temperature=0,
        )
        return {"success": True, "message": response.strip()}
    except Exception as e:
        error_msg = str(e)
        if "401" in error_msg or "Unauthorized" in error_msg:
            error_msg = "API 密钥无效（401 Unauthorized）"
        elif "404" in error_msg:
            error_msg = "API 地址或模型名称无效（404 Not Found）"
        elif "timeout" in error_msg.lower() or "connect" in error_msg.lower():
            error_msg = "无法连接到 API 服务器"
        raise HTTPException(status_code=500, detail={"success": False, "error": error_msg})

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api import router, get_spider_proxy_settings, SPIDER_PROXY_FILE, SPIDER_PROXY_CONFIG_FILE
from app.spider_instance import spider_manager
import os

class UnicodeJSONResponse(JSONResponse):
    def render(self, content) -> bytes:
        import json
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")

app = FastAPI(
    title="TVBox 爬虫后端服务",
    description="实现 TVBox type: 3 爬虫源功能的后端服务",
    version="1.0.0",
    default_response_class=UnicodeJSONResponse
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")

@app.on_event("startup")
async def startup_event():
    """启动时加载代理配置"""
    settings = get_spider_proxy_settings()
    if settings.enabled:
        proxy_config = {}
        if settings.http_proxy:
            proxy_config['http'] = settings.http_proxy
        if settings.https_proxy:
            proxy_config['https'] = settings.https_proxy
        
        if proxy_config:
            spider_manager.set_proxy_config(proxy_config)
            config_source = "运行时配置" if os.path.exists(SPIDER_PROXY_FILE) else "GitHub配置文件"
            print(f"启动时加载代理配置 ({config_source}): {proxy_config}")

@app.get("/")
async def root():
    return {
        "message": "TVBox 爬虫后端服务",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# TVBox 爬虫后端服务

基于 FastAPI 的后端服务，用于实现 TVBox type: 3 爬虫源功能。

## 功能特性

- 加载和执行 Python 爬虫脚本
- 提供与 TVBox 兼容的 RESTful API 接口
- 支持多爬虫实例管理
- 支持远程加载和本地上传爬虫脚本
- 支持 GitHub 同步管理爬虫
- 内置缓存机制提升性能
- 支持 Cloudflare Workers 图片代理加速

## 技术栈

- Python 3.10+
- FastAPI
- uvicorn
- requests
- pycryptodome

## 项目结构

```
Fastapi/
├── app/
│   ├── __init__.py
│   ├── main.py              # 主应用入口
│   ├── api.py               # API 路由
│   ├── spider_manager.py    # 爬虫管理器
│   ├── spider_instance.py   # 爬虫实例
│   ├── tvbox_parser.py      # TVBox配置解析器
│   ├── base/
│   │   ├── __init__.py
│   │   └── spider.py        # 爬虫基类
│   └── spiders/             # 爬虫脚本目录
│       ├── __init__.py
│       ├── spiders.json     # 爬虫配置文件
│       └── *.py             # 爬虫脚本文件
├── requirements.txt
├── Dockerfile
├── DEPLOY.md                # 部署说明
└── README.md
```

## 快速开始

### 本地开发

```bash
cd Fastapi
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 使用 Docker

```bash
docker build -t tvbox-backend .
docker run -p 8000:8000 tvbox-backend
```

### 访问接口

- 文档: `http://localhost:8000/docs`
- 健康检查: `http://localhost:8000/health`
- API 接口: `http://localhost:8000/api/`

## 爬虫管理

### 方式一：手动添加文件（推荐）

1. 将爬虫脚本 `.py` 文件放入 `app/spiders/` 目录
2. 在 `app/spiders/spiders.json` 中添加配置：

```json
{
  "my-spider": {
    "key": "my-spider",
    "name": "我的爬虫",
    "enabled": true,
    "source": "upload",
    "script_url": "",
    "file_path": "app/spiders/my-spider.py"
  }
}
```

3. 重启服务或调用重新加载 API

### 方式二：通过 API 添加

```bash
# 添加远程爬虫
curl -X POST http://localhost:8000/api/add-python-spider \
  -H "Content-Type: application/json" \
  -d '{"key": "my-spider", "script_url": "https://example.com/spider.py", "name": "我的爬虫"}'

# 上传本地爬虫
curl -X POST http://localhost:8000/api/upload-spider \
  -F "key=my-spider" \
  -F "file=@spider.py" \
  -F "name=我的爬虫"
```

### 方式三：GitHub 同步

详见 [DEPLOY.md](./DEPLOY.md)

## API 接口

### 视频数据接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/classify` | GET | 获取分类列表 |
| `/api/videos?t={分类ID}&pg={页码}` | GET | 获取分类下的视频列表 |
| `/api/detail?id={视频ID}` | GET | 获取视频详情 |
| `/api/search?kw={关键词}&pg={页码}` | GET | 搜索视频 |
| `/api/playurl?flag={播放源}&id={视频链接}` | GET | 获取播放地址 |

### 爬虫管理接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/spiders` | GET | 获取爬虫列表 |
| `/api/spiders/reload-all` | POST | 重新加载所有爬虫 |
| `/api/spiders/{key}/reload` | POST | 重新加载单个爬虫 |
| `/api/spiders/{key}` | DELETE | 删除爬虫 |
| `/api/add-python-spider` | POST | 添加远程爬虫 |
| `/api/upload-spider` | POST | 上传本地爬虫 |

### Webhook 接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/webhook/github` | POST | GitHub Webhook 自动同步 |

## 部署

详见 [DEPLOY.md](./DEPLOY.md)

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `CACHE_TTL` | 缓存过期时间（秒） | 300 |
| `MAX_WORKERS` | 最大并发数 | 10 |
| `PROXY_URL` | 代理服务器地址 | - |
| `WEBHOOK_SECRET` | GitHub Webhook 密钥 | - |

## 爬虫开发

爬虫需要继承 `Spider` 基类并实现以下方法：

```python
from app.base.spider import Spider

class Spider(Spider):
    def init(self):
        pass
    
    def getName(self):
        return "爬虫名称"
    
    def homeContent(self, filter):
        # 返回首页分类和筛选条件
        pass
    
    def categoryContent(self, tid, pg, filter, extend):
        # 返回分类下的视频列表
        pass
    
    def detailContent(self, ids):
        # 返回视频详情
        pass
    
    def searchContent(self, keyword, quick):
        # 返回搜索结果
        pass
    
    def playerContent(self, flag, id, vipFlags):
        # 返回播放地址
        pass
```

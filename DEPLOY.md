# 后端部署说明

## 目录
- [Zeabur 部署（推荐）](#zeabur-部署推荐)
- [GitHub 同步配置](#github-同步配置)
- [Vercel 部署](#vercel-部署)
- [其他平台](#其他平台)

---

## Zeabur 部署（推荐）

### 1. 准备工作
确保项目已推送到 GitHub 仓库。

### 2. 部署步骤

1. 登录 [Zeabur](https://zeabur.com)
2. 创建新项目，选择 GitHub 仓库
3. Zeabur 会自动检测 FastAPI 项目
4. 设置根目录为 `Fastapi`
5. 部署

### 3. 环境变量（可选）
在 Zeabur 控制台设置环境变量：
- `WEBHOOK_SECRET` - GitHub Webhook 密钥（增强安全性）

### 4. 部署后配置
部署成功后，Zeabur 会提供一个域名，例如：
`https://your-app.zeabur.app`

API 端点：
- 健康检查: `GET /health`
- 爬虫列表: `GET /spiders`
- 重新加载: `POST /spiders/reload-all`
- Webhook: `POST /webhook/github`

---

## GitHub 同步配置

### 工作流程
```
本地修改爬虫 → 推送 GitHub → Zeabur 自动拉取 → 服务重启 → 爬虫自动加载
```

### 方式一：自动重启（推荐）

Zeabur 会在检测到 GitHub 推送后自动拉取代码并重启服务，爬虫会在启动时自动加载，无需额外配置。

### 方式二：Webhook 热更新（不重启服务）

如果不想重启服务，可以配置 GitHub Webhook 实现热更新：

1. 在 GitHub 仓库中：**Settings → Webhooks → Add webhook**
2. 配置：
   - Payload URL: `https://your-backend.zeabur.app/webhook/github`
   - Content type: `application/json`
   - Secret: 可选
   - Events: `Just the push event`
3. 保存

### 手动重新加载
```bash
curl -X POST https://your-backend.zeabur.app/spiders/reload-all
```

### 爬虫文件管理

爬虫文件位置：`Fastapi/app/spiders/`

**添加新爬虫：**
1. 将 `.py` 文件放入 `Fastapi/app/spiders/` 目录
2. 修改 `Fastapi/app/spiders/spiders.json`：
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
3. 推送到 GitHub

---

## Vercel 部署

### 限制
⚠️ **注意**：Vercel 有以下限制：
- Serverless 函数执行时间限制（Hobby: 10秒，Pro: 60秒）
- 不支持 WebSocket
- 文件系统只读（爬虫持久化受限）
- 动态加载 Python 模块可能失败

### 部署步骤

#### 方法1：CLI
```bash
cd Fastapi
npm i -g vercel
vercel login
vercel
```

#### 方法2：Dashboard
1. 将代码推送到 GitHub
2. 在 Vercel Dashboard 导入项目
3. 设置根目录为 `Fastapi`
4. 部署

---

## 其他平台

### Railway
- 完整 FastAPI 支持
- 支持持久化存储
- 推荐用于生产环境

### Render
- 免费计划可用
- 支持长时间运行
- 自动从 GitHub 部署

### Fly.io
- 全球部署
- 支持 WebSocket
- 需要信用卡验证

---

## API 端点列表

| 端点 | 方法 | 说明 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/spiders` | GET | 获取爬虫列表 |
| `/spiders/reload-all` | POST | 重新加载所有爬虫 |
| `/spiders/{key}/reload` | POST | 重新加载单个爬虫 |
| `/webhook/github` | POST | GitHub Webhook |

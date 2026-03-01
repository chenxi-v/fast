from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Response
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from app.spider_instance import spider_manager
from app.tvbox_parser import TVBoxConfigParser
import json
import os
import shutil

router = APIRouter()

@router.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "ok"}

class ImportTVBoxConfigRequest(BaseModel):
    config_url: str

class AddPythonSpiderRequest(BaseModel):
    key: str
    script_url: str
    name: Optional[str] = None

class StandardEpisode(BaseModel):
    name: str
    url: str
    index: int

class StandardVideoDetail(BaseModel):
    vod_id: str
    vod_name: str
    vod_pic: str
    vod_remarks: str
    vod_actor: str
    vod_director: str
    vod_year: str
    vod_area: str
    vod_content: str
    type_name: str
    episodes: List[StandardEpisode]

class StandardVideoItem(BaseModel):
    vod_id: str
    vod_name: str
    vod_pic: str
    vod_remarks: str

class StandardPlayUrl(BaseModel):
    url: str
    header: Dict[str, str] = {}

def parse_episodes(vod_play_url: str, vod_play_from: str = "") -> List[StandardEpisode]:
    """解析播放链接，返回标准化的集数列表"""
    if not vod_play_url:
        return []
    
    episodes = []
    
    if isinstance(vod_play_url, list):
        vod_play_url = '#'.join(vod_play_url)
    
    parts = vod_play_url.split('#')
    
    for index, part in enumerate(parts):
        part = part.strip()
        if not part:
            continue
        
        if '$' in part:
            name, url = part.split('$', 1)
            name = name.strip()
            url = url.strip()
        else:
            name = f"第{index + 1}集"
            url = part.strip()
        
        if url:
            url = url.replace('\\', '')
            episodes.append(StandardEpisode(
                name=name,
                url=url,
                index=index
            ))
    
    return episodes

def normalize_video_list(video_list: List[Dict], spider_key: str = "") -> List[Dict]:
    """标准化视频列表数据"""
    result = []
    for video in video_list:
        vod_id = str(video.get('vod_id', ''))
        if spider_key and not vod_id.startswith(f"{spider_key}_"):
            vod_id = f"{spider_key}_{vod_id}" if spider_key else vod_id
        
        result.append({
            'vod_id': vod_id,
            'vod_name': video.get('vod_name', ''),
            'vod_pic': video.get('vod_pic', ''),
            'vod_remarks': video.get('vod_remarks', '')
        })
    return result

def normalize_video_detail(video_detail: Dict, spider_key: str = "") -> Dict:
    """标准化视频详情数据"""
    vod_id = str(video_detail.get('vod_id', ''))
    if spider_key and not vod_id.startswith(f"{spider_key}_"):
        vod_id = f"{spider_key}_{vod_id}" if spider_key else vod_id
    
    vod_play_url = video_detail.get('vod_play_url', '')
    vod_play_from = video_detail.get('vod_play_from', '')
    
    episodes = parse_episodes(vod_play_url, vod_play_from)
    
    return {
        'vod_id': vod_id,
        'vod_name': video_detail.get('vod_name', ''),
        'vod_pic': video_detail.get('vod_pic', ''),
        'vod_remarks': video_detail.get('vod_remarks', ''),
        'vod_actor': video_detail.get('vod_actor', ''),
        'vod_director': video_detail.get('vod_director', ''),
        'vod_year': video_detail.get('vod_year', ''),
        'vod_area': video_detail.get('vod_area', ''),
        'vod_content': video_detail.get('vod_content', ''),
        'type_name': video_detail.get('type_name', ''),
        'episodes': [ep.model_dump() for ep in episodes]
    }

def normalize_play_url(play_result: Dict) -> Dict:
    """标准化播放地址数据"""
    url = play_result.get('url', '')
    header = play_result.get('header', {})
    
    if isinstance(header, dict):
        header = {k: str(v) for k, v in header.items()}
    else:
        header = {}
    
    return {
        'url': url,
        'header': header
    }

@router.get("/classify")
async def get_classify():
    """获取分类列表"""
    try:
        spiders = spider_manager.get_all_spiders()
        result = []
        
        for key, spider_info in spiders.items():
            spider = spider_info['instance']
            classify_list = spider.homeVideoContent().get('class', [])
            for cls in classify_list:
                cls['key'] = key  # 添加爬虫标识
            result.extend(classify_list)
        
        return {
            "code": 0,
            "msg": "success",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/videos")
async def get_videos(t: str = Query(..., description="分类ID"), pg: int = Query(1, description="页码")):
    """获取分类下的视频列表"""
    try:
        # 这里需要解析t参数获取爬虫key和分类ID
        spider_key = t.split('_')[0] if '_' in t else t
        cate_id = t
        
        spider_info = spider_manager.get_spider(spider_key)
        if not spider_info:
            raise HTTPException(status_code=404, detail="Spider not found")
        
        spider = spider_info['instance']
        result = spider.categoryContent(cate_id, str(pg), False, "")
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/detail")
async def get_detail(id: str = Query(..., description="视频ID")):
    """获取视频详情"""
    try:
        # 解析ID获取爬虫key和视频ID
        parts = id.split('_', 1)
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="Invalid video ID format")
        
        spider_key, video_id = parts
        
        spider_info = spider_manager.get_spider(spider_key)
        if not spider_info:
            raise HTTPException(status_code=404, detail="Spider not found")
        
        spider = spider_info['instance']
        result = spider.detailContent([video_id])
        
        # 标准化视频详情
        if result.get('list'):
            normalized_data = normalize_video_detail(result['list'][0])
            result['list'][0] = normalized_data
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/playurl")
async def get_play_url(flag: str = Query(..., description="播放源"), id: str = Query(..., description="视频链接")):
    """获取播放地址"""
    try:
        # 解析ID获取爬虫key和播放链接
        parts = id.split('_', 1)
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="Invalid video ID format")
        
        spider_key, play_url = parts
        
        spider_info = spider_manager.get_spider(spider_key)
        if not spider_info:
            raise HTTPException(status_code=404, detail="Spider not found")
        
        spider = spider_info['instance']
        result = spider.playerContent(flag, play_url, [])
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search")
async def search(kw: str = Query(..., description="搜索关键词"), pg: int = Query(1, description="页码")):
    """搜索视频"""
    try:
        result = {"code": 0, "msg": "success", "data": []}
        
        # 在所有爬虫中搜索
        spiders = spider_manager.get_all_spiders()
        for key, spider_info in spiders.items():
            spider = spider_info['instance']
            try:
                search_result = spider.searchContent(kw, str(pg))
                
                # 如果搜索结果不为空，添加到最终结果中
                if search_result and search_result.get('list'):
                    for video in search_result['list']:
                        # 为视频ID添加爬虫标识前缀
                        if 'vod_id' in video:
                            video['vod_id'] = f"{key}_{video['vod_id']}"
                        result['data'].append(video)
            except:
                # 如果某个爬虫搜索失败，继续下一个
                continue
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/import-tvbox-config")
async def import_tvbox_config(request: ImportTVBoxConfigRequest):
    """导入 TVBox 配置"""
    try:
        parser = TVBoxConfigParser()
        config = parser.load_config(request.config_url)
        
        # 将配置中的爬虫添加到管理器
        for key, spider_config in config.items():
            if spider_config.get('type') == 'python':
                spider_manager.add_python_spider(key, spider_config['script_url'])
        
        return {"code": 0, "msg": "success", "data": config}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/add-python-spider")
async def add_python_spider(request: AddPythonSpiderRequest):
    """添加 Python 爬虫"""
    try:
        spider_manager.add_python_spider(request.key, request.script_url, request.name)
        return {"code": 0, "msg": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/spiders/upload")
async def upload_python_spider(key: str = Query(..., description="爬虫标识"), name: str = Query(None, description="爬虫名称"), file: UploadFile = File(..., description="Python爬虫文件")):
    """上传 Python 爬虫文件"""
    try:
        # 检查文件类型
        if not file.filename.endswith('.py'):
            raise HTTPException(status_code=400, detail="文件必须是 .py 格式")
        
        # 读取文件内容
        content = await file.read()
        file_content = content.decode('utf-8')
        
        # 保存文件到spiders目录
        spiders_dir = os.path.join(os.path.dirname(__file__), "spiders")
        if not os.path.exists(spiders_dir):
            os.makedirs(spiders_dir)
        
        file_path = os.path.join(spiders_dir, f"{key}.py")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(file_content)
        
        # 添加爬虫到管理器
        spider_manager.add_local_spider(key, file_path, name)
        
        return {"code": 0, "msg": "success", "data": {"key": key, "filename": file.filename}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class UpdateSpiderRequest(BaseModel):
    new_key: Optional[str] = None
    new_name: Optional[str] = None


@router.put("/spiders/{key}")
async def update_spider(key: str, request: UpdateSpiderRequest):
    """更新爬虫信息"""
    try:
        updated_key = spider_manager.update_spider(key, request.new_key, request.new_name)
        return {"code": 0, "msg": "success", "data": {"key": updated_key}}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/spider/{key}")
async def spider_api(
    key: str, 
    act: str = Query(None), 
    t: str = Query(None), 
    pg: str = Query("1"), 
    wd: str = Query(None),
    fl: str = Query(None),
    extend: str = Query(None),
    flag: str = Query(""),
    ids: str = Query(None)
):
    """
    单个爬虫API端点，返回标准化数据格式
    :param key: 爬虫标识
    :param act: 操作类型 (home/category/detail/search/play)
    :param t: 分类ID或视频ID或播放ID
    :param pg: 页码
    :param wd: 搜索关键词
    :param fl: 筛选参数
    :param extend: 筛选参数 (TVBox标准格式)
    :param flag: 播放源标识
    :param ids: 视频ID (detail操作的别名参数)
    """
    try:
        spider_info = spider_manager.get_spider(key)
        if not spider_info:
            raise HTTPException(status_code=404, detail=f"Spider '{key}' not found")
        
        spider = spider_info['instance']
        
        if act == "home":
            result = spider.homeContent(True)
            class_list = result.get('class', [])
            return {"code": 0, "msg": "success", "data": {"categories": class_list}}
        
        elif act == "homev2":
            result = spider.homeContent(False)
            class_list = result.get('class', [])
            return {"code": 0, "msg": "success", "data": {"categories": class_list}}
        
        elif act == "category":
            if t is None:
                raise HTTPException(status_code=400, detail="缺少分类ID参数t")
            
            extend_params = {}
            filter_param = extend or fl
            if filter_param:
                try:
                    import json
                    extend_params = json.loads(filter_param)
                except:
                    extend_params = {'fl': fl}
            
            result = spider.categoryContent(t, pg, False, extend_params)
            video_list = result.get('list', [])
            normalized_list = normalize_video_list(video_list, key)
            return {"code": 0, "msg": "success", "data": {"videos": normalized_list}}
        
        elif act == "detail":
            video_id = t or ids
            if video_id is None:
                raise HTTPException(status_code=400, detail="缺少视频ID参数t或ids")
            
            if '_' in str(video_id):
                _, video_id = str(video_id).split('_', 1)
            
            result = spider.detailContent([video_id])
            video_list = result.get('list', [])
            if video_list:
                video_data = video_list[0]
                if not video_data.get('vod_id'):
                    video_data['vod_id'] = video_id
                normalized_detail = normalize_video_detail(video_data, key)
                return {"code": 0, "msg": "success", "data": normalized_detail}
            return {"code": 1, "msg": "视频详情为空", "data": None}
        
        elif act == "search":
            if wd is None:
                raise HTTPException(status_code=400, detail="缺少搜索关键词参数wd")
            result = spider.searchContent(wd, '', pg)
            video_list = result.get('list', [])
            normalized_list = normalize_video_list(video_list, key)
            return {"code": 0, "msg": "success", "data": {"videos": normalized_list}}
        
        elif act == "play":
            if t is None:
                raise HTTPException(status_code=400, detail="缺少播放ID参数t")
            result = spider.playerContent(flag, t, [])
            normalized_play = normalize_play_url(result)
            return {"code": 0, "msg": "success", "data": normalized_play}
        
        else:
            result = spider.homeContent(True)
            class_list = result.get('class', [])
            return {"code": 0, "msg": "success", "data": {"categories": class_list}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/spiders/{key}")
async def delete_spider(key: str):
    """
    删除爬虫
    :param key: 爬虫标识
    """
    try:
        spider_info = spider_manager.get_spider(key)
        if not spider_info:
            raise HTTPException(status_code=404, detail=f"Spider '{key}' not found")
        
        # 从管理器中移除爬虫（spider_manager.remove_spider 会处理文件删除）
        spider_manager.remove_spider(key)
        
        return {"code": 0, "msg": "success", "data": {"key": key}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/spiders/{key}/reload")
async def reload_spider(key: str):
    """
    重新加载爬虫
    :param key: 爬虫标识
    """
    try:
        spider_info = spider_manager.get_spider(key)
        if not spider_info:
            raise HTTPException(status_code=404, detail=f"Spider '{key}' not found")
        
        # 重新加载爬虫（spider_manager.reload_spider 会处理所有类型的爬虫）
        spider_manager.reload_spider(key)
        
        return {"code": 0, "msg": "success", "data": {"key": key}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/spiders/reload-all")
async def reload_all_spiders():
    """
    重新加载所有爬虫（从 spiders.json 和 spiders 目录）
    用于 GitHub 同步后手动触发重新加载
    """
    try:
        count = spider_manager.reload_all_spiders()
        return {"code": 0, "msg": "success", "data": {"count": count}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/webhook/github")
async def github_webhook(request: dict):
    """
    GitHub Webhook 端点
    当 GitHub 仓库有推送时，自动重新加载所有爬虫
    
    在 GitHub 仓库设置中添加 Webhook：
    - Payload URL: https://your-domain.com/webhook/github
    - Content type: application/json
    - Secret: 可选（暂未实现验证）
    - Events: Just the push event
    """
    try:
        event_type = request.get('ref', '')
        print(f"收到 GitHub Webhook: {event_type}")
        
        count = spider_manager.reload_all_spiders()
        
        return {
            "code": 0, 
            "msg": "success", 
            "data": {
                "ref": event_type,
                "spiders_count": count
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/spiders")
async def list_spiders():
    """列出所有爬虫"""
    try:
        spiders = spider_manager.get_all_spiders()
        result = []
        for key, spider_info in spiders.items():
            result.append({
                "key": key,
                "name": spider_info['name'],
                "enabled": spider_info['enabled'],
                "type": spider_info.get('type', spider_info.get('source', 'unknown'))  # 兼容新旧版本
            })
        return {"code": 0, "msg": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/spider/{key}/proxy")
async def spider_proxy(key: str, url: str = Query(..., description="图片URL")):
    """
    图片代理端点，用于获取爬虫返回的图片
    :param key: 爬虫标识
    :param url: 图片URL
    """
    try:
        spider_info = spider_manager.get_spider(key)
        if not spider_info:
            raise HTTPException(status_code=404, detail=f"Spider '{key}' not found")
        
        spider = spider_info['instance']
        
        # 调用爬虫的localProxy方法
        param = {'url': url}
        result = spider.localProxy(param)
        
        # 返回图片数据
        if result and len(result) >= 3:
            status_code, content_type, data = result[0], result[1], result[2]
            return Response(content=data, media_type=content_type, status_code=status_code)
        else:
            raise HTTPException(status_code=500, detail="Invalid proxy response")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class SpiderProxySettings(BaseModel):
    enabled: bool = False
    http_proxy: str = ""
    https_proxy: str = ""

SPIDER_PROXY_FILE = os.path.join(os.path.dirname(__file__), "spider_proxy.json")

def get_spider_proxy_settings() -> SpiderProxySettings:
    """获取爬虫代理设置"""
    try:
        if os.path.exists(SPIDER_PROXY_FILE):
            with open(SPIDER_PROXY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return SpiderProxySettings(**data)
    except:
        pass
    return SpiderProxySettings()

def save_spider_proxy_settings(settings: SpiderProxySettings):
    """保存爬虫代理设置"""
    with open(SPIDER_PROXY_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings.model_dump(), f, indent=2, ensure_ascii=False)

@router.get("/spider-proxy")
async def get_spider_proxy():
    """获取爬虫代理设置"""
    try:
        settings = get_spider_proxy_settings()
        return {"code": 0, "msg": "success", "data": settings.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/spider-proxy")
async def set_spider_proxy(settings: SpiderProxySettings):
    """设置爬虫代理"""
    try:
        save_spider_proxy_settings(settings)
        
        proxy_config = {}
        if settings.enabled:
            if settings.http_proxy:
                proxy_config['http'] = settings.http_proxy
            if settings.https_proxy:
                proxy_config['https'] = settings.https_proxy
        
        spider_manager.set_proxy_config(proxy_config)
        
        return {"code": 0, "msg": "success", "data": settings.model_dump()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
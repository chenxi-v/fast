import importlib.util
import json
import os
import sys
import tempfile
import requests
from urllib.parse import urlparse
from typing import Dict, Any, Optional
from .base.spider import Spider


class SpiderManager:
    """
    爬虫管理器，负责管理多个爬虫实例
    统一管理远程和本地爬虫，所有爬虫文件存储在 spiders 目录下
    """
    
    def __init__(self):
        self.spiders: Dict[str, Dict[str, Any]] = {}
        self._spiders_dir = os.path.join(os.path.dirname(__file__), "spiders")
        self._info_file = os.path.join(self._spiders_dir, "spiders.json")
        self._proxy_config: Dict[str, str] = {}
        
        # 确保 spiders 目录存在
        if not os.path.exists(self._spiders_dir):
            os.makedirs(self._spiders_dir)
        
        # 迁移旧的配置文件（如果存在）
        self._migrate_old_configs()
        
        # 加载现有爬虫
        self._load_spiders()
    
    def _migrate_old_configs(self):
        """迁移旧的配置文件到新的 spiders 目录"""
        old_remote_file = os.path.join(os.path.dirname(__file__), "remote_spiders.json")
        old_local_file = os.path.join(os.path.dirname(__file__), "local_spiders.json")
        
        # 如果新的 info 文件不存在，尝试从旧文件迁移
        if not os.path.exists(self._info_file):
            info_data = {}
            
            # 迁移远程爬虫配置
            if os.path.exists(old_remote_file):
                try:
                    with open(old_remote_file, 'r', encoding='utf-8') as f:
                        remote_spiders = json.load(f)
                    for key, config in remote_spiders.items():
                        if key not in info_data:
                            info_data[key] = {
                                'key': key,
                                'name': config.get('name', key),
                                'enabled': True,
                                'source': 'remote',
                                'script_url': config.get('script_url', ''),
                                'file_path': os.path.join(self._spiders_dir, f"{key}.py")
                            }
                except Exception as e:
                    print(f"迁移远程爬虫配置失败: {str(e)}")
            
            # 迁移本地爬虫配置
            if os.path.exists(old_local_file):
                try:
                    with open(old_local_file, 'r', encoding='utf-8') as f:
                        local_spiders = json.load(f)
                    for key, name in local_spiders.items():
                        if key not in info_data:
                            info_data[key] = {
                                'key': key,
                                'name': name,
                                'enabled': True,
                                'source': 'local',
                                'script_url': '',
                                'file_path': os.path.join(self._spiders_dir, f"{key}.py")
                            }
                except Exception as e:
                    print(f"迁移本地爬虫配置失败: {str(e)}")
            
            # 保存迁移后的配置
            if info_data:
                try:
                    with open(self._info_file, 'w', encoding='utf-8') as f:
                        json.dump(info_data, f, indent=2, ensure_ascii=False)
                    print(f"已迁移 {len(info_data)} 个爬虫配置到 {self._info_file}")
                except Exception as e:
                    print(f"保存迁移配置失败: {str(e)}")
    
    def _load_spiders(self):
        """加载所有爬虫"""
        # 从 info 文件加载爬虫信息
        info_data = {}
        if os.path.exists(self._info_file):
            try:
                with open(self._info_file, 'r', encoding='utf-8') as f:
                    info_data = json.load(f)
            except Exception as e:
                print(f"加载爬虫信息文件失败: {str(e)}")
        
        # 加载 spiders 目录中的 Python 文件
        if os.path.exists(self._spiders_dir):
            for filename in os.listdir(self._spiders_dir):
                if filename.endswith('.py') and filename != '__init__.py':
                    key = filename[:-3]  # 移除 .py 扩展名
                    file_path = os.path.join(self._spiders_dir, filename)
                    
                    # 如果 info 文件中没有该爬虫的信息，创建默认信息
                    if key not in info_data:
                        info_data[key] = {
                            'key': key,
                            'name': key,
                            'enabled': True,
                            'source': 'upload',
                            'script_url': '',
                            'file_path': file_path
                        }
                    
                    # 加载爬虫实例
                    try:
                        self._load_spider_instance(key, file_path, info_data[key])
                        print(f"自动加载爬虫: {key} from {filename}")
                    except Exception as e:
                        print(f"加载爬虫 {filename} 失败: {str(e)}")
        
        self._save_info()
    
    def _load_spider_instance(self, key: str, file_path: str, info: Dict[str, Any]):
        """加载爬虫实例"""
        current_dir = os.path.dirname(os.path.abspath(file_path))
        parent_dir = os.path.dirname(current_dir)
        sys.path.insert(0, parent_dir)
        sys.path.insert(0, current_dir)
        
        try:
            spec = importlib.util.spec_from_file_location(f"spider_{key}", file_path)
            module = importlib.util.module_from_spec(spec)
            sys.modules[f"spider_{key}"] = module
            spec.loader.exec_module(module)
        finally:
            if parent_dir in sys.path:
                sys.path.remove(parent_dir)
            if current_dir in sys.path:
                sys.path.remove(current_dir)
        
        spider_class = getattr(module, 'Spider', None)
        if spider_class is None:
            raise ValueError("脚本中未找到Spider类")
        
        spider_instance = spider_class()
        
        proxy_json = json.dumps(self._proxy_config) if self._proxy_config else ""
        spider_instance.init(proxy_json)
        
        # 获取爬虫名称（优先使用 info 中的名称，其次从爬虫实例获取）
        spider_name = info.get('name', key)
        if spider_name == key:  # 如果名称还是 key，尝试从爬虫实例获取
            if hasattr(spider_instance, 'getName') and callable(getattr(spider_instance, 'getName')):
                name_result = spider_instance.getName()
                if name_result and name_result != 'Spider':
                    spider_name = name_result
        
        self.spiders[key] = {
            'instance': spider_instance,
            'name': spider_name,
            'enabled': info.get('enabled', True),
            'source': info.get('source', 'unknown'),
            'type': info.get('source', 'unknown'),  # 兼容旧版本
            'script_url': info.get('script_url', ''),
            'file_path': file_path
        }
    
    def _save_info(self, info_data: Dict[str, Any] = None):
        """保存爬虫信息到文件"""
        if info_data is None:
            info_data = {}
            for key, spider_info in self.spiders.items():
                info_data[key] = {
                    'key': key,
                    'name': spider_info['name'],
                    'enabled': spider_info['enabled'],
                    'source': spider_info.get('source', 'unknown'),
                    'script_url': spider_info.get('script_url', ''),
                    'file_path': spider_info.get('file_path', os.path.join(self._spiders_dir, f"{key}.py"))
                }
        
        try:
            existing_data = {}
            if os.path.exists(self._info_file):
                with open(self._info_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            
            if existing_data == info_data:
                return
            
            with open(self._info_file, 'w', encoding='utf-8') as f:
                json.dump(info_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存爬虫信息失败: {str(e)}")
    
    def add_spider(self, key: str, source_type: str, source_data: str, custom_name: str = None):
        """
        添加爬虫（统一方法）
        
        参数:
            key: 爬虫标识
            source_type: 来源类型 ('remote' 或 'upload')
            source_data: 来源数据（远程URL或文件内容）
            custom_name: 自定义名称
        """
        file_path = os.path.join(self._spiders_dir, f"{key}.py")
        
        # 根据来源类型处理文件
        if source_type == 'remote':
            # 从远程URL下载文件
            try:
                response = requests.get(source_data)
                response.raise_for_status()
                script_content = response.text
            except Exception as e:
                raise ValueError(f"下载远程脚本失败: {str(e)}")
        elif source_type == 'upload':
            # 文件内容直接使用
            script_content = source_data
        else:
            raise ValueError(f"不支持的来源类型: {source_type}")
        
        # 保存文件到 spiders 目录
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(script_content)
        except Exception as e:
            raise ValueError(f"保存爬虫文件失败: {str(e)}")
        
        # 加载爬虫实例
        info = {
            'key': key,
            'name': custom_name if custom_name else key,
            'enabled': True,
            'source': source_type,
            'script_url': source_data if source_type == 'remote' else '',
            'file_path': file_path
        }
        
        try:
            self._load_spider_instance(key, file_path, info)
        except Exception as e:
            # 如果加载失败，删除已保存的文件
            try:
                os.unlink(file_path)
            except:
                pass
            raise e
        
        # 保存更新后的信息
        self._save_info()
        
        return self.spiders[key]
    
    def add_python_spider(self, key: str, script_url: str, custom_name: str = None):
        """
        添加远程 Python 爬虫（兼容旧接口）
        """
        return self.add_spider(key, 'remote', script_url, custom_name)
    
    def add_local_spider(self, key: str, file_path: str, custom_name: str = None):
        """
        添加本地 Python 爬虫（兼容旧接口）
        """
        # 读取文件内容
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
        except Exception as e:
            raise ValueError(f"读取本地文件失败: {str(e)}")
        
        # 如果文件不在 spiders 目录，复制到 spiders 目录
        target_path = os.path.join(self._spiders_dir, f"{key}.py")
        if os.path.abspath(file_path) != os.path.abspath(target_path):
            try:
                import shutil
                shutil.copy2(file_path, target_path)
            except Exception as e:
                raise ValueError(f"复制文件到 spiders 目录失败: {str(e)}")
        
        return self.add_spider(key, 'upload', file_content, custom_name)
    
    def remove_spider(self, key: str):
        """
        移除爬虫
        """
        if key in self.spiders:
            spider_info = self.spiders[key]
            
            # 调用爬虫的销毁方法（如果存在）
            if hasattr(spider_info['instance'], 'destroy'):
                try:
                    spider_info['instance'].destroy()
                except:
                    pass
            
            # 删除爬虫文件
            file_path = spider_info.get('file_path')
            if file_path and os.path.exists(file_path):
                try:
                    os.unlink(file_path)
                except Exception as e:
                    print(f"删除爬虫文件失败 {file_path}: {str(e)}")
            
            # 从内存中移除
            del self.spiders[key]
            
            # 更新信息文件
            self._save_info()
    
    def get_spider(self, key: str) -> Optional[Dict[str, Any]]:
        return self.spiders.get(key)
    
    def get_all_spiders(self) -> Dict[str, Dict[str, Any]]:
        return self.spiders.copy()
    
    def reload_spider(self, key: str):
        """
        重新加载爬虫
        """
        if key not in self.spiders:
            return
        
        spider_info = self.spiders[key]
        file_path = spider_info.get('file_path')
        
        if not file_path or not os.path.exists(file_path):
            print(f"爬虫文件不存在: {file_path}")
            return
        
        # 移除旧实例
        if hasattr(spider_info['instance'], 'destroy'):
            try:
                spider_info['instance'].destroy()
            except:
                pass
        
        # 重新加载
        try:
            self._load_spider_instance(key, file_path, {
                'key': key,
                'name': spider_info['name'],
                'enabled': spider_info['enabled'],
                'source': spider_info.get('source', 'unknown'),
                'script_url': spider_info.get('script_url', ''),
                'file_path': file_path
            })
            print(f"重新加载爬虫成功: {key}")
        except Exception as e:
            print(f"重新加载爬虫失败 {key}: {str(e)}")
    
    def reload_all_spiders(self):
        """
        重新加载所有爬虫（从 spiders.json 和 spiders 目录）
        用于 GitHub 同步后重新加载配置
        """
        print("开始重新加载所有爬虫...")
        
        # 销毁所有现有爬虫实例
        for key, spider_info in self.spiders.items():
            if hasattr(spider_info['instance'], 'destroy'):
                try:
                    spider_info['instance'].destroy()
                except:
                    pass
        
        # 清空内存中的爬虫
        self.spiders.clear()
        
        # 重新加载
        self._load_spiders()
        
        print(f"重新加载完成，共 {len(self.spiders)} 个爬虫")
        return len(self.spiders)
    
    def enable_spider(self, key: str):
        if key in self.spiders:
            self.spiders[key]['enabled'] = True
            self._save_info()
    
    def disable_spider(self, key: str):
        if key in self.spiders:
            self.spiders[key]['enabled'] = False
            self._save_info()
    
    def update_spider(self, old_key: str, new_key: str = None, new_name: str = None):
        if old_key not in self.spiders:
            raise ValueError(f"爬虫 '{old_key}' 不存在")
        
        spider_info = self.spiders[old_key]
        
        # 更新名称
        if new_name is not None:
            spider_info['name'] = new_name
        
        # 更新 key
        if new_key is not None and new_key != old_key:
            if new_key in self.spiders:
                raise ValueError(f"爬虫标识 '{new_key}' 已存在")
            
            # 重命名文件
            old_file = spider_info.get('file_path')
            if old_file and os.path.exists(old_file):
                new_file = os.path.join(self._spiders_dir, f"{new_key}.py")
                try:
                    os.rename(old_file, new_file)
                    spider_info['file_path'] = new_file
                except Exception as e:
                    raise ValueError(f"重命名爬虫文件失败: {str(e)}")
            
            # 更新内存中的 key
            spider_info['key'] = new_key
            self.spiders[new_key] = spider_info
            del self.spiders[old_key]
            
            # 更新信息文件
            self._save_info()
            return new_key
        
        # 只更新名称，也需要保存
        if new_name is not None:
            self._save_info()
        
        return old_key
    
    def set_proxy_config(self, proxy_config: Dict[str, str]):
        """
        设置代理配置并重新加载所有爬虫
        
        参数:
            proxy_config: 代理配置字典，例如 {'http': 'http://127.0.0.1:7890', 'https': 'http://127.0.0.1:7890'}
        """
        self._proxy_config = proxy_config
        print(f"设置爬虫代理配置: {proxy_config}")
        
        for key, spider_info in self.spiders.items():
            try:
                if hasattr(spider_info['instance'], 'destroy'):
                    try:
                        spider_info['instance'].destroy()
                    except:
                        pass
                
                file_path = spider_info.get('file_path')
                if file_path and os.path.exists(file_path):
                    self._load_spider_instance(key, file_path, {
                        'key': key,
                        'name': spider_info['name'],
                        'enabled': spider_info['enabled'],
                        'source': spider_info.get('source', 'unknown'),
                        'script_url': spider_info.get('script_url', ''),
                        'file_path': file_path
                    })
                    print(f"已为爬虫 {key} 应用代理配置")
            except Exception as e:
                print(f"为爬虫 {key} 应用代理配置失败: {str(e)}")


spider_manager = SpiderManager()

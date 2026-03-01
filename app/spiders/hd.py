# -*- coding: utf-8 -*-
# by @嗷呜
import json
import re
import sys
import threading
import time
from urllib.parse import urlparse
import requests
from pyquery import PyQuery as pq
from app.spider_manager import Spider


class Spider(Spider):

    def init(self, extend=""):
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 14; SM-S928U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36',
            'sec-ch-ua-platform': '"Android"',
            'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="130", "Google Chrome";v="130"',
            'dnt': '1',
            'sec-ch-ua-mobile': '?1',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-mode': 'no-cors',
            'sec-fetch-dest': 'script',
            'accept-language': 'zh-CN,zh;q=0.9',
            'priority': 'u=2',
        }
        try:self.proxies = json.loads(extend)
        except:self.proxies = {}
        self.hsot=self.gethost()
        self.headers.update({'referer': f"{self.hsot}/"})
        self.session.proxies.update(self.proxies)
        self.session.headers.update(self.headers)
        pass

    def getName(self):
        pass

    def isVideoFormat(self, url):
        pass

    def manualVideoCheck(self):
        pass

    def destroy(self):
        pass

    pheader={
        'User-Agent': 'Mozilla/5.0 (Linux; Android 14; SM-S928U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36',
        'sec-ch-ua-platform': '"Android"',
        'sec-ch-ua': '"Not/A)Brand";v="8", "Chromium";v="130", "Google Chrome";v="130"',
        'dnt': '1',
        'sec-ch-ua-mobile': '?1',
        'origin': 'https://jx.8852.top',
        'sec-fetch-site': 'cross-site',
        'sec-fetch-mode': 'cors',
        'sec-fetch-dest': 'empty',
        'accept-language': 'zh-CN,zh;q=0.9',
        'priority': 'u=1, i',
    }

    def homeContent(self, filter):
        data=self.getpq(self.session.get(self.hsot))
        cdata=data('.stui-header__menu li')
        ldata=data('.stui-vodlist.clearfix li')
        result = {}
        classes = []
        for k in cdata.items():
            i=k('a').attr('href')
            if i and 'type' in i:
                classes.append({
                    'type_name': k.text(),
                    'type_id': re.search(r'\d+', i).group(0)
                })
        result['class'] = classes
        
        # 添加筛选器支持 - 按分类ID分组，每个分类有不同的类型筛选器
        filters = {}
        
        # 字母筛选（通用）
        letter_values = [{'n': '全部', 'v': ''}]
        for letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            letter_values.append({'n': letter, 'v': letter})
        
        # 每个分类的类型筛选器
        type_filters = {
            '1': {  # 中文字幕
                'key': 'type',
                'name': '类型',
                'value': [
                    {'n': '全部', 'v': ''},
                    {'n': '中字无码', 'v': '8'},
                    {'n': '中字有码', 'v': '6'},
                ]
            },
            '2': {  # 无字幕
                'key': 'type',
                'name': '类型',
                'value': [
                    {'n': '全部', 'v': ''},
                    {'n': '步兵无码', 'v': '9'},
                    {'n': '骑兵有码', 'v': '7'},
                ]
            },
            '3': {  # 国产
                'key': 'type',
                'name': '类型',
                'value': [
                    {'n': '全部', 'v': ''},
                    {'n': '糖心Vlog', 'v': '13'},
                    {'n': '国产传媒', 'v': '11'},
                    {'n': '国产精品', 'v': '10'},
                ]
            },
            '4': {  # 欧美
                'key': 'type',
                'name': '类型',
                'value': [
                    {'n': '全部', 'v': ''},
                    {'n': '欧美中字', 'v': '12'},
                ]
            },
            '5': {  # 动漫
                'key': 'type',
                'name': '类型',
                'value': [
                    {'n': '全部', 'v': ''},
                    {'n': '中字里番', 'v': '14'},
                    {'n': '3D动漫', 'v': '15'},
                ]
            },
        }
        
        # 为每个分类添加筛选器（不包含 cate，避免与前端分类冲突）
        for cat in classes:
            cat_id = cat['type_id']
            cat_filters = [
                type_filters.get(cat_id, {'key': 'type', 'name': '类型', 'value': [{'n': '全部', 'v': ''}]}),
                {'key': 'letter', 'name': '字母', 'value': letter_values}
            ]
            filters[cat_id] = cat_filters
        
        result['filters'] = filters
        result['list'] = self.getlist(ldata)
        return result

    def homeVideoContent(self):
        return {'list':''}

    def categoryContent(self, tid, pg, filter, extend):
        # 构建筛选URL
        # URL格式: /vodshow/{tid}--------{pg}---.html
        # 带字母筛选: /vodshow/{tid}-----{letter}---{pg}---.html
        
        cate = extend.get('cate', '') if extend else ''
        type_filter = extend.get('type', '') if extend else ''
        letter = extend.get('letter', '') if extend else ''
        
        # 如果选择了类型筛选，使用类型ID作为分类ID
        actual_tid = type_filter if type_filter else tid
        
        # 构建URL
        # 格式: /vodshow/{tid}-----{letter}---{pg}---.html 或 /vodshow/{tid}--------{pg}---.html
        if letter:
            url = f"{self.hsot}/vodshow/{actual_tid}-----{letter}---{pg}---.html"
        else:
            url = f"{self.hsot}/vodshow/{actual_tid}--------{pg}---.html"
        
        print(f"[hd] categoryContent URL: {url}, tid={tid}, cate={cate}, type={type_filter}, letter={letter}")
        
        data=self.getpq(self.session.get(url))
        result = {}
        result['list'] = self.getlist(data('.stui-vodlist.clearfix li'))
        result['page'] = pg
        result['pagecount'] = 9999
        result['limit'] = 90
        result['total'] = 999999
        return result

    def detailContent(self, ids):
        url = ids[0]
        if not url.startswith('http'):
            url = f"{self.hsot}{url}"
        data=self.getpq(self.session.get(url))
        
        vod_name = data('.stui-vodlist__box img').attr('alt') or ''
        if not vod_name:
            title_text = data('title').text()
            if title_text and '《' in title_text and '》' in title_text:
                vod_name = title_text.split('《')[1].split('》')[0]
        
        vod_pic = data('.stui-vodlist__box img').attr('data-original') or ''
        
        vod = {
            'vod_id': ids[0],
            'vod_name': vod_name,
            'vod_pic': vod_pic,
            'vod_remarks': '',
            'vod_content': '',
            'vod_actor': '',
            'vod_director': '',
            'vod_area': '',
            'vod_year': '',
        }
        
        all_p = data('p')
        for p in all_p.items():
            text = p.text().strip()
            if '分类：' in text:
                vod['vod_area'] = text.replace('分类：', '').strip()
            elif '日期：' in text:
                vod['vod_year'] = text.replace('日期：', '').strip()
            elif '时长：' in text:
                vod['vod_remarks'] = text.replace('时长：', '').strip()
        
        meta_desc = data('meta[name="description"]').attr('content')
        if meta_desc:
            if '主演：' in meta_desc:
                actor_match = re.search(r'主演：([^，。]+)', meta_desc)
                if actor_match:
                    vod['vod_actor'] = actor_match.group(1).strip()
            if '详情介绍：' in meta_desc:
                content_match = re.search(r'详情介绍：([^主]+)', meta_desc)
                if content_match:
                    vod['vod_content'] = content_match.group(1).strip()[:200]
        
        play_link = data('.stui-vodlist__box a').attr('href') or data('a[href*="vodplay"]').attr('href')
        if play_link:
            vod['vod_play_from'] = '花都影视'
            vod['vod_play_url'] = f"{vod_name}${play_link}"
        
        return {'list':[vod]}

    def searchContent(self, key, quick, pg="1"):
        data=self.getpq(self.session.get(f"{self.hsot}/vodsearch/{key}----------{pg}---.html"))
        return {'list':self.getlist(data('.stui-vodlist.clearfix li')),'page':pg}

    def playerContent(self, flag, id, vipFlags):
        try:
            url = id
            if not url.startswith('http'):
                url = f"{self.hsot}{id}"
            data=self.getpq(self.session.get(url))
            jstr=data('.stui-player script').eq(0).text()
            jsdata=json.loads(jstr.split("=", maxsplit=1)[-1])
            
            encoded_url = jsdata.get('url', '')
            encrypt = jsdata.get('encrypt', 0)
            
            if encrypt == 1:
                from urllib.parse import unquote
                decoded_url = unquote(encoded_url)
            elif encrypt == 2:
                import base64
                from urllib.parse import unquote
                decoded_url = unquote(base64.b64decode(encoded_url).decode('utf-8'))
            else:
                decoded_url = encoded_url
            
            p, url = 0, decoded_url
        except Exception as e:
            print(f"{str(e)}")
            url = id
            if not url.startswith('http'):
                url = f"{self.hsot}{id}"
            p, url = 1, url
        return {'parse': p, 'url': url, 'header': self.pheader}

    def liveContent(self, url):
        pass

    def localProxy(self, param):
        url = self.d64(param['url'])
        if param.get('type') == 'm3u8':
            return self.m3Proxy(url)
        else:
            return self.tsProxy(url,param['type'])

    def gethost(self):
        params = {
            'v': '1',
        }
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
            'Accept': '*/*',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Referer': 'https://a.hdys.top/',
        }
        try:
            response = self.session.get('https://a.hdys.top/assets/js/config.js', proxies=self.proxies, params=params, headers=headers, timeout=15)
            return self.host_late(response.text.split(';')[:-4])
        except Exception as e:
            print(f"获取host失败: {str(e)}")
            return "https://hd14.huaduziyuan.com"

    def getlist(self,data):
        videos=[]
        for i in data.items():
            vod_id = i('a').attr('href')
            # 跳过完整URL的视频（那些是分享链接，不是有效视频）
            if vod_id and not vod_id.startswith('http'):
                videos.append({
                    'vod_id': vod_id,
                    'vod_name': i('img').attr('alt'),
                    'vod_pic': self.proxy(i('img').attr('data-original')),
                    'vod_year': i('.pic-tag-t').text(),
                    'vod_remarks': i('.pic-tag-b').text(),
                    'style': {"type": "rect", "ratio": 1.33}
                })
        return videos

    def getpq(self, data):
        try:
            return pq(data.text)
        except Exception as e:
            print(f"{str(e)}")
            return pq(data.text.encode('utf-8'))

    def host_late(self, url_list):
        if isinstance(url_list, str):
            urls = [u.strip() for u in url_list.split(',')]
        else:
            urls = url_list

        if len(urls) <= 1:
            return urls[0] if urls else ''

        results = {}
        threads = []

        def test_host(url):
            try:
                url=re.findall(r'"([^"]*)"', url)[0]
                start_time = time.time()
                self.headers.update({'referer': f'{url}/'})
                response = requests.head(url,proxies=self.proxies,headers=self.headers,timeout=1.0, allow_redirects=False)
                delay = (time.time() - start_time) * 1000
                results[url] = delay
            except Exception as e:
                results[url] = float('inf')

        for url in urls:
            t = threading.Thread(target=test_host, args=(url,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        return min(results.items(), key=lambda x: x[1])[0]

    def m3Proxy(self, url):
        ydata = requests.get(url, headers=self.pheader, proxies=self.proxies, allow_redirects=False)
        data = ydata.content.decode('utf-8')
        if ydata.headers.get('Location'):
            url = ydata.headers['Location']
            data = requests.get(url, headers=self.pheader, proxies=self.proxies).content.decode('utf-8')
        lines = data.strip().split('\n')
        last_r = url[:url.rfind('/')]
        parsed_url = urlparse(url)
        durl = parsed_url.scheme + "://" + parsed_url.netloc
        for index, string in enumerate(lines):
            if '#EXT' not in string:
                if 'http' not in string:
                    domain=last_r if string.count('/') < 2 else durl
                    string = domain + ('' if string.startswith('/') else '/') + string
                lines[index] = self.proxy(string, string.split('.')[-1].split('?')[0])
        data = '\n'.join(lines)
        return [200, "application/vnd.apple.mpegur", data]

    def tsProxy(self, url,type):
        h=self.pheader.copy()
        if type=='img':h=self.headers.copy()
        data = requests.get(url, headers=h, proxies=self.proxies, stream=True)
        return [200, data.headers['Content-Type'], data.content]

    def proxy(self, data, type='img'):
        if data and len(self.proxies):return f"{self.getProxyUrl()}&url={self.e64(data)}&type={type}"
        else:return data

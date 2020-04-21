#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Aileon'

import logging
logging.basicConfig(level=logging.INFO)
import os, json, time
from datetime import datetime
from aiohttp import web
from jinja2 import Environment, FileSystemLoader

from url_handle_fn import COOKIE_NAME, cookie2user

def init_jinja2(app, **kw):
    ' 初始化jinja2，设置模板来源 '
    logging.info('init jinja2...')
    options = dict(
        autoescape = kw.get('autoescape', True),
        block_start_string = kw.get('block_start_string', '{%'),
        block_end_string = kw.get('block_end_string', '%}'),
        variable_start_string = kw.get('variable_start_string', '{{'),
        variable_end_string = kw.get('variable_end_string', '}}'),
        auto_reload = kw.get('auto_reload', True)
    )
    path = kw.get('path', None)
    if path is None: # 使用当前文件夹下的templates文件加，所以本目录下要创建一个templates文件夹
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
    logging.info('set jinja2 template path: %s' % path)
    env = Environment(loader=FileSystemLoader(path), **options) # 加载系统环境变量path
    filters = kw.get('filters', None) # 去掉不希望用到的路径
    if filters is not None:
        for name, f in filters.items():
            env.filters[name] = f
    app['__templating__'] = env # 保存到__templating__属性中

"""
一轮过后，如何将函数返回值转化为web.response对象呢？
这里引入aiohttp框架的web.Application()中的middleware参数。
middleware是一种拦截器，一个URL在被某个函数处理前，可以经过一系列的middleware的处理。
一个middleware可以改变URL的输入、输出，甚至可以决定不继续处理而直接返回。
middleware的用处就在于把通用的功能从每个URL处理函数中拿出来，集中放到一个地方。
类似于装饰器
"""
async def logger_factory(app, handler):
    async def logger(request):
        logging.info('Request: %s %s' % (request.method, request.path))
        # await asyncio.sleep(0.3)
        return (await handler(request))
    return logger

async def data_factory(app, handler):
    async def parse_data(request):
        if request.method == 'POST':
            if request.content_type.lower().startswith('application/json'):
                request.__data__ = await request.json()
                logging.info('request json: %s' % str(request.__data__))
            elif request.content_type.lower().startswith('application/x-www-form-urlencoded'):
                request.__data__ = await request.post()
                logging.info('request form: %s' % str(request.__data__))
        return (await handler(request))
    return parse_data

async def response_factory(app, handler):
    '将经handler处理request后的结果转换成一个response对象'
    async def response(request):
        logging.info('Response handler...')
        r = await handler(request) # 使用handler处理request 并且得到处理结果
        if isinstance(r, web.StreamResponse):
            return r
        if isinstance(r, bytes):
            resp = web.Response(body=r)
            resp.content_type = 'application/octet-stream'
            return resp
        if isinstance(r, str):
            if r.startswith('redirect:'):
                return web.HTTPFound(r[9:])
            resp = web.Response(body=r.encode('utf-8'))
            resp.content_type = 'text/html;charset=utf-8'
            return resp
        if isinstance(r, dict):
            template = r.get('__template__')
            if template is None:
                # 没有模板，直接把r的内容以json格式保存在body中 返回
                resp = web.Response(body=json.dumps(r, ensure_ascii=False, default=lambda o: o.__dict__).encode('utf-8'))
                resp.content_type = 'application/json;charset=utf-8'
                return resp
            else:
                # 有模板 则从app内置的模板__templating__中找到template模板，把r字典填入相应模板相应位置，返回
                resp = web.Response(body=app['__templating__'].get_template(template).render(**r).encode('utf-8'))
                resp.content_type = 'text/html;charset=utf-8'
                return resp
        if isinstance(r, int) and r >= 100 and r < 600:
            return web.Response(status=r)
        if isinstance(r, tuple) and len(r) == 2:
            t, m = r
            if isinstance(t, int) and t >= 100 and t < 600:
                return web.Response(status=t, text=str(m))
        # default:
        resp = web.Response(body=str(r).encode('utf-8'))
        resp.content_type = 'text/plain;charset=utf-8'
        return resp
    return response


async def auth_factory(app, handler):
    ' 验证中间件middleware 用于在调用url处理函数之前对request进行cookie解析 提取并解析cookie并绑定在request对象上'
    async def auth(request):
        logging.info('check user: %s %s' % (request.method, request.path))
        request.__user__ = None # 给request绑定一个属性叫__user__, cookie过期或失效或没有的时候为None
        cookie_str = request.cookies.get(COOKIE_NAME) # 从request中获取cookie（字符串）
        if cookie_str:
            user = await cookie2user(cookie_str) # 解析cookie对应的user
            if user:
                logging.info('set current user: %s' % user.email)
                request.__user__ = user # 将user对象绑定在__user__属性
        return (await handler(request))
    return auth

"""
Blog的创建日期显示的是一个浮点数，因为它是由这段模板渲染出来的：
<p class="uk-article-meta">发表于{{ blog.created_at }}</p>
解决方法是通过jinja2的filter（过滤器），把一个浮点数转换成日期字符串。
编写一个datetime的filter，在模板里用法如下：
{{ blog.created_at|datetime }}
其中的|管道符是将前面的结果再经过datetime处理，在web_app中已经将datetime的处理函数指向了datetime_filter
"""

def datetime_filter(t):
    delta = int(time.time() - t)
    if delta < 60:
        return u'1分钟前'
    if delta < 3600:
        return u'%s分钟前' % (delta // 60)
    if delta < 86400:
        return u'%s小时前' % (delta // 3600)
    if delta < 604800:
        return u'%s天前' % (delta // 86400)
    dt = datetime.fromtimestamp(t)
    return u'%s年%s月%s日' % (dt.year, dt.month, dt.day)

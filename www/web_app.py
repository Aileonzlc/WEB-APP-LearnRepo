#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Aileon"

# 廖雪峰教程版
# import logging; logging.basicConfig(level=logging.INFO)

# import asyncio, os, json, time
# from datetime import datetime

# from aiohttp import web

# def index(request):
#     return web.Response(body=b'<h1>Awesome</h1>', content_type='text/html')

# @asyncio.coroutine
# def init(loop):
#     app = web.Application(loop=loop)
#     app.router.add_route('GET', '/', index)
#     srv = yield from loop.create_server(app.make_handler(), '127.0.0.1', 9000)
#     logging.info('server started at http://127.0.0.1:9000...')
#     return srv

# loop = asyncio.get_event_loop()
# loop.run_until_complete(init(loop))
# loop.run_forever()

# 廖雪峰GitHub版
# '''
# async web application.
# '''

# import logging; logging.basicConfig(level=logging.INFO)

# import asyncio, os, json, time
# from datetime import datetime

# from aiohttp import web

# def index(request):
#     return web.Response(body=b'<h1>Awesome</h1>')

# async def init(loop):
#     app = web.Application(loop=loop)
#     app.router.add_route('GET', '/', index)
#     srv = await loop.create_server(app.make_handler(), '127.0.0.1', 9000)
#     logging.info('server started at http://127.0.0.1:9000...')
#     return srv

# loop = asyncio.get_event_loop()
# loop.run_until_complete(init(loop))
# loop.run_forever()

"""
# 新版
# 请求处理器返回的Resonse实例传入参数content_type='text/html'，否则会出现下载页面。
# 创建Application实例的部分参考了官方文档。

import logging
logging.basicConfig(level=logging.INFO)
import asyncio, os, json, time
from datetime import datetime
from aiohttp import web


async def index(request):
    return web.Response(body=b'<h1>Awesome</h1>', content_type='text/html')


def init():
    app = web.Application() 
    app.add_routes([web.get('/', index)])  
    logging.info('Server started at 127.0.0.1...')
    web.run_app(app, host='127.0.0.1', port=8080)  

init()
"""


import logging; logging.basicConfig(level=logging.INFO)
import asyncio
from aiohttp import web

import orm
from web_frame_handler import add_routes, add_static
from web_frame_middleware import logger_factory, response_factory, datetime_filter, init_jinja2

async def init(loop):
    await orm.create_pool(loop=loop, host='127.0.0.1', port=3306, user='Aileon', password='767872313', db='web_app')
    app = web.Application(loop=loop, middlewares=[logger_factory, response_factory])
    init_jinja2(app, filters=dict(datetime=datetime_filter))
    add_routes(app, 'url_handle_fn')
    add_static(app)
    # loop.create_server()则利用asyncio创建TCP服务。
    srv = await loop.create_server(app.make_handler(), '127.0.0.1', 9000)
    logging.info('server started at http://127.0.0.1:9000...')
    return srv

lo = asyncio.get_event_loop()
lo.run_until_complete(init(lo))
lo.run_forever()

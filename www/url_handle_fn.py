# import asyncio
import time

from web_frame_handler import get, post
from models import User, Blog #引入orm框架的User模型

"""
MVC：Model-View-Controller,中文名“模型-视图-控制器”。
其中Python处理的URL函数就是C：Controller，Controller主要负责业务逻辑，
比如检查用户名是否存在，取出用户信息等等；
而View负责显示逻辑，通过一些简单的替换变量，View生成最终用户看到的HTML，那View实质就是HTML模板（如Django等），
而在本次Web开发就是Jinja2模板；
Model是用来传给View的，这样View在替换变量的时候，就可以从Model中取出相应的数据。
"""

'''
串联ORM框架以及Web框架编写MVC，用于测试运行
'''

@get('/p')
async def index1(request):
    users = await User.findAll()
    return {
    '__template__':'text.html',
    'users':users
    } # 返回一个字典，'__template__'指定的模板文件是test.html，其他参数是传递给模板的数据

@get('/')
async def index(request):
    summary = 'Lorem ipsum dolor sit amet, consectetur adipisicing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.'
    blogs = [
        Blog(id='1', name='Test Blog', summary=summary, created_at=time.time()-120),
        Blog(id='2', name='Something New', summary=summary, created_at=time.time()-3600),
        Blog(id='3', name='Learn Swift', summary=summary, created_at=time.time()-7200)
    ]
    return {
        '__template__': 'blogs.html',
        'blogs': blogs
    }

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = 'Aileon'

import asyncio, os, inspect, logging, functools
from urllib import parse
from aiohttp import web

from apis import APIError
'''
这个coroweb.py主要制作了url函数的装饰器，
提供能够预处理request提取函数参数和值的handler，用于统一处理传进url函数的request，
提供url函数注册的函数，用于将特定的访问方式（post，get等，带路径）与url处理函数绑定起来
本模块还未编写url处理函数
'''

"""
补充知识，装饰器的执行过程:
def log(text):
    def decorator(func):
        def wrapper(*args, **kw):
            print('%s %s():' % (text, func.__name__))
            return func(*args, **kw)
        return wrapper
    return decorator

@log('execute')
def now(x):
    print('2015-3-25')
相当于now = log('execute')(now)
我们来剖析上面的语句，首先执行log('execute')，返回的是decorator函数，
再调用返回的函数，参数是now函数，返回值最终是wrapper函数
执行now(5) 相当于log('execute')(now)(5)
相当于执行wrapper(5) 即先执行wrapper内的语句再执行func(5)

@functools.warps(fn)的作用：
以上decorator的定义没有问题，但还差最后一步。因为我们讲了函数也是对象，它有__name__等属性，
但你去看经过decorator装饰之后的函数，它们的__name__已经从原来的'now'变成了'wrapper'
因为返回的那个wrapper()函数名字就是'wrapper'，所以，需要把原始函数的__name__等属性复制到wrapper()函数中，
否则，有些依赖函数签名的代码执行就会出错。
不需要编写wrapper.__name__ = func.__name__这样的代码，Python内置的functools.wraps就是干这个事的
"""

def get(path): # 为了传进path参数，需要在decorator外再嵌套一层函数
    '''
    Define decorator @get('/path')
    '''
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)
        wrapper.__method__ = 'GET' # 给wrapper函数添加__method__参数
        wrapper.__route__ = path # 给wrapper函数添加路径参数
        return wrapper # 返回该函数，此时wrapper不仅有了路径参数，经过functools.wraps之后也把__name__等参数修改成和func的一致
    return decorator

def post(path): # 同上
    '''
    Define decorator @post('/path')
    '''
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            return func(*args, **kw)
        wrapper.__method__ = 'POST'
        wrapper.__route__ = path
        return wrapper
    return decorator

"""
补充知识，以上可以运用偏函数，一并建立URL处理函数的装饰器，用来存储GET、POST和URL路径信息
import functools
def Handler_decorator(path,*,method):
    def decorator(func):
        @functools.wraps(func)#更正函数签名
        def wrapper(*args,**kw):
            return func(*args,**kw)
        wrapper.__route__ = path #存储路径信息,注意这里属性名叫route
        wrapper.__method__ = method #存储方法信息
        return wrapper
    return decorator

get = functools.partial(Handler_decorator,method = 'GET')
post = functools.partial(Handler_decorator,method = 'POST')
"""

'''
补充知识
inspect.signature（fn)： 返回一个inspect.Signature类型的对象，值为fn这个函数的所有参数
inspect.Signature对象的paramerters属性： 一个mappingproxy（映射）类型的对象，值为一个有序字典（Orderdict)；
    这个字典里的key即为参数名，str类型
    这个字典里的value是一个inspect.Parameter类型的对象
inspect.Parameter对象的kind属性: 一个_ParameterKind枚举类型的对象，值为这个参数的类型（位置参数，关键词参数，etc）
inspect.Parameter对象的default属性： 如果这个参数有默认值，即返回这个默认值，如果没有，返回一个inspect._empty类。
'''
def get_required_kw_args(fn):
    ' 收集没有默认值的关键字参数 '
    args = []
    # signature(obj,*,f=true),其中*接收了所有tuple形式的位置参数，所以f仅限关键字参数传入
    # def f(a,*,b,c)的话，b，c 均为仅限关键字参数。
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY and param.default == inspect.Parameter.empty:
            args.append(name)
    return tuple(args)

def get_named_kw_args(fn):
    ' 获取关键字参数 '
    args = []
    params = inspect.signature(fn).parameters
    for name, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            args.append(name)
    return tuple(args)

def has_named_kw_args(fn):
    ' 判断有没有关键字参数 '
    params = inspect.signature(fn).parameters
    # for name, param in params.items():
    for _, param in params.items():
        if param.kind == inspect.Parameter.KEYWORD_ONLY:
            return True

def has_var_kw_arg(fn):
    ' 判断有没有通过**kw关键字传参 **kw使用时是dict'
    ' *args为VAR_POSIONAL ,*args使用时是tuple'
    params = inspect.signature(fn).parameters
    # for name, param in params.items():
    for _, param in params.items():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            return True

def has_request_arg(fn):
    ' 判断是否含有名叫request参数，且该参数是否为最后一个命名的位置参数 '
    sig = inspect.signature(fn)
    params = sig.parameters
    found = False
    for name, param in params.items():
        # 循环判断request后的参数，可以为*args，可以为**kw，也可以为关键字参数，除此之外都不行
        if name == 'request': # 如果参数名叫request
            found = True
            continue
        if found and (param.kind != inspect.Parameter.VAR_POSITIONAL and param.kind != inspect.Parameter.KEYWORD_ONLY and param.kind != inspect.Parameter.VAR_KEYWORD):
            raise ValueError('request parameter must be the last named parameter in function: %s%s' % (fn.__name__, str(sig)))
    return found

class RequestHandler(object):

    def __init__(self, app, fn):
        self._app = app
        self._func = fn
        self._has_request_arg = has_request_arg(fn)
        self._has_var_kw_arg = has_var_kw_arg(fn)
        self._has_named_kw_args = has_named_kw_args(fn)
        self._named_kw_args = get_named_kw_args(fn)
        self._required_kw_args = get_required_kw_args(fn)

    async def __call__(self, request): # 处理request中的各项参数的值，根据url函数的需求，将参数及值整理发送给url函数fn处理
        kw = None
        if self._has_var_kw_arg or self._has_named_kw_args or self._required_kw_args:
            if request.method == 'POST': #判断客户端发来的方法是否为POST
                if not request.content_type: #查询有没提交数据的格式（EncType）
                    return web.HTTPBadRequest(text='Missing Content-Type.')
                ct = request.content_type.lower() #小写
                if ct.startswith('application/json'): # 如果request的内容格式属性以application/json开头
                    params = await request.json() # 将request的body部分解码为json
                    if not isinstance(params, dict): # 判断解码后的对象是不是一个字典
                        return web.HTTPBadRequest(text='JSON body must be object.')
                    kw = params
                elif ct.startswith('application/x-www-form-urlencoded') or ct.startswith('multipart/form-data'):
                    # reads POST parameters from request body.
                    # If method is not POST, PUT, PATCH, TRACE or DELETE 
                    # or content_type is not empty or application/x-www-form-urlencoded 
                    # or multipart/form-data returns empty multidict.
                    params = await request.post()
                    kw = dict(**params)
                else:
                    return web.HTTPBadRequest(text='Unsupported Content-Type: %s' % request.content_type)
            if request.method == 'GET':
                qs = request.query_string # The query string in the URL
                if qs:
                    kw = dict()
                    # Parse a query string given as a string argument.
                    # Data are returned as a dictionary. 
                    # The dictionary keys are the unique query variable names 
                    # and the values are lists of values for each name.
                    for k, v in parse.parse_qs(qs, True).items():
                        kw[k] = v[0]
        if kw is None:
            kw = dict(**request.match_info)
        else:
            # 当函数参数没有未命名关键字参数**kw时，移去request中除已命名关键字参数外的所有的关键字参数
            if not self._has_var_kw_arg and self._named_kw_args:
                # 移除未命名的关键字参数，保留已命名的关键字参数的值
                # remove all unamed kw:
                copy = dict()
                for name in self._named_kw_args:
                    if name in kw:
                        copy[name] = kw[name]
                kw = copy
            # check named arg:
            for k, v in request.match_info.items():
                if k in kw:
                    logging.warning('Duplicate arg name in named arg and kw args: %s' % k)
                kw[k] = v
        if self._has_request_arg:
            kw['request'] = request
        # check required kw:
        if self._required_kw_args:
            for name in self._required_kw_args: # 如果处理函数需要传入命名的关键字参数（没有默认值），且kw中没有提供
                # if not name in kw:
                if name not in kw:
                    return web.HTTPBadRequest(text='Missing argument: %s' % name)
        logging.info('call with args: %s' % str(kw))
        try:
            r = await self._func(**kw)
            return r
        except APIError as e:
            return dict(error=e.error, data=e.data, message=e.message)

def add_static(app):
    ' 添加静态文件夹的路径 '
    #输出当前文件夹中'static'的路径,记得当前目录下一定要有个和下面填加路径一致的文件名（如static文件夹）
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    app.router.add_static('/static/', path)
    logging.info('add static %s => %s' % ('/static/', path))

"""
补充知识
# As discussed above, handlers can be first-class coroutines:

async def hello(request):
    return web.Response(text="Hello, world")

app.router.add_get('/', hello)

# But sometimes it’s convenient to group logically similar handlers into a Python class.
# Since aiohttp.web does not dictate any implementation details, 
# application developers can organize handlers in classes if they so wish:

class Handler:
    def __init__(self):
        pass
    async def handle_intro(self, request):
        return web.Response(text="Hello, world")
    async def handle_greeting(self, request):
        name = request.match_info.get('name', "Anonymous")
        txt = "Hello, {}".format(name)
        return web.Response(text=txt)

handler = Handler()
app.add_routes([web.get('/intro', handler.handle_intro),
                web.get('/greet/{name}', handler.handle_greeting)]
"""

def add_route(app, fn):
    ' 为一个网页路径添加相应的url处理方法fn（注册） 添加前用requesthandler处理函数参数（验证及传参） '
    method = getattr(fn, '__method__', None)
    path = getattr(fn, '__route__', None)
    if path is None or method is None:
        raise ValueError('@get or @post not defined in %s.' % str(fn))
    # 当这个函数不是协程且不是生成器（生成器有yield，调用使用next）
    if not asyncio.iscoroutinefunction(fn) and not inspect.isgeneratorfunction(fn):
        fn = asyncio.coroutine(fn)# 创建一个协程
    logging.info('add route %s %s => %s(%s)' % (method, path, fn.__name__, ', '.join(inspect.signature(fn).parameters.keys())))
    app.router.add_route(method, path, RequestHandler(app, fn))

# 直接导入文件，批量注册URL处理函数
def add_routes(app, module_name):
    n = module_name.rfind('.')
    if n == (-1):
        mod = __import__(module_name, globals(), locals())
    else:
        name = module_name[n+1:]
        mod = getattr(__import__(module_name[:n], globals(), locals(), [name]), name)

    for attr in dir(mod): # 对这个模块里的所有属性进行判断
        if attr.startswith('_'): # 如果是私有属性，跳过
            continue
        fn = getattr(mod, attr) # 获取这个属性的值（这个值是一个引用）
        if callable(fn): # 如果这个对象可以调用，说明带__call__
            method = getattr(fn, '__method__', None) # 判断他是不是经过修饰的url函数
            path = getattr(fn, '__route__', None) # 判断他是不是经过修饰的url函数
            if method and path: # 判断他是不是经过修饰的url函数
                add_route(app, fn)

import time,re,hashlib
from aiohttp import web
import json
import logging
logging.basicConfig(level=logging.INFO)

from web_frame_handler import get, post
from models import User, Blog, next_id #引入orm框架的User模型
from config import config
from apis import APIError, APIValueError

# ========================第一部分url处理函数：面向前端==========================
"""
MVC：Model-View-Controller,中文名“模型-视图-控制器”。
其中Python处理的URL函数就是C：Controller，Controller主要负责业务逻辑，
比如检查用户名是否存在，取出用户信息等等；
而View负责显示逻辑，通过一些简单的替换变量，View生成最终用户看到的HTML，那View实质就是HTML模板（如Django等），
而在本次Web开发就是Jinja2模板；
MVC中的Model在哪？Model是用来传给View的，这样View在替换变量的时候，就可以从Model中取出相应的数据。在本项目中实际上model就是一个dict
MVC注重网页的呈现，用户与web的交互
C处理得到M，M传给V填入，最后得到response
"""
#显示注册页面
@get('/register')#这个作用是用来显示登录页面
def register():
    return {
        '__template__': 'register.html'
    }

# 显示注册页面
@get('/signin')
def signin():
    return {
        '__template__': 'signin.html'
    }

@get('/test')
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
        'blogs': blogs,
        '__user__': request.__user__
    }

# =======================第二部分url处理函数：web api 面向后端====================
'''
mvc主要用于建站，web api主要用于构建http服务，API更抽象，更不注重View的生成。注重后端数据库与网页输入数据的交互
'''
'''
服务端制作cookie发给客户端过程：
1、首先会由网页中的javascript取得对应的值，并按照如下组合方式，进行摘要算法计算出一个字符串(A)：
"email" + ":" + "passwd"
2、然后字符串(A)被以密码的形式传递到API内，在API内，字符串(A)再一次按照如下组合方式，进行摘要算法计算出一个字符串(B)，并保存到服务器数据库上。
"用户id" + ":" + 字串符(A)
3、到了最后制作cookie发送给浏览器时，又使用字符串(B)按照如下组合方式，进行摘要算法计算出一个字符串(C),密钥是服务端持有的用来加密，客户端无法获得：
"用户id" + 字串符(B) + "到期时间" + "密匙"
4、最后再按照如下**组合方式**，生成一个字串符(D)发送给浏览器
"用户id" + "到期时间" + 字符串(C)
服务端验证客户端的cookie过程：
浏览器收到cookie的信息有：用户id、过期时间、SHA1值(字串符(C))
在cookie未到过期的期间，当服务器验证cookie是否伪造时，其实只需根据用户信息在数据库查找相应的用户口令(即字符串(B))，
再使用其进行摘要算法与cookie中的字符串(C)比较是否等价，就可以知道是否伪造了。
'''
COOKIE_NAME = config['session']['cookieName'] # 浏览器的cookies是以字典储存的，包含了很多网站的cookie，这个cookie代表本服务器cookie对应的名字叫webcookie
_COOKIE_KEY = config['session']['secret'] # 导入默认设置里的密钥

#制作cookie的数值，即set_cookie的value
def user2cookie(user, max_age): # max_age：cookie最长使用时间
    '''
    Generate cookie str by user.用user的记录产生cookie
    '''
    # build cookie string by: id-expires-sha1（id-到期时间-摘要算法）
    expires = str(time.time()+max_age) # 到期时间
    s = '%s-%s-%s-%s'%(user.id, user.passwd, expires, _COOKIE_KEY)#s的组成：id, passwd, expires, _COOKIE_KEY
    L = [user.id, expires, hashlib.sha1(s.encode('utf-8')).hexdigest()]#再把s进行摘要算法
    return '-'.join(L)


# 用户注册：对用户密码进行加密，这里使用SHA1单向算法，并储存到数据库
_RE_EMAIL = re.compile(r'^[a-z0-9\.\-\_]+\@[a-z0-9\-\_]+(\.[a-z0-9\-\_]+){1,4}$') # email匹配规则
_RE_SHA1 = re.compile(r'^[0-9a-f]{40}$') # 输入密码匹配规则

@post('/api/users')
async def api_register_user(*, email, name, passwd):
    # 如果名字是空格或没有返错 其实name为空时已经包含在name.strip()中了，前面的判断没有必要
    if not name or not name.strip():
        raise APIValueError('name')
    # 如果email是空或不匹配规则
    if not email or not _RE_EMAIL.match(email):
        raise APIValueError('email')
    # 如果passwd 是空或者不匹配规则
    if not passwd or not _RE_SHA1.match(passwd):
        raise APIValueError('passwd')
    users = await User.findAll('email=?', [email])
    if len(users) > 0:
        raise APIError('register:failed', 'email', 'Email is already in use.')

    # 接下来把输入的账号注册到数据库上,
    uid = next_id() # 生成一个id
    sha1_passwd = '%s:%s' % (uid, passwd) # 与passwd组合，为了使密码更安全
    # hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest()先把密码用utf-8编码（与数据库里的字符集一致）
    # 然后sha1单向计算生成加密密码 生成40位字符
    user = User(id=uid, name=name.strip(), email=email, passwd=hashlib.sha1(sha1_passwd.encode('utf-8')).hexdigest(), image='http://www.gravatar.com/avatar/%s?d=mm&s=120' % hashlib.md5(email.encode('utf-8')).hexdigest())
    await user.save()

    # 制作cookie返回浏览器客户端
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True) # 86400秒相当于24小时
    user.passwd = '******' # 此处的passwd是由__getter__方法返回的，相当于user['passwd']。隐藏密码，这样不会再body中显示出来
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r

# 用户登录：验证用户登陆输入时的密码经过计算后的密文与数据库中保存的一致
@post('/api/authenticate')
async def authenticate(*, email, passwd): # 这里的passwd是明文
    ' 用户登陆，验证用户输入的密码经过单向函数计算后的密码是否和数据库中的一致，一致则成功登陆，返回一个cookie '
    if not email:
        raise APIValueError('email', 'Invalid email.')
    if not passwd:
        raise APIValueError('passwd', 'Invalid password.')
    users = await User.findAll('email=?', [email]) # 如果邮箱唯一，则这里用find也可以，不唯一的话还需要验证姓名那么了，就需要修改url函数
    if len(users) == 0:
        raise APIValueError('email', 'Email not exist.')
    user = users[0]

    # 验证密码单向计算后的值是否一致
    sha1 = hashlib.sha1()
    sha1.update(user.id.encode('utf-8'))
    sha1.update(b':')
    sha1.update(passwd.encode('utf-8'))
    if user.passwd != sha1.hexdigest(): # 判断 数据库中保存的密码！=用户登陆数据的密码的单向计算结果
        raise APIValueError('passwd', 'Invalid password.')

    # 制作cookie返回浏览器客户端
    r = web.Response()
    r.set_cookie(COOKIE_NAME, user2cookie(user, 86400), max_age=86400, httponly=True)
    user.passwd = '******'
    r.content_type = 'application/json'
    r.body = json.dumps(user, ensure_ascii=False).encode('utf-8')
    return r


async def cookie2user(cookie_str):
    '''
    解析cookie 得到相应的用户，返回用户对象，否则返回none
    '''
    if not cookie_str: # 此处其实已经在middleware中判断过一次
        return None
    try:
        L = cookie_str.split('-') # 将cookie拆分成三部分 用户id  到期时间  加密字符串(C)
        if len(L) != 3:
            return None
        uid, expires, sha1 = L
        if float(expires) < time.time(): # 过期则返回,廖老师用的是int，但是字符串用int的时候，只能全是数字，不能含小数点
            return None
        user = await User.find(uid) # 找到该用户
        if user is None:
            return None
        s = '%s-%s-%s-%s' % (uid, user.passwd, expires, _COOKIE_KEY)
        if sha1 != hashlib.sha1(s.encode('utf-8')).hexdigest():# shq1是客户端request里的密文，后边的是服务器里计算该用户后的密文
            logging.info('invalid sha1')
            return None
        user.passwd = '******' # 在获得该用户验证通过之后，都要记得把passwd密文段隐藏掉，否则客户端有概率通过passwd制作cookie
        return user
    except Exception as e:
        logging.exception(e)
        return None
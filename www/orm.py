#!/usr/bin/env python3
# -*- coding: utf-8 -*-

__author__ = "Aileon"

import asyncio, logging, aiomysql
"""
ORM框架提供了python操作mysql数据库的简便方式
把表映射为类对象（即表类，表类内包含字段类的实例），把记录映射为实例对象
表的定义就是类对象的创建，类对象的创建使用了metaclass元类来创建，初始化了基本字段，和基本sql语句（把字段动态添加进去）
类对象的创建过程中包括了字段实例的创建，字段实例的创建使用普通类来创建，初始化字段名，字段类型和字段约束
完成表的定义（包括使用元类创建表类，表类内创建字段实例）
所有表内的增删改查，都通过表的实例来操作
表类的实例是个字典，字典内包含表的所有字段key，及相应的字段值value
记录的插入（增）动作：先创建实例，执行保存时查找字段默认值并添加到数据库中（通过execute（））
记录的更新、删除（删改）动作: 在当前实例下（当前实例记录了这个实例的所有属性值），用主键执行删改
记录的查询（查）动作：根据条件执行execute（），用获得的记录对每个记录创建实例，返回实例对象
"""
# 记录过程信息
def log(sql, args=()):
    logging.info('SQL: %s' % sql)

# ======================数据库连接部分====================
# 连接池
async def create_pool(loop, **kw):
    logging.info('create database connection pool...')
    global __pool # 全局变量
    __pool = await aiomysql.create_pool(
        host=kw.get('host', 'localhost'), # 传入IP地址 默认localhost本机
        port=kw.get('port', 3306), # 传入端口，默认3306
        user=kw['user'], # 传入用户名
        password=kw['password'], # 传入密码
        db=kw['db'], # 当前连接的数据库名
        charset=kw.get('charset', 'utf8'), # 设置默认字符集
        autocommit=kw.get('autocommit', True), # 设置自动提交
        maxsize=kw.get('maxsize', 10), # 连接池最大连接数
        minsize=kw.get('minsize', 1), # 连接词最小连接数
        loop=loop # 传入事件循环
    )
# DQL查询语句
async def select(sql, args, size=None):
    log(sql, args) # 记录过程信息
    global __pool
    async with __pool.get() as conn: # with (yield from _pool) as conn 在python3.5以前
        async with conn.cursor(aiomysql.DictCursor) as cur: # 用DictCursor，cur返回的结果集为一个字典
            await cur.execute(sql.replace('?', '%s'), args or ())# 短路逻辑args or () 表示当args为None时，使用()
            # 取指定个数记录，默认取all
            if size:
                rs = await cur.fetchmany(size)
            else:
                rs = await cur.fetchall()
        logging.info('rows returned: %s' % len(rs)) # 记录过程信息
        return rs
# DML操纵语句，delete insert update
async def execute(sql, args, autocommit=True):
    log(sql) # 记录过程信息
    async with __pool.get() as conn:
        if not autocommit:
            await conn.begin() # 如果不是自动提交，需要开启事务
        try:
            async with conn.cursor(aiomysql.DictCursor) as cur: # with语句可以自动close（上下文管理）
                await cur.execute(sql.replace('?', '%s'), args)
                affected = cur.rowcount
            if not autocommit: # 如果不是自动提交，开启事务后需要提交才生效
                await conn.commit()
        except BaseException as e:
            print(e)
            if not autocommit: # 如果不是自动提交且发送错误，需要回滚
                await conn.rollback()
            raise # raise 一个错误让上一层的函数处理
        # finally:
        #     await cur.close()
        return affected # 如果发生错误，则这句代码不会执行，上一句已经raise

def create_args_string(num):
    L = []
    for _ in range(num):
        L.append('?')
    return ', '.join(L)

# ===================字段（列）的映射部分================= 
class Field(object):

    def __init__(self, name, column_type, primary_key, default):
        self.name = name
        self.column_type = column_type
        self.primary_key = primary_key
        self.default = default

    def __str__(self):
        # self.__class__.__name__ 表示这个实例的类对象的__name__属性，也就是类名，如StringField，BooleanField那些
        return '<%s, %s:%s>' % (self.__class__.__name__, self.column_type, self.name)

class StringField(Field):

    def __init__(self, name=None, primary_key=False, default=None, ddl='varchar(100)'):
        super().__init__(name, ddl, primary_key, default)

class BooleanField(Field):

    def __init__(self, name=None, default=False):
        super().__init__(name, 'boolean', False, default)

class IntegerField(Field):

    def __init__(self, name=None, primary_key=False, default=0):
        super().__init__(name, 'bigint', primary_key, default)

class FloatField(Field):

    def __init__(self, name=None, primary_key=False, default=0.0):
        super().__init__(name, 'real', primary_key, default)

class TextField(Field):

    def __init__(self, name=None, default=None):
        super().__init__(name, 'text', False, default)

# ==================数据表的映射部分================== 
class ModelMetaclass(type): # 利用type创建元类，元类用于创建其他普通类，会在普通类创建时调用
    # 元类创建普通类的特性可以用来动态创建普通类的初始属性和方法
    def __new__(cls, name, bases, attrs): # cls表示类，以下内容针对类创建
        if name=='Model': # 排除Model类本身创建时
            return type.__new__(cls, name, bases, attrs)
        # attrs是储存类的方法的字典，这个字段的键就是方法名，但使用字符串表示，value使用类引用地址或方法引用地址
        tableName = attrs.get('__table__', None) or name # 短路逻辑，当创建的类（映射表）没有__table__属性时，会返回name（类名）
        logging.info('found model: %s (table: %s)' % (name, tableName)) # 记录类名-》表名的映射
        mappings = dict() # 用于在储存在该类中的映射关系，表字段（str）-》Field对象
        fields = [] # 储存除主键外的其余字段，以字符串形式储存在列表（未格式化）
        primaryKey = None # 储存主键 字符串形式
        for k, v in attrs.items(): # 储存主键，其他字段，及所有映射关系
            if isinstance(v, Field):
                logging.info('  found mapping: %s ==> %s' % (k, v))
                mappings[k] = v
                if v.primary_key:
                    # 找到主键:
                    if primaryKey:
                        raise Exception('Duplicate primary key for field: %s' % k)
                    primaryKey = k
                else:
                    fields.append(k)
        if not primaryKey: # 确保主键存在
            raise Exception('Primary key not found.')
        for k in mappings.keys(): # 将这些类属性从这个创建的类中删除
            attrs.pop(k)
        escaped_fields = list(map(lambda f: '`%s`' % f, fields)) # 格式化后的字段，为每个字段加上``以确保字段为字符串区别于一些关键字
        attrs['__mappings__'] = mappings # 保存字段和字段类的映射关系
        attrs['__table__'] = tableName # 为这个类增加一个表名
        attrs['__primary_key__'] = primaryKey # 主键属性名
        attrs['__fields__'] = fields # 除主键外的属性名
        # select `字段1`，`字段2` from `表`
        attrs['__select__'] = 'select `%s`, %s from `%s`' % (primaryKey, ', '.join(escaped_fields), tableName)
        # insert into 表 （`字段1`，`字段2`） values （？，？）
        attrs['__insert__'] = 'insert into `%s` (%s, `%s`) values (%s)' % (tableName, ', '.join(escaped_fields), primaryKey, create_args_string(len(escaped_fields) + 1))
        # mappings.get(f).name or f，在创建字段实例的时候不一定会传入字段名储存，这时候是默认使用键值的
        # update `表` set `字段1`=？，`字段2`=？ where `字段3`=？，更新时通过实例来更新，可以获取实例的主键，所以直接用主键来更新
        attrs['__update__'] = 'update `%s` set %s where `%s`=?' % (tableName, ', '.join(map(lambda f: '`%s`=?' % (mappings.get(f).name or f), fields)), primaryKey)
        # delete from `表` where `字段`=？，删除时通过实例删，可以获取实例的主键
        attrs['__delete__'] = 'delete from `%s` where `%s`=?' % (tableName, primaryKey)
        return type.__new__(cls, name, bases, attrs)

class Model(dict, metaclass=ModelMetaclass): # 继承Model的子类，会隐式地继承Model的元类

    def __init__(self, **kw): # self表示实例，以下内容针对实例创建
        # 将实例传进来的关键字参数储存为字典
        super(Model, self).__init__(**kw)

    def __getattr__(self, key):
        try:
            return self[key] # 继承字典
        except KeyError: # 当没有这个key时会raise attributeError 
            raise AttributeError(r"'Model' object has no attribute '%s'" % key)

    def __setattr__(self, key, value):
        self[key] = value

    def getValue(self, key): # 此方法为了方便update调用
        return getattr(self, key, None)

    def getValueOrDefault(self, key):
        value = getattr(self, key, None) # 当raise attributeError时会使用默认值none
        if value is None: # 如果这个实例没有这个字段的值
            field = self.__mappings__[key] # 从类对象（表）中的映射字典中获取字段对象（列）,如果该类没有该字段，会raise keyerror
            if field.default is not None:  # 如果该字段有默认值或者生成默认值的调用方法，默认值为None则会直接放回none
                value = field.default() if callable(field.default) else field.default
                logging.debug('using default value for %s: %s' % (key, str(value)))
                setattr(self, key, value) # 将该类的值的字段设置为默认值
        return value

    @classmethod
    async def findAll(cls, where=None, args=None, **kw): # 类方法（表方法）
        ' find objects by where clause. '
        # 实例化的时候输入的字段不用加反引号`但调用方法时需要加
        sql = [cls.__select__] # 用该表的字段初始化该表的select语句
        if where:
            sql.append('where')
            sql.append(where) # 此处的where输入的是条件（字符串形式），如"`id`>2"
        if args is None:
            args = []
        orderBy = kw.get('orderBy', None)
        if orderBy:
            sql.append('order by')
            sql.append(orderBy) # 此处orderBY输入的是字段，如 "`id`"
        limit = kw.get('limit', None)
        # if limit is not None:
        if limit:
            sql.append('limit')
            if isinstance(limit, int):
                sql.append('?')
                args.append(limit)
            elif isinstance(limit, tuple) and len(limit) == 2:
                sql.append('?, ?')
                args.extend(limit)
            else:
                raise ValueError('Invalid limit value: %s' % str(limit))
        # 到这一步为止 sql这个list里除了最后的限制记录条数使用？填充，其余已经填好对应的值
        rs = await select(' '.join(sql), args)# list里边储存每个记录的字典
        return [cls(**r) for r in rs] # 创建这些实例，以列表返回

    @classmethod
    async def findNumber(cls, selectField, where=None, args=None):
        ' find number by select and where. '
        # 此处不懂_num_
        sql = ['select %s _num_ from `%s`' % (selectField, cls.__table__)]
        if where:
            sql.append('where')
            sql.append(where) # 此处的where输入的是条件（字符串形式），如"`id`>2"
        rs = await select(' '.join(sql), args, 1)
        if len(rs) == 0:
            return None
        return rs[0]['_num_']

    @classmethod
    async def find(cls, pk):
        ' find object by primary key. '
        # rs = await select('%s where `%s`=?' % (cls.__select__, cls.__primary_key__), [pk])
        # 按关键字查询，结果只会返回一条记录 不写size参数1也可以，只不过查询要遍历全表，慢
        rs = await select('%s where `%s`=?' % (cls.__select__, cls.__primary_key__), [pk], 1)
        if len(rs) == 0:
            return None
        return cls(**rs[0]) # 返回一个实例对象

    async def save(self):
        args = list(map(self.getValueOrDefault, self.__fields__)) # 获取实例对象的字段当前值或默认值
        args.append(self.getValueOrDefault(self.__primary_key__)) # 获取实例对象的主键当前值或默认值
        rows = await execute(self.__insert__, args) # 执行插入
        if rows != 1:
            logging.warn('failed to insert record: affected rows: %s' % rows)

    async def update(self):
        args = list(map(self.getValue, self.__fields__)) # 获取实例对象字段的当前值，不存在会raise错误，因为在所有记录在save时就已经要设置好默认值
        args.append(self.getValue(self.__primary_key__)) 
        rows = await execute(self.__update__, args)
        if rows != 1:
            logging.warn('failed to update by primary key: affected rows: %s' % rows)

    async def remove(self):
        args = [self.getValue(self.__primary_key__)] # 获取当前实例的主键值
        rows = await execute(self.__delete__, args) # 执行删除
        if rows != 1:
            logging.warn('failed to remove by primary key: affected rows: %s' % rows)
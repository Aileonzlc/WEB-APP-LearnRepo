#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
这个模块创建了三个表（以类对象的方式）
'''

__author__ = "Aileon"

import time, uuid

from orm import Model, StringField, BooleanField, FloatField, TextField

def next_id():
    # 用于创建id %0nd 用得比较多，表示输出的整型宽度至少为n位，不足n位用0填充
    # uuid.uuid4().hex使用随机数生成唯一id 36位字符
    # 为避免随机数相同，再加上了用时间生成的整数（秒），在1秒内产生的相同的随机数相同才会使整个id相同，但概率非常小了
    return '%015d%s000' % (int(time.time() * 1000), uuid.uuid4().hex)

class User(Model):
    __table__ = 'users'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    email = StringField(ddl='varchar(50)')
    passwd = StringField(ddl='varchar(50)')
    admin = BooleanField()
    name = StringField(ddl='varchar(50)')
    image = StringField(ddl='varchar(500)')
    created_at = FloatField(default=time.time)

class Blog(Model):
    __table__ = 'blogs'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    user_id = StringField(ddl='varchar(50)')
    user_name = StringField(ddl='varchar(50)')
    user_image = StringField(ddl='varchar(500)')
    name = StringField(ddl='varchar(50)')
    summary = StringField(ddl='varchar(200)')
    content = TextField()
    created_at = FloatField(default=time.time)

class Comment(Model):
    __table__ = 'comments'

    id = StringField(primary_key=True, default=next_id, ddl='varchar(50)')
    blog_id = StringField(ddl='varchar(50)')
    user_id = StringField(ddl='varchar(50)')
    user_name = StringField(ddl='varchar(50)')
    user_image = StringField(ddl='varchar(500)')
    content = TextField()
    created_at = FloatField(default=time.time)

#定义选取数量（每一页都会选取相应选取数量的数据库中日志出来显示）
class Page(object):
    def __init__(self, item_count, page_index=1, page_size=10):#参数依次是：数据库博客总数，初始页，一页显示博客数
        self.item_count = item_count
        self.page_size = page_size
        self.page_count = item_count // page_size + (1 if item_count % page_size > 0 else 0)#一共所需页的总数
        if (item_count == 0) or (page_index > self.page_count):#假如数据库没有博客或全部博客总页数不足一页
            self.offset = 0
            self.limit = 0
            self.page_index = 1
        else:
            self.page_index = page_index #初始页
            self.offset = self.page_size * (page_index - 1) #当前页数，应从数据库的那个序列博客开始显示
            self.limit = self.page_size #当前页数，应从数据库的那个序列博客结束像素
        self.has_next = self.page_index < self.page_count #有否下一页
        self.has_previous = self.page_index > 1 #有否上一页

    def __str__(self):
        return 'item_count: %s, page_count: %s, page_index: %s, page_size: %s, offset: %s, limit: %s' % (self.item_count, self.page_count, self.page_index, self.page_size, self.offset, self.limit)

    __repr__ = __str__
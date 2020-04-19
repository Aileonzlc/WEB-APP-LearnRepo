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
    # uuid.uuid4().hex使用随机数生成唯一id
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
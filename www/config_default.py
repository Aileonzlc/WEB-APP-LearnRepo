#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
Default configurations.
'''

__author__ = 'Aileon'

configs = {
    'debug': True,
    'db': {
        'host': '127.0.0.1',
        'port': 3306,
        'user': 'Aileon',
        'password': '767872313',
        'db': 'web_app'
    },
    'session': {
        'secret': 'web_app', # 本服务器使用的cookie密钥
        'cookieName': 'web_cookie' # cookie的名字，用来在字典里找cookie
    }
}
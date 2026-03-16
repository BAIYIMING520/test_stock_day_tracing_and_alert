# -*- coding: utf-8 -*-
"""Fetcher 模块"""

from .base import IApiFetcher, ILocalFetcher
from .api.sina import SinaFetcher
from .api.tencent import TencentFetcher
from .api.eastmoney import EastMoneyFetcher
from .local.database_loader import DatabaseLoader

API_FETCHERS = {'sina': SinaFetcher, 'tencent': TencentFetcher, 'eastmoney': EastMoneyFetcher}

def get_api_fetcher(name: str = 'sina') -> IApiFetcher:
    return API_FETCHERS.get(name, SinaFetcher)()

def get_local_fetcher() -> ILocalFetcher:
    return DatabaseLoader()

__all__ = ['IApiFetcher', 'ILocalFetcher', 'SinaFetcher', 'TencentFetcher', 'EastMoneyFetcher', 'DatabaseLoader', 'get_api_fetcher', 'get_local_fetcher', 'API_FETCHERS']

import requests
from collections import namedtuple
from datetime import  timezone
from logging import getLogger
from functools import wraps
from pmgaiorest import ApiBase

logger = getLogger(__name__)

Page = namedtuple('Page', 'items page_number number_of_pages total_count')

def params_add_columns(params, columns):
    if not params:
        params = {}
    params['columns'] = ','.join(columns)
    return params

class SimProApi(ApiBase):
    def __init__(self, aiohttp_session, base_url, header_args,
            handle_reconnect=None):
        super().__init__(aiohttp_session,
                base_url,
                header_args,
                handle_reconnect=handle_reconnect)

    async def get_invoice_pages(self, *,
            page_size=None, params=None, modified_since=None):
        async for page in self._get_pages(
                self.get_invoice_page,
                page_size=page_size,
                params=params,
                modified_since=modified_since):
            yield page

    async def get_invoice_page(self, *,
            page_number=1, page_size=None, params=None, modified_since=None):
        return await self._get_page('customerInvoices/',
                    page_number, page_size, params, modified_since)

    async def get_site(self, site_id):
        return await self.get(f'sites/{site_id}')

    async def _get_pages(self, page_callable, *,
            page_size=None, params=None, modified_since=None):
        page_number = 1
        while True:
            page = await page_callable(
                    page_number=page_number,
                    page_size=page_size,
                    params=params,
                    modified_since=modified_since)
            yield page
            page_number += 1
            if page_number >= page.number_of_pages:
                break

    async def _get_page(self, path, page_number, page_size, params, modified_since):
        params = params or {}
        if page_size is not None:
            params['page'] = page_number or 1
            params['pageSize'] = page_size

        in_headers = {}
        if modified_since is not None:
            mod_time = modified_since.astimezone(tz=timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')
            in_headers = {'If-Modified-Since': mod_time}

        json, headers = await self.get_with_headers(path, params=params, headers=in_headers)

        return Page(items=json, page_number=page_number, number_of_pages=int(headers['Result-Pages']),
                total_count=int(headers['Result-Total']))


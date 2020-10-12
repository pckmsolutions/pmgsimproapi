import requests
from collections import namedtuple
from datetime import  timezone
from logging import getLogger

logger = getLogger(__name__)

Page = namedtuple('Page', 'items page_number number_of_pages total_count')

def params_add_columns(params, columns):
    if not params:
        params = {}
    params['columns'] = ','.join(columns)
    return params

class SimProApi:
    def __init__(self, aiohttp_session, base_url, token_type, access_token,
            handle_reconnect=None):
        self.aiohttp_session = aiohttp_session
        self.base_url = base_url
        self.base_headers = simpro_headers(token_type, access_token)
        self.get = self._resp_wrap(self.aiohttp_session.get, handle_reconnect)
        self.get_with_headers = self._resp_wrap(
                self.aiohttp_session.get, handle_reconnect, with_headers=True)

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
        return await self._get_page(self._path('customerInvoices/'),
                    page_number, page_size, params, modified_since)

    async def get_site(self, site_id):
        return await self.get(self._path(f'sites/{site_id}'))

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

    def _path(self, suffix):
        return self.base_url + '/' + suffix

    def _resp_wrap(self, f, handle_reconnect, *, with_headers=False):
        async def wrapper(*args, **kwargs):
            headers = kwargs.pop('headers',{})
            headers.update(self.base_headers)

            attempts = 0
            while True:
                resp = await f(*args, headers=headers, **kwargs)

                if resp.status == 200:
                    json = await resp.json() 
                    return (json if not with_headers
                            else (json, resp.headers))

                if handle_reconnect is None or attempts > 0:
                    resp.raise_for_status()

                attemps += 1

                if resp.status != requests.status_codes.codes['unauthorized']:
                    resp.raise_for_status()

                logger.warning('Request unauthorised - attempting to reconnect')

                token_type, access_token = handle_reconnect()
                self.base_headers = simpro_headers(token_type, access_token)
                headers.update(self.base_headers)
    
                if not token_type or not access_token:
                    # original error
                    resp.raise_for_status()
    
        return wrapper

def simpro_headers(token_type, access_token):
    return {'Authorization': f'{token_type} {access_token}',
            'Content-Type': 'application/json'}


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
    def __init__(self, base_url, token_type, access_token,
            handle_reconnect=None):
        self.base_url = base_url
        self._set_callers(token_type, access_token, handle_reconnect)

    def _set_callers(self, token_type, access_token, handle_reconnect):
        hdrs = headers(token_type, access_token)
        self.get = self._resp_wrap(requests.get, hdrs, handle_reconnect)
        self.get_with_headers = self._resp_wrap(
                requests.get, hdrs, handle_reconnect, with_headers=True)

    def get_invoice_pages(self, page_size, *, params=None, modified_since=None):
        page_number = 1
        while True:
            page = self._get_page(self._path('customerInvoices/'),
                    page_number, page_size, params, modified_since)
            yield page
            page_number += 1
            if page_number >= page.number_of_pages:
                break

    def get_site(self, site_id):
        return self.get(self._path(f'sites/{site_id}'))

    def _get_page(self, path, page, page_size, params, modified_since):
        params = params or {}
        params['page'] = page
        params['pageSize'] = page_size

        in_headers = {}
        if modified_since is not None:
            mod_time = modified_since.astimezone(tz=timezone.utc).strftime('%a, %d %b %Y %H:%M:%S GMT')
            in_headers = {'If-Modified-Since': mod_time}

        json, headers = self.get_with_headers(path, params=params, headers=in_headers)

        return Page(items=json, page_number=page, number_of_pages=int(headers['Result-Pages']),
                total_count=int(headers['Result-Total']))

    def _path(self, suffix):
        return self.base_url + '/' + suffix

    def _resp_wrap(self, f, headers, handle_reconnect, *, with_headers=False):
        def wrapper(*args, **kwargs):
            _headers = kwargs.pop('headers',{})
            _headers.update(headers)
            resp = f(*args, headers=_headers, **kwargs)
            if resp.ok:
                json = resp.json() 
                return (json if not with_headers
                        else (json, resp.headers))

            if handle_reconnect is None:
                resp.raise_for_status()

            if resp.status_code != requests.status_codes.codes['unauthorized']:
                resp.raise_for_status()

            logger.warning('Request unauthorised - attempting to reconnect')

            token_type, access_token = handle_reconnect()
    
            if not token_type or not access_token:
                # original error
                resp.raise_for_status()
    
            self._set_callers(token_type, access_token, handle_reconnect)

            resp = f(*args, headers=_headers, **kwargs)
            if not resp.ok:
                resp.raise_for_status()
            return resp.json()
        return wrapper

def headers(token_type, access_token):
    return {'Authorization': f'{token_type} {access_token}',
            'Content-Type': 'application/json'}


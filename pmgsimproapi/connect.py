import requests
from datetime import datetime, timedelta
from getpass import getpass
from requests.exceptions import HTTPError
from logging import getLogger
from urllib.parse import urlparse, urljoin

from .api import SimProApi
from .exceptions import LogonFailure

api_url_suffix = 'api/v1.0'
logger = getLogger(__name__)

class SimProConnect:
    def __init__(self, aiohttp_session, token_url, client_id, client_secret,
            company, new_token_callable = None):
        self.aiohttp_session = aiohttp_session
        self.token_url = token_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.company = company
        self.new_token_callable = new_token_callable
        self.token_config = None

    def token_config_connect(self, token_config):
        self.token_config = token_config
        return self.create_api()

    def cli_connect(self, user=None, password=None):
        if user is None:
            user = input('simPro User: ')
            password = None
        if password is None:
            password = getpass('simPro Password: ')
        self.token_config = self.fetch_tokens(username=user, password=password)
        return self.create_api()
    
    def _handle_reconnect(self):
        logger.info('Reconnecting using refresh token.')
        token_config = self.fetch_tokens(
                refresh_token=self.token_config['refresh_token'])
        if not token_config:
            logger.error('Failed to reconnect.')
            return None
    
        self.token_config = token_config

        if self.new_token_callable is not None:
            self.new_token_callable(self.token_config)
        #return (self.token_config['token_type'],
        #        self.token_config['access_token'])

        return _header_args(token_type=self.token_config['token_type'],
                access_token=self.token_config['access_token']),
    
    def fetch_tokens(self, *, username=None, password=None, refresh_token=None):
        args = {'client_id': self.client_id,
                'client_secret': self.client_secret}
    
        if username is not None:
            assert password is not None
            assert refresh_token is None
            args['grant_type'] = 'password'
            args['username'] = username
            args['password'] = password
        else:
            args['grant_type'] = 'refresh_token'
            args['refresh_token'] = refresh_token
    
        resp = requests.post(self.token_url, data=args)
        if not resp.ok:
            logger.error(f'Error feting tokens {resp.status_code} / {resp.text[:100]}.')
            if resp.status_code == 400 or resp.status_code == 401:
                raise LogonFailure()
            return None

        return resp.json()
    
    def create_api(self):
        if not self.token_config:
            logger.error('Invalid config. Unable to connect to simPRO')
            return

        access_token = self.token_config['access_token']
        token_type = self.token_config['token_type']
    
        parse = urlparse(self.token_url)
        new_path = '/'.join((api_url_suffix, 'companies', self.company),)
        base_url = urljoin(parse.geturl()[:-len(parse.path)], new_path)
    
        return SimProApi(self.aiohttp_session,
                base_url,
                _header_args(token_type=token_type, access_token=access_token),
                self._handle_reconnect)

def _header_args(*, token_type, access_token):
    return locals()


import requests
from datetime import datetime, timedelta
from getpass import getpass
from requests.exceptions import HTTPError
from logging import getLogger
from urllib.parse import urljoin

from .exceptions import LogonFailure

api_url_suffix = 'api/v1.0'
token_url_suffix = 'oauth2/token'
logger = getLogger(__name__)

try:
    from .api import SimProApi
except ModuleNotFoundError:
    logger.warn('Skipping asyncio support')


class SimProConnect:
    def __init__(self, *, aiohttp_session, base_url, client_id, client_secret,
            company, new_token_callable = None):
        self.aiohttp_session = aiohttp_session
        self.base_url = base_url
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
                access_token=self.token_config['access_token'])
    
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
            assert refresh_token is not None
            args['grant_type'] = 'refresh_token'
            args['refresh_token'] = refresh_token

        resp = requests.post('/'.join((self.base_url, token_url_suffix),), 
                data=args)
        if not resp.ok:
            logger.error(f'Error feting tokens {resp.status_code}'
                    + ' / {resp.text[:100]}.')
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
    
        base_url = urljoin(self.base_url,
                '/'.join((api_url_suffix, 'companies', self.company),))
    
        return SimProApi(self.aiohttp_session,
                base_url,
                _header_args(token_type=token_type, access_token=access_token),
                self._handle_reconnect)

def _header_args(*, token_type, access_token):
    return {'token_type': token_type, 'access_token': access_token}


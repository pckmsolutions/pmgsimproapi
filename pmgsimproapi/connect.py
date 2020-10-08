import requests
from datetime import datetime, timedelta
from getpass import getpass
from requests.exceptions import HTTPError
from logging import getLogger

from .api import SimProApi

token_url_suffix = 'oauth2/token'
api_url_suffix = 'api/v1.0'
logger = getLogger(__name__)

class SimProConnect:
    def __init__(self, base_url, client_id, client_secret, company):
        self.base_url = base_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.company = company
        self.token_config = None

    def token_config_connect(self, token_config):
        self.token_config = token_config
        return self.create_api()

    def cli_connect(self, user=None, password=None):
        user = input('simPro User: ')
        password = getpass('simPro Password: ')
        self.token_config = self.fetch_tokens(username=user, password=password)
        return self.create_api()
    
    def _handle_reconnect(self):
        token_config = self.fetch_tokens(
                refresh_token=self.token_config['refresh_token'])
        if not token_config:
            logger.error('Failed to reconnect.')
            return None, None
    
        self.token_config = token_config
        return (self.token_config['token_type'],
                self.token_config['access_token'])
    
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
    
        resp = requests.post('/'.join((self.base_url, token_url_suffix),), data=args)
        if not resp.ok:
            logger.error(f'Error feting tokens {resp.status_code} / {resp.text[:100]}.')
            return None

        return resp.json()
    
    def create_api(self):
        if not self.token_config:
            logger.error('Invalid config. Unable to connect to simPRO')
            return

        access_token = self.token_config['access_token']
        token_type = self.token_config['token_type']
    
        base_url = '/'.join((self.base_url,
            api_url_suffix, 'companies', self.company),)
    
        return SimProApi(base_url, token_type, access_token, self._handle_reconnect)


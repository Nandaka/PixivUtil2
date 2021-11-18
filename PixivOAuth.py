#!C:/Python37-32/python
# -*- coding: utf-8 -*-

import hashlib
import json
import os
import random
import ssl
import sys
from collections import OrderedDict
from datetime import datetime
from typing import Dict

import cloudscraper
import requests

import PixivHelper
import PixivOAuthBrowser


# monkey patch cloudscraper.User_Agent.loadUserAgent function
# this is to allow to bundle browser.json in the package
# based on cloudscraper==1.2.56
def loadUserAgent(self, *args, **kwargs):
    self.browser = kwargs.pop('browser', None)

    self.platforms = ['linux', 'windows', 'darwin', 'android', 'ios']
    self.browsers = ['chrome', 'firefox']

    if isinstance(self.browser, dict):
        self.custom = self.browser.get('custom', None)
        self.platform = self.browser.get('platform', None)
        self.desktop = self.browser.get('desktop', True)
        self.mobile = self.browser.get('mobile', True)
        self.browser = self.browser.get('browser', None)
    else:
        self.custom = kwargs.pop('custom', None)
        self.platform = kwargs.pop('platform', None)
        self.desktop = kwargs.pop('desktop', True)
        self.mobile = kwargs.pop('mobile', True)

    if not self.desktop and not self.mobile:
        sys.tracebacklimit = 0
        raise RuntimeError("Sorry you can't have mobile and desktop disabled at the same time.")

    # resolve browser.json path if frozen
    default_browser_json = os.path.dirname(sys.executable) + os.sep + 'browsers.json'
    PixivHelper.get_logger().debug(f"browser.json location = {default_browser_json}")
    # end changes

    with open(default_browser_json, 'r') as fp:
        user_agents = json.load(
            fp,
            object_pairs_hook=OrderedDict
        )

    if self.custom:
        if not self.tryMatchCustom(user_agents):
            self.cipherSuite = [
                ssl._DEFAULT_CIPHERS,
                '!AES128-SHA',
                '!ECDHE-RSA-AES256-SHA',
            ]
            self.headers = OrderedDict([
                ('User-Agent', self.custom),
                ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8'),
                ('Accept-Language', 'en-US,en;q=0.9'),
                ('Accept-Encoding', 'gzip, deflate, br')
            ])
    else:
        if self.browser and self.browser not in self.browsers:
            sys.tracebacklimit = 0
            raise RuntimeError(f'Sorry "{self.browser}" browser is not valid, valid browsers are [{", ".join(self.browsers)}].')

        if not self.platform:
            self.platform = random.SystemRandom().choice(self.platforms)

        if self.platform not in self.platforms:
            sys.tracebacklimit = 0
            raise RuntimeError(f'Sorry the platform "{self.platform}" is not valid, valid platforms are [{", ".join(self.platforms)}]')

        filteredAgents = self.filterAgents(user_agents['user_agents'])

        if not self.browser:
            # has to be at least one in there...
            while not filteredAgents.get(self.browser):
                self.browser = random.SystemRandom().choice(list(filteredAgents.keys()))

        if not filteredAgents[self.browser]:
            sys.tracebacklimit = 0
            raise RuntimeError(f'Sorry "{self.browser}" browser was not found with a platform of "{self.platform}".')

        self.cipherSuite = user_agents['cipherSuite'][self.browser]
        self.headers = user_agents['headers'][self.browser]

        self.headers['User-Agent'] = random.SystemRandom().choice(filteredAgents[self.browser])

    if not kwargs.get('allow_brotli', False) and 'br' in self.headers['Accept-Encoding']:
        self.headers['Accept-Encoding'] = ','.join([
            encoding for encoding in self.headers['Accept-Encoding'].split(',') if encoding.strip() != 'br'
        ]).strip()


def create_scraper(sess=None, **kwargs):
    """
    Convenience function for creating a ready-to-go CloudScraper object.
    """
    scraper = cloudscraper.CloudScraper(**kwargs)

    if sess:
        for attr in ['auth', 'cert', 'cookies', 'headers', 'hooks', 'params', 'proxies', 'data', 'verify']:
            val = getattr(sess, attr, None)
            if val:
                setattr(scraper, attr, val)
    return scraper
# end monkey patch


class PixivOAuth():
    _username: str = None
    _password: str = None
    _refresh_token: str = None
    _access_token: str = None
    _url: str = "https://oauth.secure.pixiv.net/auth/token"
    _proxies: Dict[str, str] = None
    _tzInfo: PixivHelper.LocalUTCOffsetTimezone = None
    _validate_ssl: bool = True

    sess = requests.Session()
    if PixivHelper.we_are_frozen():
        PixivHelper.get_logger().debug("Running from executable version for PixivOAuth")
        # 842 always refer to local cacert.pem ca bundle if frozen
        sess.verify = os.path.dirname(sys.executable) + os.sep + 'cacert.pem'
        # monkey patch load user agent
        cloudscraper.User_Agent.loadUserAgent = loadUserAgent
        cloudscraper.create_scraper = create_scraper
    _req = cloudscraper.create_scraper(sess=sess)

    def __init__(self, username, password, proxies=None, validate_ssl=True, refresh_token=None):
        if username is None or len(username) <= 0:
            raise Exception("Username cannot empty!")
        if password is None or len(password) <= 0:
            raise Exception("Password cannot empty!")

        self._username = username
        self._password = password
        self._proxies = proxies
        if refresh_token is not None and len(refresh_token) > 0:
            self._refresh_token = refresh_token
        else:
            self._refresh_token = None
        self._access_token = None
        self._tzInfo = PixivHelper.LocalUTCOffsetTimezone()
        self._validate_ssl = validate_ssl
        PixivOAuthBrowser.set_proxy(proxies)
        PixivOAuthBrowser.set_verify(validate_ssl)

    def _get_default_values(self):
        return {'client_id': PixivOAuthBrowser.CLIENT_ID,
                'client_secret': PixivOAuthBrowser.CLIENT_SECRET,
                'device_token': 'pixiv',
                'get_secure_url': 'true',
                'include_policy': 'true'}

    def _get_values_for_refresh(self):
        values = self._get_default_values()
        values['refresh_token'] = self._refresh_token
        values['grant_type'] = 'refresh_token'
        return values

    def _get_values_for_login(self):
        values = self._get_default_values()
        values['username'] = self._username
        values['password'] = self._password
        values['grant_type'] = 'password'
        return values

    def _get_default_headers(self):
        # fix #530
        # 2019-11-17T10:04:40+8.00
        time = "{0}{1}".format(datetime.now().isoformat()[0:19], self._tzInfo)
        secret = "28c1fdd170a5204386cb1313c7077b34f83e4aaf4aa829ce78c231e05b0bae2c"
        time_hash = hashlib.md5("{0}{1}".format(time, secret).encode('utf-8'))
        return {'User-Agent': PixivOAuthBrowser.USER_AGENT,
                'Accept-Language': 'en_US',
                'App-OS': 'android',
                'App-OS-Version': '4.4.2',
                'App-Version': '5.0.145',
                'X-Client-Time': time,
                'X-Client-Hash': time_hash.hexdigest()}

    def _get_headers_with_bearer(self):
        if self._access_token is None:
            self.login()

        headers = self._get_default_headers()
        headers["Authorization"] = "Bearer {0}".format(self._access_token)
        return headers

    def login_with_username_and_password(self):
        PixivHelper.get_logger().info("Login to OAuth using username and password.")
        oauth_response = self._req.post(self._url,
                                        data=self._get_values_for_login(),
                                        headers=self._get_default_headers(),
                                        proxies=self._proxies,
                                        verify=self._validate_ssl)
        return oauth_response

    def login(self):
        oauth_response = None
        need_relogin = True
        if self._refresh_token is not None:
            PixivHelper.get_logger().info("Login to OAuth using refresh token.")
            oauth_response = self._req.post(self._url,
                                            data=self._get_values_for_refresh(),
                                            headers=self._get_default_headers(),
                                            proxies=self._proxies,
                                            verify=self._validate_ssl)
            if oauth_response.status_code == 200:
                need_relogin = False
            else:
                PixivHelper.get_logger().info("OAuth Refresh Token invalid, Relogin needed.")

        if need_relogin:
            # Semi Auto handling to get the refresh token
            oauth_response = PixivOAuthBrowser.login()

        PixivHelper.get_logger().debug("%s: %s", oauth_response.status_code, oauth_response.text)
        if oauth_response.status_code == 200:
            info = json.loads(oauth_response.text)
            self._refresh_token = info["response"]["refresh_token"]
            self._access_token = info["response"]["access_token"]
        elif oauth_response.status_code in (400, 403):
            info = oauth_response.text
            try:
                info = json.loads(info)["errors"]["system"]["message"]
            except (ValueError, KeyError):
                if info is not None:
                    PixivHelper.dump_html("Error - oAuth login.html", info)

            PixivHelper.print_and_log('error', info)
            # raise PixivException("Failed to login using OAuth, follow instruction in https://gist.github.com/ZipFile/c9ebedb224406f4f11845ab700124362 to get the refresh token.", PixivException.OAUTH_LOGIN_ISSUE)

        return oauth_response

    def get_user_info(self, userid):
        url = 'https://app-api.pixiv.net/v1/user/detail?user_id={0}'.format(userid)
        user_info = self._req.get(url,
                                  headers=self._get_headers_with_bearer(),
                                  proxies=self._proxies,
                                  verify=self._validate_ssl)

        if user_info.status_code == 404:
            PixivHelper.print_and_log('error', user_info.text)

        return user_info


def test_OAuth():
    from PixivConfig import PixivConfig
    cfg = PixivConfig()
    cfg.loadConfig("./config.ini")
    # proxies = {'http': 'http://localhost:8888',
    #            'https': 'http://localhost:8888'}
    # oauth = PixivOAuth(cfg.username, cfg.password, proxies, False, cfg.refresh_token)

    if cfg.refresh_token is None:
        cfg.refresh_token = PixivOAuthBrowser.login()

    oauth = PixivOAuth(cfg.username, cfg.password, {}, True, cfg.refresh_token)
    # oauth = PixivOAuth(cfg.username, cfg.password, {}, True, None)
    result = oauth.login()
    assert oauth._refresh_token is not None
    print("refresh token {0}".format(oauth._refresh_token))

    assert result.status_code == 200
    if result.status_code == 200:
        info = oauth.get_user_info(2101890)
        print(info.text)
        print("")

        info = oauth.get_user_info(2101890)
        print(info.text)
        print("")

        # suspended user
        info = oauth.get_user_info(39182623)
        print(info.text)
        print("")


if __name__ == '__main__':
    test_OAuth()
    print("done")

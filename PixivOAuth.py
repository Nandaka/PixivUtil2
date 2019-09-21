import requests
import json
from datetime import datetime
import hashlib

import PixivHelper
from PixivHelper import LocalUTCOffsetTimezone
from PixivException import PixivException


class PixivOAuth(object):
    _username = None
    _password = None
    _refresh_token = None
    _access_token = None
    _url = "https://oauth.secure.pixiv.net/auth/token"
    _proxies = None
    _tzInfo = None
    _validate_ssl = True

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
        self._tzInfo = LocalUTCOffsetTimezone()
        self._validate_ssl = validate_ssl

    def _get_default_values(self):
        return {'client_id': 'MOBrBDS8blbauoSck0ZfDbtuzpyT',
              'client_secret': 'lsACyCD94FhDUtGTXi3QzcFE2uU1hqtDaKeqrdwj',
              'device_token': '416eeaafe17577e471b35d2cee7cdfdc',
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
        time = "{0}{1}".format(datetime.now().isoformat()[:19], self._tzInfo)
        secret = "28c1fdd170a5204386cb1313c7077b34f83e4aaf4aa829ce78c231e05b0bae2c"
        time_hash = hashlib.md5("{0}{1}".format(time, secret).encode("ascii"))
        return {'User-Agent': 'PixivAndroidApp/5.0.136 (Android 6.0; Google Pixel C - 6.0.0 - API 23 - 2560x1800)',
                       'Accept-Language': 'en_US',
                       'App-OS': 'android',
                       'App-OS-Version': '4.4.2',
                       'App-Version': '5.0.136',
                       'X-Client-Time': time,
                       'X-Client-Hash': time_hash.hexdigest()}

    def _get_headers_with_bearer(self):
        if self._access_token is None:
            self.login()

        headers = self._get_default_headers()
        headers["Authorization"] = "Bearer {0}".format(self._access_token)
        return headers

    def login_with_username_and_password(self):
        PixivHelper.GetLogger().info("Login to OAuth using username and password.")
        oauth_response = requests.post(self._url,
                                       self._get_values_for_login(),
                                       headers=self._get_default_headers(),
                                       proxies=self._proxies,
                                       verify=self._validate_ssl)
        return oauth_response

    def login(self):
        oauth_response = None
        need_relogin = True
        if self._refresh_token is not None:
            PixivHelper.GetLogger().info("Login to OAuth using refresh token.")
            oauth_response = requests.post(self._url,
                                           self._get_values_for_refresh(),
                                           headers=self._get_default_headers(),
                                           proxies=self._proxies,
                                           verify=self._validate_ssl)
            if oauth_response.status_code == 200:
                need_relogin = False
            else:
                PixivHelper.GetLogger().info("OAuth Refresh Token invalid, Relogin needed.")

        if need_relogin:
            oauth_response = self.login_with_username_and_password()

        PixivHelper.GetLogger().debug("{0}: {1}".format(oauth_response.status_code, oauth_response.text))
        if oauth_response.status_code == 200:
            info = json.loads(oauth_response.text)
            self._refresh_token = info["response"]["refresh_token"]
            self._access_token = info["response"]["access_token"]
        elif oauth_response.status_code == 400:
            info = oauth_response.text
            try:
                info = json.loads(info)["errors"]["system"]["message"]
            except (ValueError, KeyError):
                pass
            PixivHelper.print_and_log('error', info)
            raise PixivException("Failed to login using OAuth", PixivException.OAUTH_LOGIN_ISSUE)

        return oauth_response

    def get_user_info(self, userid):
        url = 'https://app-api.pixiv.net/v1/user/detail?user_id={0}'.format(userid)
        user_info = requests.get(url,
                                  None,
                                  headers=self._get_headers_with_bearer(),
                                  proxies=self._proxies,
                                  verify=self._validate_ssl)

        if user_info.status_code == 404:
            PixivHelper.print_and_log('error', user_info.text)

        return user_info


def test():
    proxies = {'http': 'http://localhost:8888',
               'https': 'http://localhost:8888'}

    from PixivConfig import PixivConfig
    cfg = PixivConfig()
    cfg.loadConfig("./config.ini")
    oauth = PixivOAuth(cfg.username, cfg.password, proxies, False, cfg.refresh_token)
    result = oauth.login()
    if result.status_code == 200:
        info = oauth.get_user_info(2101890)
        print(info)

    print("")
    result = oauth.login()
    if result.status_code == 200:
        info = oauth.get_user_info(2101890)
        print(info)
    print("")

if __name__ == '__main__':
    test()
    print("done")

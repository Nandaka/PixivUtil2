# adapted from https://gist.github.com/ZipFile/c9ebedb224406f4f11845ab700124362
from base64 import urlsafe_b64encode
from hashlib import sha256
from pprint import pprint
from secrets import token_urlsafe
from sys import exit
from urllib.parse import urlencode
from webbrowser import open as open_url

import requests
from colorama import Fore, Style

# Latest app version can be found using GET /v1/application-info/android
USER_AGENT = "PixivAndroidApp/5.0.234 (Android 11; Pixel 5)"
REDIRECT_URI = "https://app-api.pixiv.net/web/v1/users/auth/pixiv/callback"
LOGIN_URL = "https://app-api.pixiv.net/web/v1/login"
AUTH_TOKEN_URL = "https://oauth.secure.pixiv.net/auth/token"
CLIENT_ID = "MOBrBDS8blbauoSck0ZfDbtuzpyT"
CLIENT_SECRET = "lsACyCD94FhDUtGTXi3QzcFE2uU1hqtDaKeqrdwj"


session = requests.Session()


def set_proxy(value):
    session.proxies = value


def set_verify(value):
    session.verify = value


def s256(data):
    """S256 transformation method."""

    return urlsafe_b64encode(sha256(data).digest()).rstrip(b"=").decode("ascii")


def oauth_pkce(transform):
    """Proof Key for Code Exchange by OAuth Public Clients (RFC7636)."""

    code_verifier = token_urlsafe(32)
    code_challenge = transform(code_verifier.encode("ascii"))

    return code_verifier, code_challenge


def print_auth_token_response(response):
    data = response.json()

    try:
        access_token = data["access_token"]
        refresh_token = data["refresh_token"]
    except KeyError:
        print("error:")
        pprint(data)
        exit(1)

    print("access_token:", access_token)
    print("refresh_token:", refresh_token)
    print("expires_in:", data.get("expires_in", 0))
    return data


def login():
    ''' open browser to login and get the code
        :return access token and refresh token'''
    code_verifier, code_challenge = oauth_pkce(s256)
    login_params = {
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "client": "pixiv-android",
    }

    print(Style.BRIGHT + Fore.YELLOW + "Instructions: " + Style.RESET_ALL)
    print("1. This will open a new browser to login to Pixiv site to get the code.")
    print("1b. In case the browser will not open, or you are using an headless server, use this link: " + f"{LOGIN_URL}?{urlencode(login_params)}")
    print("2. Open dev console " + Fore.YELLOW + "(F12)" + Style.RESET_ALL + " and switch to network tab." + Style.RESET_ALL)
    print("3. Enable persistent logging (" + Fore.YELLOW + "\"Preserve log\"" + Style.RESET_ALL + "). " + Style.RESET_ALL)
    print("4. Type into the filter field: '" + Fore.YELLOW + "callback?" + Style.RESET_ALL + "'." + Style.RESET_ALL)
    print("5. Proceed with Pixiv login.")
    print("6. After logging in you should see a blank page and request that looks like this:" + Style.RESET_ALL)
    print("   'https://app-api.pixiv.net/web/v1/users/auth/pixiv/callback?state=...&" + Fore.YELLOW + "code=..." + Style.RESET_ALL + "'" + Style.RESET_ALL)
    print("7. Copy value of the " + Fore.YELLOW + "code param" + Style.RESET_ALL + " into the prompt and hit the Enter key.")
    input("Press enter when you ready.")
    open_url(f"{LOGIN_URL}?{urlencode(login_params)}")

    try:
        code = input("code: ").strip()
    except (EOFError, KeyboardInterrupt):
        return

    response = session.post(
        AUTH_TOKEN_URL,
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code,
            "code_verifier": code_verifier,
            "grant_type": "authorization_code",
            "include_policy": "true",
            "redirect_uri": REDIRECT_URI,
        },
        headers={"User-Agent": USER_AGENT},
    )
    return response
    # login_data = print_auth_token_response(response)
    # return login_data


def refresh(refresh_token):
    ''' :return new access token and refresh token '''
    response = session.post(
        AUTH_TOKEN_URL,
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "refresh_token",
            "include_policy": "true",
            "refresh_token": refresh_token,
        },
        headers={"User-Agent": USER_AGENT},
    )
    login_data = print_auth_token_response(response)
    return login_data


if __name__ == "__main__":
    login()

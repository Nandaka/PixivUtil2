/// PKCE-based OAuth login helper.
///
/// Port of the Python `PixivOAuthBrowser`, which handles the
/// `code_verifier`/`code_challenge` flow used by Pixiv's web auth.
library;

import 'dart:convert';
import 'dart:math';

import 'package:crypto/crypto.dart' as crypto;
import 'package:http/http.dart' as http;

import 'pixiv_exception.dart';

class PixivOAuthBrowser {
  static const String _clientId = 'MOBrBDS8blbauoSck0ZfDbtuzpyT';
  static const String _clientSecret =
      'lsACyCD94FhDUtGTXi3QzcFE2uU1hqtDaKeqrdwj';
  static const String _redirectUri =
      'https://app-api.pixiv.net/web/v1/users/auth/pixiv/callback';
  static const String _loginUrl = 'https://app-api.pixiv.net/web/v1/login';
  static const String _authTokenUrl =
      'https://oauth.secure.pixiv.net/auth/token';
  static const String _userAgent =
      'PixivAndroidApp/5.0.234 (Android 11; Pixel 5)';

  late String _codeVerifier;
  late String _codeChallenge;

  PixivOAuthBrowser() {
    _codeVerifier = _generateCodeVerifier();
    _codeChallenge = _generateCodeChallenge(_codeVerifier);
  }

  String get codeVerifier => _codeVerifier;
  String get codeChallenge => _codeChallenge;

  String getLoginUrl() {
    final params = {
      'code_challenge': _codeChallenge,
      'code_challenge_method': 'S256',
      'client': 'pixiv-android',
    };
    final qs = params.entries
        .map((e) => '${Uri.encodeComponent(e.key)}=${Uri.encodeComponent(e.value)}')
        .join('&');
    return '$_loginUrl?$qs';
  }

  Future<Map<String, dynamic>> exchangeCode(String code) async {
    final response = await http.post(
      Uri.parse(_authTokenUrl),
      headers: {
        'User-Agent': _userAgent,
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: {
        'client_id': _clientId,
        'client_secret': _clientSecret,
        'code': code,
        'code_verifier': _codeVerifier,
        'grant_type': 'authorization_code',
        'include_policy': 'true',
        'redirect_uri': _redirectUri,
      },
    );
    if (response.statusCode != 200) {
      throw PixivException(
        'OAuth exchange failed (${response.statusCode}): ${response.body}',
        errorCode: PixivException.OAUTH_LOGIN_ISSUE,
      );
    }
    return jsonDecode(response.body) as Map<String, dynamic>;
  }

  static String _generateCodeVerifier() {
    final random = Random.secure();
    final bytes = List<int>.generate(32, (_) => random.nextInt(256));
    return base64UrlEncode(bytes).replaceAll('=', '');
  }

  static String _generateCodeChallenge(String verifier) {
    final hash = crypto.sha256.convert(utf8.encode(verifier)).bytes;
    return base64UrlEncode(hash).replaceAll('=', '');
  }
}

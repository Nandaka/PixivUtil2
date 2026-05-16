/// Pixiv OAuth manager (port of `PixivOAuth.py`).
library;

import 'dart:convert';

import 'package:crypto/crypto.dart' as crypto;
import 'package:http/http.dart' as http;

import 'pixiv_exception.dart';

/// OAuth client for Pixiv's mobile API.
class PixivOAuth {
  static const String _clientId = 'MOBrBDS8blbauoSck0ZfDbtuzpyT';
  static const String _clientSecret =
      'lsACyCD94FhDUtGTXi3QzcFE2uU1hqtDaKeqrdwj';
  static const String _hashSecret =
      '28c1fdd170a5204386cb1313c7077b34f83e4aaf4aa829ce78c231e05b0bae2c';
  static const String _redirectUri = 'https://app-api.pixiv.net/web/v1/users/auth/pixiv/callback';

  final String? username;
  final String? password;
  String? refreshToken;
  String? accessToken;
  final Map<String, String>? proxies;
  final bool validateSsl;
  DateTime? _expiresAt;

  PixivOAuth(
    this.username,
    this.password, {
    this.proxies,
    this.refreshToken,
    this.validateSsl = true,
  });

  bool get isAuthenticated =>
      accessToken != null && (_expiresAt?.isAfter(DateTime.now()) ?? false);

  /// Returns headers for the API call (X-Client-Time and X-Client-Hash).
  Map<String, String> _hashHeaders() {
    final time = DateTime.now().toUtc().toIso8601String();
    final hashInput = '$time$_hashSecret';
    final hash = crypto.md5.convert(utf8.encode(hashInput)).toString();
    return {
      'X-Client-Time': time,
      'X-Client-Hash': hash,
      'User-Agent': 'PixivAndroidApp/5.0.234 (Android 11; Pixel 5)',
      'App-OS': 'android',
      'App-OS-Version': '11',
      'App-Version': '5.0.234',
    };
  }

  /// Refresh the access token using the refresh token.
  Future<void> doRefresh() async {
    if (refreshToken == null || refreshToken!.isEmpty) {
      throw PixivException(
        'No refresh token. Cannot OAuth-login.',
        errorCode: PixivException.OAUTH_LOGIN_ISSUE,
      );
    }
    final response = await http.post(
      Uri.parse('https://oauth.secure.pixiv.net/auth/token'),
      headers: _hashHeaders()
        ..addAll({'Content-Type': 'application/x-www-form-urlencoded'}),
      body: {
        'client_id': _clientId,
        'client_secret': _clientSecret,
        'grant_type': 'refresh_token',
        'include_policy': 'true',
        'refresh_token': refreshToken!,
      },
    );
    if (response.statusCode != 200) {
      throw PixivException(
        'OAuth refresh failed (${response.statusCode}): ${response.body}',
        errorCode: PixivException.OAUTH_LOGIN_ISSUE,
      );
    }
    final data = jsonDecode(response.body) as Map<String, dynamic>;
    accessToken = data['access_token'] as String?;
    refreshToken = data['refresh_token'] as String? ?? refreshToken;
    final expiresIn = (data['expires_in'] as num?)?.toInt() ?? 3600;
    _expiresAt = DateTime.now().add(Duration(seconds: expiresIn));
  }

  /// Returns the authorization header value (`Bearer <token>`).
  Future<String> authHeader() async {
    if (!isAuthenticated) await doRefresh();
    return 'Bearer $accessToken';
  }

  /// Generic GET against `app-api.pixiv.net`.
  Future<Map<String, dynamic>> getJson(String url,
      {Map<String, String>? headers, Map<String, String>? params}) async {
    final auth = await authHeader();
    final uri = Uri.parse(url).replace(queryParameters: params);
    final response = await http.get(uri,
        headers: _hashHeaders()
          ..['Authorization'] = auth
          ..addAll(headers ?? const {}));
    if (response.statusCode >= 400) {
      throw PixivException(
        'OAuth GET $url failed (${response.statusCode}): ${response.body}',
        errorCode: PixivException.OAUTH_LOGIN_ISSUE,
      );
    }
    return jsonDecode(response.body) as Map<String, dynamic>;
  }
}

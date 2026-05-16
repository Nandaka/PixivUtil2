/// Browser wrapper that talks to Pixiv's web API.
///
/// This is a Dart port of the original Python `PixivBrowserFactory`.
/// It uses the `http` package + a custom `cookie_jar` for cookie handling.
library;

import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:cookie_jar/cookie_jar.dart';
import 'package:http/http.dart' as http;

import '../model/pixiv_artist.dart';
import '../model/pixiv_bookmark.dart';
import '../model/pixiv_image.dart';
import '../model/pixiv_model_fanbox.dart';
import '../model/pixiv_model_sketch.dart';
import '../model/pixiv_novel.dart';
import '../model/pixiv_ranking.dart';
import '../model/pixiv_tags.dart';
import 'pixiv_config.dart';
import 'pixiv_exception.dart';
import 'pixiv_helper.dart' as pixiv_helper;
import 'pixiv_oauth.dart';

PixivBrowser? _defaultBrowser;
CookieJar? _defaultCookieJar;

const _setCookieAttributeNames = {
  'domain',
  'expires',
  'httponly',
  'max-age',
  'path',
  'samesite',
  'secure',
};

/// Get the default browser instance.
PixivBrowser? getBrowser() => _defaultBrowser;

/// Build (or return) the global PixivBrowser instance.
PixivBrowser createBrowser({PixivConfig? config, CookieJar? cookieJar}) {
  _defaultCookieJar ??= cookieJar ?? CookieJar();
  _defaultBrowser ??= PixivBrowser(
    config: config ?? PixivConfig(),
    cookieJar: _defaultCookieJar!,
  );
  return _defaultBrowser!;
}

/// Reset the global browser/cookie jar.
void resetBrowser() {
  _defaultBrowser = null;
  _defaultCookieJar = null;
}

class PixivBrowser {
  final PixivConfig config;
  final CookieJar cookieJar;
  final http.Client _client;

  // Simple TTL cache.
  final Map<String, _CacheEntry> _cache = {};
  static const int _maxCache = 10000;

  int _myId = 0;
  bool _isPremium = false;
  int _xRestrict = 0;
  String _locale = '';
  bool _isLoggedInToFanbox = false;
  PixivOAuth? _oauthManager;

  int get myId => _myId;
  bool get isPremium => _isPremium;
  int get xRestrict => _xRestrict;
  String get locale => _locale;
  bool get isLoggedInToFanbox => _isLoggedInToFanbox;

  PixivBrowser({required this.config, required this.cookieJar})
      : _client = http.Client();

  PixivOAuth get oauthManager {
    return _oauthManager ??= PixivOAuth(
      config.username,
      config.password,
      proxies: config.useProxy ? config.proxy : null,
      refreshToken: config.refreshToken,
      validateSsl: config.enableSSLVerification,
    );
  }

  /// Close any open resources.
  void close() => _client.close();

  /// Clear browser history (no-op in this Dart port).
  void clearHistory() {}

  /// Make a generic GET request and return the response body.
  Future<String> getContent(String url, {Map<String, String>? headers}) async {
    final mergedHeaders = await _buildHeaders(url, headers);
    pixiv_helper.getLogger().fine('GET $url');
    final response =
        await _client.get(Uri.parse(url), headers: mergedHeaders).timeout(
              Duration(seconds: config.timeout),
            );
    if (response.statusCode == 302) {
      // Don't follow auth redirects.
      throw PixivException('HTTP 302: ${response.headers['location']}',
          errorCode: PixivException.NOT_LOGGED_IN);
    }
    if (response.statusCode >= 400) {
      throw PixivException('HTTP ${response.statusCode} on $url',
          errorCode: PixivException.SERVER_ERROR, htmlPage: response.body);
    }
    _saveCookies(url, response);
    return response.body;
  }

  /// POST request returning the response body.
  Future<String> postContent(
    String url, {
    Map<String, String>? headers,
    dynamic body,
  }) async {
    final mergedHeaders = await _buildHeaders(url, headers);
    pixiv_helper.getLogger().fine('POST $url');
    final response = await _client
        .post(Uri.parse(url), headers: mergedHeaders, body: body)
        .timeout(Duration(seconds: config.timeout));
    if (response.statusCode >= 400) {
      throw PixivException('HTTP ${response.statusCode} on $url',
          errorCode: PixivException.SERVER_ERROR, htmlPage: response.body);
    }
    _saveCookies(url, response);
    return response.body;
  }

  /// Get raw bytes for a URL (used for downloading images).
  Future<List<int>> getBytes(String url, {Map<String, String>? headers}) async {
    final mergedHeaders = await _buildHeaders(url, headers);
    final response = await _client
        .get(Uri.parse(url), headers: mergedHeaders)
        .timeout(Duration(seconds: config.timeout));
    if (response.statusCode >= 400) {
      throw PixivException('HTTP ${response.statusCode} on $url',
          errorCode: PixivException.DOWNLOAD_FAILED_NETWORK);
    }
    return response.bodyBytes;
  }

  Future<Map<String, String>> _buildHeaders(
      String url, Map<String, String>? headers) async {
    final uri = Uri.parse(url);
    final h = <String, String>{
      'User-Agent': config.useragent,
      'Accept': '*/*',
    };
    if (headers != null) h.addAll(headers);

    final cookieValues = <String, String>{};
    cookieValues.addAll(parseCookieHeader(h.remove('Cookie')));
    if (uri.host == 'pixiv.net' || uri.host.endsWith('.pixiv.net')) {
      cookieValues.addAll(parseCookieHeader(config.cookie));
    }

    final cookies = await cookieJar.loadForRequest(uri);
    if (cookies.isNotEmpty) {
      for (final cookie in cookies) {
        cookieValues[cookie.name] = cookie.value;
      }
    }
    if (cookieValues.isNotEmpty) {
      h['Cookie'] =
          cookieValues.entries.map((e) => '${e.key}=${e.value}').join('; ');
    }
    return h;
  }

  Future<void> _saveCookies(String url, http.Response response) async {
    final raw = response.headers['set-cookie'];
    if (raw == null || raw.isEmpty) return;
    final cookies = <Cookie>[];
    for (final part in _splitSetCookie(raw)) {
      try {
        cookies.add(Cookie.fromSetCookieValue(part));
      } catch (_) {}
    }
    await cookieJar.saveFromResponse(Uri.parse(url), cookies);
  }

  static List<String> _splitSetCookie(String header) {
    // http package merges Set-Cookie headers with ", " between them. This is a
    // best-effort split that respects comma-in-date.
    final result = <String>[];
    final re = RegExp(r',(?=[^,;]+=[^,;]+)(?!\s*\d{2}[-A-Za-z]{3}\s\d{4})');
    for (final s in header.split(re)) {
      if (s.trim().isNotEmpty) result.add(s.trim());
    }
    return result;
  }

  static Map<String, String> parseCookieHeader(String? header) {
    if (header == null) return const {};
    var raw = header.trim();
    if (raw.isEmpty) return const {};
    if (raw.toLowerCase().startsWith('cookie:')) {
      raw = raw.substring(raw.indexOf(':') + 1).trim();
    }

    final values = <String, String>{};
    for (final part in raw.split(';')) {
      final trimmed = part.trim();
      final separator = trimmed.indexOf('=');
      if (separator <= 0) continue;

      final name = trimmed.substring(0, separator).trim();
      final lowerName = name.toLowerCase();
      if (name.isEmpty || _setCookieAttributeNames.contains(lowerName)) {
        continue;
      }

      values[name] = trimmed.substring(separator + 1).trim();
    }
    return values;
  }

  void _putCache(String key, dynamic item, {int expirationSeconds = 3600}) {
    final expiry = DateTime.now()
        .add(Duration(seconds: expirationSeconds))
        .millisecondsSinceEpoch;
    _cache[key] = _CacheEntry(item, expiry);
    if (_cache.length > _maxCache) {
      String? oldest;
      int? oldestExpiry;
      _cache.forEach((k, v) {
        if (oldestExpiry == null || v.expiry < oldestExpiry!) {
          oldest = k;
          oldestExpiry = v.expiry;
        }
      });
      if (oldest != null) _cache.remove(oldest);
    }
  }

  dynamic _getCache(String key, {int slidingWindowSeconds = 3600}) {
    final entry = _cache.remove(key);
    if (entry == null) return null;
    if (entry.expiry > DateTime.now().millisecondsSinceEpoch) {
      _cache[key] =
          _CacheEntry(entry.item, entry.expiry + (slidingWindowSeconds * 1000));
      return entry.item;
    }
    return null;
  }

  void addCookieValue(String name, String value,
      {String domain = '.pixiv.net'}) {
    cookieJar.saveFromResponse(Uri.parse('https://www.pixiv.net'),
        [Cookie(name, value)..domain = domain]);
  }

  // -----------
  // High-level Pixiv API methods (placeholders for the most common calls).
  // -----------

  Future<(PixivArtist, String)> getMemberPage(int memberId,
      {int page = 1, int? referenceImageId, bool tagsOnly = false}) async {
    final cacheKey = 'member_$memberId';
    PixivArtist? cached = _getCache(cacheKey) as PixivArtist?;
    if (cached != null) return (cached, '');

    final url = 'https://www.pixiv.net/ajax/user/$memberId';
    final body = await getContent(url);
    // /ajax/user returns: { error, body: { ... } }
    final data = jsonDecode(body) as Map<String, dynamic>;
    if (data['error'] == true) {
      throw PixivException(
        '${data['message']}',
        errorCode: PixivException.OTHER_MEMBER_ERROR,
        htmlPage: body,
      );
    }
    final artist = PixivArtist(artistId: memberId);
    artist.parseInfo({'body': null, ...data}, false);

    // Fetch the all-illust list to populate imageList.
    final allUrl = 'https://www.pixiv.net/ajax/user/$memberId/profile/all';
    final allBody = await getContent(allUrl);
    final allData = jsonDecode(allBody) as Map<String, dynamic>;
    if (allData['body'] is Map) {
      final inner = allData['body'] as Map<String, dynamic>;
      artist.offset = 0;
      artist.limit = 60;
      artist.parseImages(inner);
      artist.parseMangaList(inner);
      artist.parseNovelList(inner);
    }

    _putCache(cacheKey, artist);
    return (artist, body);
  }

  Future<(PixivImage, String)> getImagePage(int imageId,
      {PixivArtist? parent,
      bool fromBookmark = false,
      int bookmarkCount = -1,
      int imageResponseCount = -1,
      Duration? tzInfo,
      String? dateFormat,
      bool writeRawJSON = false,
      bool stripHTMLTagsFromCaption = false}) async {
    final url = 'https://www.pixiv.net/ajax/illust/$imageId';
    final body = await getContent(url);
    final image = PixivImage(
      iid: imageId,
      page: body,
      parent: parent,
      fromBookmark: fromBookmark,
      bookmark_count: bookmarkCount,
      image_response_count: imageResponseCount,
      tzInfo: tzInfo,
      dateFormat: dateFormat,
      writeRawJSON: writeRawJSON,
      stripHTMLTagsFromCaption: stripHTMLTagsFromCaption,
    );
    return (image, body);
  }

  Future<PixivTags> getSearchTagPage(String tags,
      {int currentPage = 1,
      String wildCard = '%20',
      String typeMode = 'all',
      String sortOrder = 'date_d',
      String? startDate,
      String? endDate,
      int? bookmarkCount}) async {
    final urlTags = Uri.encodeComponent(tags);
    final url = 'https://www.pixiv.net/ajax/search/artworks/$urlTags'
        '?word=$urlTags&order=$sortOrder&mode=all&p=$currentPage&type=$typeMode';
    final body = await getContent(url);
    final result = PixivTags();
    result.parseTags(body, query: tags, currPage: currentPage);
    return result;
  }

  Future<PixivRanking> getPixivRanking(
      String mode, int currentPage, String date, String content,
      [List<String>? filters]) async {
    var url =
        'https://www.pixiv.net/ranking.php?mode=$mode&p=$currentPage&format=json';
    if (date.isNotEmpty) url += '&date=$date';
    if (content.isNotEmpty) url += '&content=$content';
    final body = await getContent(url);
    return PixivRanking(body, filters);
  }

  Future<PixivNewIllust> getNewIllust(int lastId,
      {String typeMode = 'illust', bool r18 = false}) async {
    final url =
        'https://www.pixiv.net/ajax/illust/new?lastId=$lastId&limit=20&type=$typeMode&r18=${r18 ? 'true' : 'false'}';
    final body = await getContent(url);
    return PixivNewIllust(body, typeMode);
  }

  Future<PixivNewIllustBookmark> getNewIllustBookmark({int page = 1}) async {
    final url =
        'https://www.pixiv.net/ajax/follow_latest/illust?p=$page&mode=all';
    final body = await getContent(url);
    return PixivNewIllustBookmark(body);
  }

  Future<PixivNovel> getNovelPage(int novelId,
      {Duration? tzInfo, String? dateFormat}) async {
    final url = 'https://www.pixiv.net/ajax/novel/$novelId';
    final body = await getContent(url);
    return PixivNovel(novelId, body, tzInfo: tzInfo, dateFormat: dateFormat);
  }

  Future<NovelSeries> getNovelSeries(int seriesId) async {
    final url = 'https://www.pixiv.net/ajax/novel/series/$seriesId';
    final body = await getContent(url);
    return NovelSeries(seriesId, body);
  }

  Future<FanboxArtist> getFanboxArtist(int artistId,
      {String? creatorId}) async {
    final url = creatorId != null
        ? 'https://api.fanbox.cc/creator.get?creatorId=$creatorId'
        : 'https://api.fanbox.cc/legacy/manage/profile/get';
    final body = await getContent(url, headers: {
      'Origin': 'https://www.fanbox.cc',
      'Referer': 'https://www.fanbox.cc/',
    });
    return FanboxArtist(artistId: artistId, page: body);
  }

  Future<List<FanboxPost>> getFanboxPosts(FanboxArtist artist) async {
    final url =
        'https://api.fanbox.cc/post.listCreator?creatorId=${artist.creatorId}&limit=50';
    final body = await getContent(url, headers: {
      'Origin': 'https://www.fanbox.cc',
      'Referer': 'https://www.fanbox.cc/',
    });
    artist.parsePosts(body);
    return artist.posts;
  }

  Future<SketchArtist> getSketchArtist(String unique) async {
    final url = 'https://sketch.pixiv.net/api/users/@$unique.json';
    final body = await getContent(url);
    final data = jsonDecode(body) as Map<String, dynamic>;
    return SketchArtist(
      (data['data']['id'] as num).toInt(),
      body,
    );
  }

  Future<List<SketchPost>> getSketchPosts(SketchArtist artist) async {
    final url =
        'https://sketch.pixiv.net/api/walls/users/@${artist.artistToken}/posts.json';
    final body = await getContent(url);
    artist.parsePosts(body);
    return artist.posts;
  }

  /// Download a file at [url] to [destination].
  /// Returns the number of bytes downloaded.
  Future<int> downloadFile(String url, String destination,
      {Map<String, String>? headers}) async {
    final mergedHeaders = await _buildHeaders(url, headers);
    final request = http.Request('GET', Uri.parse(url));
    request.headers.addAll(mergedHeaders);
    final response = await _client.send(request);
    if (response.statusCode >= 400) {
      throw PixivException('HTTP ${response.statusCode} downloading $url',
          errorCode: PixivException.DOWNLOAD_FAILED_NETWORK);
    }
    final file = await File(destination).create(recursive: true);
    final sink = file.openWrite();
    var bytes = 0;
    await for (final chunk in response.stream) {
      sink.add(chunk);
      bytes += chunk.length;
    }
    await sink.close();
    return bytes;
  }
}

class _CacheEntry {
  final dynamic item;
  final int expiry;
  _CacheEntry(this.item, this.expiry);
}

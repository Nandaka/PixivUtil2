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

  Future<bool> loginUsingCookie([String? loginCookie]) async {
    final cookie = (loginCookie == null || loginCookie.isEmpty)
        ? config.cookie
        : loginCookie;
    if (cookie.isEmpty) return false;

    pixiv_helper.printAndLog('info', 'Trying to log in with saved cookie');
    final uri = Uri.parse('https://www.pixiv.net');
    final request = http.Request('GET', uri)..followRedirects = false;
    request.headers.addAll(await _buildHeaders(uri.toString(), {
      'Accept':
          'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    }));

    final streamed = await _client.send(request).timeout(
          Duration(seconds: config.timeout),
        );
    final response = await http.Response.fromStream(streamed);
    _saveCookies(uri.toString(), response);

    final xUserId = response.headers['x-userid'] ??
        response.headers['x-userId'] ??
        response.headers['X-UserId'];
    if (xUserId != null && xUserId.isNotEmpty) {
      _myId = int.tryParse(xUserId) ?? _myId;
      pixiv_helper.printAndLog(
          'info', 'Login recognized by server (x-userid=$xUserId).');
      return true;
    }

    final body = response.body;
    pixiv_helper.printAndLog('info', 'Logging in, return url: $uri');
    final result = body.contains('logout.php') ||
        body.contains('pixiv.user.loggedIn = true') ||
        body.contains("_gaq.push(['_setCustomVar', 1, 'login', 'yes'") ||
        body.contains("var dataLayer = [{ login: 'yes',");

    if (result) {
      _parseLoginStatus(body);
      pixiv_helper.printAndLog('info', 'Login successful.');
    } else {
      pixiv_helper.printAndLog('info', 'Cookie already expired/invalid.');
    }
    return result;
  }

  void _parseLoginStatus(String body) {
    final userIdPatterns = [
      RegExp(r'''user_id['"]?\s*:\s*['"]?(\d+)'''),
      RegExp(r'''userId['"]?\s*:\s*['"]?(\d+)'''),
      RegExp(r'''USER_ID['"]?\s*:\s*['"]?(\d+)'''),
    ];
    for (final pattern in userIdPatterns) {
      final match = pattern.firstMatch(body);
      if (match != null) {
        _myId = int.tryParse(match.group(1)!) ?? _myId;
        break;
      }
    }
    _isPremium = body.contains("premium: 'yes'") ||
        body.contains('"premium":true') ||
        body.contains('"isPremium":true');
  }

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
    } else if (uri.host == 'fanbox.cc' || uri.host.endsWith('.fanbox.cc')) {
      cookieValues.addAll(parseCookieHeader(config.cookieFanbox));
      cookieValues.addAll(parseCookieHeader(config.cookieFanboxTemp));
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
    if (!raw.contains('=')) return {'PHPSESSID': raw};

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
      {int page = 1,
      int? referenceImageId,
      bool tagsOnly = false,
      String? tags}) async {
    final cacheKey = tags == null || tags.isEmpty
        ? 'member_$memberId'
        : 'member_${memberId}_tag_${tags}_$page';
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

    // Fetch the all-illust list or the member/tag result to populate imageList.
    final offset = (page - 1) * 60;
    const limit = 60;
    final allUrl = tags == null || tags.isEmpty
        ? 'https://www.pixiv.net/ajax/user/$memberId/profile/all'
        : 'https://www.pixiv.net/ajax/user/$memberId/illustmanga/tag'
            '?tag=${Uri.encodeQueryComponent(tags)}&offset=$offset&limit=$limit';
    final allBody = await getContent(allUrl);
    final allData = jsonDecode(allBody) as Map<String, dynamic>;
    if (allData['body'] is Map) {
      final inner = allData['body'] as Map<String, dynamic>;
      artist.offset = offset;
      artist.limit = limit;
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
      int mangaSeriesOrder = -1,
      PixivMangaSeries? mangaSeriesParent,
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
      mangaSeriesOrder: mangaSeriesOrder,
      mangaSeriesParent: mangaSeriesParent,
      writeRawJSON: writeRawJSON,
      stripHTMLTagsFromCaption: stripHTMLTagsFromCaption,
    );
    return (image, body);
  }

  Future<(PixivImage, String)> getUnlistedImagePage(String unlistedId,
      {PixivArtist? parent,
      bool fromBookmark = false,
      int bookmarkCount = -1,
      int imageResponseCount = -1,
      Duration? tzInfo,
      String? dateFormat,
      bool writeRawJSON = false,
      bool stripHTMLTagsFromCaption = false}) async {
    final pageUrl = 'https://www.pixiv.net/artworks/unlisted/$unlistedId';
    final page = await getContent(pageUrl, headers: {
      'Referer': 'https://www.pixiv.net/',
    });
    var resolvedId = int.tryParse(unlistedId);
    resolvedId ??= _extractIllustId(page);
    if (resolvedId == null) {
      throw PixivException(
        'Unable to resolve unlisted artwork id from $unlistedId',
        errorCode: PixivException.OTHER_ERROR,
        htmlPage: page,
      );
    }
    return getImagePage(
      resolvedId,
      parent: parent,
      fromBookmark: fromBookmark,
      bookmarkCount: bookmarkCount,
      imageResponseCount: imageResponseCount,
      tzInfo: tzInfo,
      dateFormat: dateFormat,
      writeRawJSON: writeRawJSON,
      stripHTMLTagsFromCaption: stripHTMLTagsFromCaption,
    );
  }

  int? _extractIllustId(String page) {
    final patterns = [
      RegExp(r'"illustId"\s*:\s*"?(\d+)"?'),
      RegExp(r'"illust_id"\s*:\s*"?(\d+)"?'),
      RegExp(r'/artworks/(\d+)'),
      RegExp(r'illust_id=(\d+)'),
    ];
    for (final pattern in patterns) {
      final match = pattern.firstMatch(page);
      if (match != null) return int.tryParse(match.group(1)!);
    }
    return null;
  }

  Future<PixivTags> getSearchTagPage(String tags,
      {int currentPage = 1,
      String wildCard = '%20',
      bool wildCardSearch = true,
      bool titleCaption = false,
      String typeMode = 'all',
      String sortOrder = 'date_d',
      String? startDate,
      String? endDate,
      int? memberId,
      int? bookmarkCount}) async {
    if (memberId != null) {
      final (artist, _) =
          await getMemberPage(memberId, page: currentPage, tags: tags);
      final result = PixivTags();
      result.parseMemberTags(artist, memberId, query: tags);
      return result;
    }

    final query = <String, String>{
      'word': tags,
      'order': sortOrder,
      'mode': 'all',
      'p': '$currentPage',
      's_mode':
          titleCaption ? 's_tc' : (wildCardSearch ? 's_tag' : 's_tag_full'),
      'type': _normalizeSearchType(typeMode),
    };
    if (startDate != null && startDate.isNotEmpty) query['scd'] = startDate;
    if (endDate != null && endDate.isNotEmpty) query['ecd'] = endDate;
    if (bookmarkCount != null && bookmarkCount > 0 && _isPremium) {
      query['blt'] = '$bookmarkCount';
    }
    if (_locale.isNotEmpty) query['lang'] = _locale.replaceFirst('/', '');
    final url = Uri.https(
      'www.pixiv.net',
      '/ajax/search/artworks/$tags',
      query,
    ).toString();
    final body = await getContent(url);
    final result = PixivTags();
    result.parseTags(body, query: tags, currPage: currentPage);
    return result;
  }

  String _normalizeSearchType(String typeMode) {
    if (typeMode == 'i') return 'illust_and_ugoira';
    if (typeMode == 'm') return 'manga';
    return typeMode == 'all' ? 'all' : typeMode;
  }

  Future<PixivTag> getTagInfo(String tag, {String? lang}) async {
    if (tag.trim().isEmpty) {
      throw PixivException('Tag is empty.',
          errorCode: PixivException.OTHER_ERROR);
    }
    final query = <String, String>{};
    final resolvedLang = lang ?? _locale.replaceFirst('/', '');
    if (resolvedLang.isNotEmpty) query['lang'] = resolvedLang;
    final url = Uri.https(
      'www.pixiv.net',
      '/ajax/search/tags/${tag.trim()}',
      query.isEmpty ? null : query,
    ).toString();
    final cached = _getCache(url) as PixivTag?;
    if (cached != null) return cached;
    final body = await getContent(url);
    final tagInfo = PixivTag(jsonDecode(body) as Map<String, dynamic>);
    _putCache(url, tagInfo);
    return tagInfo;
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

  Future<String> getMangaSeriesJson(int mangaSeriesId, int currentPage) async {
    pixiv_helper.printAndLog(
        'info', 'Getting Manga Series: $mangaSeriesId from page: $currentPage');
    final query = <String, String>{'p': '$currentPage'};
    if (_locale.isNotEmpty) query['lang'] = _locale.replaceFirst('/', '');
    final url = Uri.https(
      'www.pixiv.net',
      '/ajax/series/$mangaSeriesId',
      query,
    ).toString();
    return getContent(url);
  }

  Future<PixivMangaSeries> getMangaSeries(
      int mangaSeriesId, int currentPage) async {
    final body = await getMangaSeriesJson(mangaSeriesId, currentPage);
    final series = PixivMangaSeries(
      mangaSeriesId: mangaSeriesId,
      currentPage: currentPage,
      payload: body,
    );
    if (series.memberId > 0) {
      pixiv_helper.printAndLog(
          'info', ' - Fetching artist details ${series.memberId}');
      final (artist, _) = await getMemberPage(series.memberId);
      series.artist = artist;
    }
    return series;
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

  Future<FanboxPost> getFanboxPostById(int postId) async {
    final body = await getContent(
      'https://api.fanbox.cc/post.info?postId=$postId',
      headers: {
        'Accept': 'application/json, text/plain, */*',
        'Origin': 'https://www.fanbox.cc',
        'Referer': 'https://www.fanbox.cc/posts/$postId',
      },
    );
    final js = jsonDecode(body) as Map<String, dynamic>;
    if (js['error'] == true) {
      throw PixivException('${js['message']}',
          errorCode: PixivException.OTHER_ERROR, htmlPage: body);
    }
    final postBody = js['body'] as Map<String, dynamic>;
    final creatorId = '${postBody['creatorId'] ?? ''}';
    final artist = await getFanboxArtist(0, creatorId: creatorId);
    return FanboxPost(postId, artist, postBody);
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

  Future<SketchPost> getSketchPost(int postId, {SketchArtist? artist}) async {
    final url = 'https://sketch.pixiv.net/api/replies/$postId.json';
    final body = await getContent(url, headers: {
      'Referer': 'https://sketch.pixiv.net/items/$postId',
      'X-Requested-With': 'https://sketch.pixiv.net/items/$postId',
    });
    return SketchPost(postId, artist, body);
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

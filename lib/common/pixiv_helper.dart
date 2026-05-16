/// Helper utilities ported from PixivHelper.py.
library;

import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math';

import 'package:crypto/crypto.dart' as crypto;
import 'package:html/parser.dart' as html_parser;
import 'package:intl/intl.dart';
import 'package:logging/logging.dart';
import 'package:path/path.dart' as p;

import 'pixiv_constant.dart' as pixiv_constant;
import 'pixiv_exception.dart';

/// Lazily initialized application-wide logger.
Logger? _logger;
dynamic _config;

/// ANSI color escape regex.
final RegExp _ansiColor = RegExp(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])');

/// Bad-character regex (platform-aware), matches PixivHelper.__badchars__.
final RegExp _badchars =
    Platform.isWindows ? RegExp(r'[\?:<>\|\*"]') : RegExp(r'^$');

/// Custom sanitizer dictionary.
final Map<String, Map<String, dynamic>> _customSanitizerDic = {};

void setConfig(dynamic cfg) {
  _config = cfg;
}

dynamic get config => _config;

/// Return the global logger (set up on first use).
Logger getLogger({Level? level, bool reload = false}) {
  if (reload) _logger = null;
  if (_logger == null) {
    Logger.root.level = level ?? Level.INFO;
    _logger = Logger('PixivUtil${pixiv_constant.PIXIVUTIL_VERSION}');
    Logger.root.onRecord.listen((record) {
      stderr.writeln(
          '${record.time} - ${record.loggerName} - ${record.level.name} - ${record.message}');
    });
  }
  return _logger!;
}

void setLogLevel(Level level) {
  getLogger().info('Setting log level to: $level');
  Logger.root.level = level;
}

/// Sanitize a filename. Replace reserved characters with underscore.
String sanitizeFilename(String name, [String? rootDir]) {
  if (rootDir != null) {
    rootDir = p.absolute(rootDir);
  }

  // Unescape HTML entities (&amp;, &lt;, &gt;)
  name = _htmlUnescape(name);

  name = name.replaceAll(_badchars, '_');

  for (final entry in _customSanitizerDic.entries) {
    final regex = entry.value['regex'] as RegExp;
    final replace = entry.value['replace'] as String;
    name = name.replaceAll(regex, replace);
  }

  // Remove unicode control chars
  name = name.runes
      .where((r) => !((r >= 0 && r <= 0x1F) || (r >= 0x7F && r <= 0x9F)))
      .map((r) => String.fromCharCode(r))
      .join();

  final stripped = <String>[];
  for (final item in name.split(p.separator)) {
    var t = item;
    if (_isReservedName(t)) t = '_$t';
    stripped.add(t.replaceAll(RegExp(r'^[\s\.\t\r\n]+|[\s\.\t\r\n]+$'), ''));
  }
  name = stripped.join(p.separator);

  if (Platform.isWindows) {
    String fullName;
    if (rootDir != null) {
      final tname = name.startsWith(p.separator) ? name.substring(1) : name;
      fullName = p.absolute(p.join(rootDir, tname));
    } else {
      fullName = p.absolute(name);
    }
    if (fullName.length > 255) {
      final ext = p.extension(name);
      var stem = p.withoutExtension(name);
      if (stem.length > 255 - ext.length) {
        stem = stem.substring(0, 255 - ext.length);
      }
      name = stem + ext;
      if (name == ext) {
        throw FileSystemException('Path name too long', fullName);
      }
    }
  } else {
    while (utf8.encode(name).length > 249) {
      final ext = p.extension(name);
      var stem = p.withoutExtension(name);
      stem = stem.substring(0, stem.length - 1);
      name = stem + ext;
    }
    name = name.replaceAll(r'\\', '/');
  }

  if (rootDir != null) {
    final tname = name.startsWith(p.separator) ? name.substring(1) : name;
    name = p.absolute(p.join(rootDir, tname));
  }

  getLogger().fine('Sanitized Filename: $name');
  return name;
}

bool _isReservedName(String name) {
  if (!Platform.isWindows) return false;
  final reserved = {
    'CON',
    'PRN',
    'AUX',
    'NUL',
    'COM1',
    'COM2',
    'COM3',
    'COM4',
    'COM5',
    'COM6',
    'COM7',
    'COM8',
    'COM9',
    'LPT1',
    'LPT2',
    'LPT3',
    'LPT4',
    'LPT5',
    'LPT6',
    'LPT7',
    'LPT8',
    'LPT9',
  };
  final stem = p.withoutExtension(name).toUpperCase();
  return reserved.contains(stem);
}

String _htmlUnescape(String s) {
  return s
      .replaceAll('&amp;', '&')
      .replaceAll('&lt;', '<')
      .replaceAll('&gt;', '>')
      .replaceAll('&#039;', "'")
      .replaceAll('&quot;', '"');
}

/// Replace path separators '/' and '\' with the given replacement.
String replacePathSeparator(String s, [String replacement = '_']) {
  return s.replaceAll('/', replacement).replaceAll(r'\', replacement);
}

/// Build a filename from a format string and image/artist info.
/// Mirrors the make_filename helper in PixivHelper.py.
String makeFilename(
  String nameFormat,
  dynamic imageInfo, {
  dynamic artistInfo,
  String tagsSeparator = ' ',
  int tagsLimit = -1,
  String fileUrl = '',
  bool appendExtension = true,
  bool bookmark = false,
  String searchTags = '',
  bool useTranslatedTag = false,
  String tagTranslationLocale = 'en',
}) {
  artistInfo ??= imageInfo.artist;

  final basename = p.basename(fileUrl);
  String imageFile = basename;
  String imageExtension = '';
  if (basename.contains('.')) {
    final parts = basename.split('.');
    imageFile = parts[0];
    imageExtension = parts[1].split('?')[0];
  }

  // Issue #940
  if (nameFormat.contains('%force_extension')) {
    final m = RegExp(r'(%force_extension\{.*\}%)').firstMatch(nameFormat);
    if (m != null) {
      final inside = RegExp(r'\{(.*)\}').firstMatch(m.group(0)!);
      if (inside != null) {
        imageExtension = inside.group(1)!;
        nameFormat = nameFormat.replaceFirst(m.group(0)!, '');
      }
    }
  }

  // Artist related
  nameFormat = nameFormat.replaceAll(
      '%artist%', replacePathSeparator(_safeStr(artistInfo.artistName)));
  nameFormat =
      nameFormat.replaceAll('%member_id%', '${artistInfo.artistId ?? 0}');
  nameFormat =
      nameFormat.replaceAll('%member_token%', _safeStr(artistInfo.artistToken));

  // Image related
  nameFormat = nameFormat.replaceAll(
      '%title%', replacePathSeparator(_safeStr(imageInfo.imageTitle)));
  nameFormat = nameFormat.replaceAll('%image_id%', '${imageInfo.imageId ?? 0}');
  nameFormat =
      nameFormat.replaceAll('%works_date%', _safeStr(imageInfo.worksDate));
  final wd = _safeStr(imageInfo.worksDate);
  nameFormat = nameFormat.replaceAll(
      '%works_date_only%', wd.contains(' ') ? wd.split(' ').first : wd);
  nameFormat = nameFormat.replaceAll('%image_ext%', imageExtension);

  // %works_date_fmt{...}%
  if (nameFormat.contains('%works_date_fmt')) {
    final m = RegExp(r'(%works_date_fmt\{(.*?)\}%)').firstMatch(nameFormat);
    if (m != null) {
      final fmt = _convertPyDateFormat(m.group(2)!);
      final dt = (imageInfo.worksDateDateTime as DateTime?) ?? DateTime.now();
      nameFormat =
          nameFormat.replaceFirst(m.group(0)!, DateFormat(fmt).format(dt));
    }
  }

  nameFormat =
      nameFormat.replaceAll('%works_res%', _safeStr(imageInfo.worksResolution));
  nameFormat = nameFormat.replaceAll('%urlFilename%', imageFile);
  nameFormat =
      nameFormat.replaceAll('%searchTags%', replacePathSeparator(searchTags));

  // date today
  nameFormat = nameFormat.replaceAll(
      '%date%', DateFormat('yyyyMMdd').format(DateTime.now()));

  if (nameFormat.contains('%date_fmt')) {
    final m = RegExp(r'(%date_fmt\{(.*?)\}%)').firstMatch(nameFormat);
    if (m != null) {
      final fmt = _convertPyDateFormat(m.group(2)!);
      nameFormat = nameFormat.replaceFirst(
          m.group(0)!, DateFormat(fmt).format(DateTime.now()));
    }
  }

  // Manga page index/number
  String pageIndex = '';
  String pageNumber = '';
  String pageBig = '';
  if (imageInfo.imageMode == 'manga') {
    final m = RegExp(r'_p(\d+)').firstMatch(fileUrl);
    if (m != null) {
      pageIndex = m.group(1)!;
      final padding = max(1, '${imageInfo.imageCount ?? 0}'.length);
      pageNumber = '${int.parse(pageIndex) + 1}'.padLeft(padding, '0');
    }
    if (fileUrl.contains('_big') || !fileUrl.contains('_m')) {
      pageBig = 'big';
    }
  }
  nameFormat = nameFormat.replaceAll('%page_big%', pageBig);
  nameFormat = nameFormat.replaceAll('%page_index%', pageIndex);
  nameFormat = nameFormat.replaceAll('%page_number%', pageNumber);

  // Manga Series
  final seriesNav = _tryGet(imageInfo, 'seriesNavData');
  if (seriesNav is Map) {
    nameFormat =
        nameFormat.replaceAll('%manga_series_order%', '${seriesNav['order']}');
    nameFormat =
        nameFormat.replaceAll('%manga_series_id%', '${seriesNav['seriesId']}');
    nameFormat =
        nameFormat.replaceAll('%manga_series_title%', '${seriesNav['title']}');
  } else {
    nameFormat = nameFormat.replaceAll('%manga_series_order%', '');
    nameFormat = nameFormat.replaceAll('%manga_series_id%', '');
    nameFormat = nameFormat.replaceAll('%manga_series_title%', '');
  }

  if (tagsSeparator == '%space%') tagsSeparator = ' ';
  if (tagsSeparator == '%ideo_space%') tagsSeparator = '　';

  List<String> imageTags = List<String>.from(imageInfo.imageTags ?? const []);
  if (tagsLimit != -1) {
    final lim = min(tagsLimit, imageTags.length);
    imageTags = imageTags.sublist(0, lim);
  }
  if (useTranslatedTag) {
    final tagsList = imageInfo.tags as List? ?? const [];
    for (var i = 0; i < imageTags.length; i++) {
      for (final t in tagsList) {
        if (t.tag == imageTags[i]) {
          imageTags[i] = t.getTranslation(tagTranslationLocale) as String;
          break;
        }
      }
    }
  }
  final tags = imageTags.join(tagsSeparator);

  if (_tryGet(imageInfo, 'ai_type') == 2) {
    nameFormat = nameFormat.replaceAll('%AI%', 'AI');
  } else {
    nameFormat = nameFormat.replaceAll('%AI%', '');
  }

  String r18Dir = '';
  if (imageTags.contains('R-18G')) {
    r18Dir = 'R-18G';
  } else if (imageTags.contains('R-18')) {
    r18Dir = 'R-18';
  }
  nameFormat = nameFormat.replaceAll('%R-18%', r18Dir);
  nameFormat = nameFormat.replaceAll('%tags%', replacePathSeparator(tags));
  nameFormat = nameFormat.replaceAll('&#039;', "'");

  if (bookmark) {
    nameFormat = nameFormat.replaceAll('%bookmark%', 'Bookmarks');
    nameFormat = nameFormat.replaceAll(
        '%original_member_id%', '${imageInfo.originalArtist?.artistId ?? 0}');
    nameFormat = nameFormat.replaceAll('%original_member_token%',
        _safeStr(imageInfo.originalArtist?.artistToken));
    nameFormat = nameFormat.replaceAll('%original_artist%',
        replacePathSeparator(_safeStr(imageInfo.originalArtist?.artistName)));
  } else {
    nameFormat = nameFormat.replaceAll('%bookmark%', '');
    nameFormat = nameFormat.replaceAll(
        '%original_member_id%', '${artistInfo.artistId ?? 0}');
    nameFormat = nameFormat.replaceAll(
        '%original_member_token%', _safeStr(artistInfo.artistToken));
    nameFormat = nameFormat.replaceAll('%original_artist%',
        replacePathSeparator(_safeStr(artistInfo.artistName)));
  }

  if ((imageInfo.bookmark_count ?? 0) > 0) {
    nameFormat = nameFormat.replaceAll(
        '%bookmark_count%', '${imageInfo.bookmark_count}');
    if (nameFormat.contains('%bookmarks_group%')) {
      nameFormat = nameFormat.replaceAll(
          '%bookmarks_group%', calculateGroup(imageInfo.bookmark_count as int));
    }
  } else {
    nameFormat = nameFormat.replaceAll('%bookmark_count%', '');
    nameFormat = nameFormat.replaceAll('%bookmarks_group%', '');
  }

  if ((imageInfo.image_response_count ?? 0) > 0) {
    nameFormat = nameFormat.replaceAll(
        '%image_response_count%', '${imageInfo.image_response_count}');
  } else {
    nameFormat = nameFormat.replaceAll('%image_response_count%', '');
  }

  while (nameFormat.contains('  ')) {
    nameFormat = nameFormat.replaceAll('  ', ' ');
  }
  while (nameFormat.contains('//') || nameFormat.contains(r'\\')) {
    nameFormat = nameFormat.replaceAll('//', '/').replaceAll(r'\\', r'\');
  }

  if (appendExtension) {
    nameFormat = '${nameFormat.trim()}.$imageExtension';
  }

  if (_config != null &&
      (_config.customCleanUpRe as String?) != null &&
      (_config.customCleanUpRe as String).isNotEmpty) {
    nameFormat =
        nameFormat.replaceAll(RegExp(_config.customCleanUpRe as String), '');
  }

  return nameFormat.trim();
}

dynamic _tryGet(dynamic obj, String name) {
  try {
    return (obj as dynamic).noSuchMethod(
      Invocation.getter(Symbol(name)),
    );
  } catch (_) {
    try {
      switch (name) {
        case 'seriesNavData':
          return obj.seriesNavData;
        case 'ai_type':
          return obj.ai_type;
      }
    } catch (_) {
      return null;
    }
    return null;
  }
}

String _safeStr(dynamic v) => v == null ? '' : '$v';

/// Compute hash of file contents using md5/sha1/sha256.
Future<String> getHash(String path, {String method = 'md5'}) async {
  final bytes = await File(path).readAsBytes();
  switch (method) {
    case 'md5':
      return crypto.md5.convert(bytes).toString();
    case 'sha1':
      return crypto.sha1.convert(bytes).toString();
    case 'sha256':
      return crypto.sha256.convert(bytes).toString();
    default:
      throw PixivException('Invalid hash function $method');
  }
}

/// Compute the bookmark group (per pixiv 'users入り' rules).
String calculateGroup(int count) {
  if (count >= 100 && count < 250) return '100';
  if (count >= 250 && count < 500) return '250';
  if (count >= 500 && count < 1000) return '500';
  if (count >= 1000 && count < 5000) return '1000';
  if (count >= 5000 && count < 10000) return '5000';
  if (count >= 10000) return '10000';
  return '';
}

/// Convert a Python-style strftime/strptime format to an `intl` DateFormat pattern.
String _convertPyDateFormat(String fmt) {
  return fmt
      .replaceAll('%Y', 'yyyy')
      .replaceAll('%m', 'MM')
      .replaceAll('%d', 'dd')
      .replaceAll('%H', 'HH')
      .replaceAll('%M', 'mm')
      .replaceAll('%S', 'ss');
}

/// Print a message handling encoding errors gracefully.
void safePrint(String msg, {bool newline = true, String? end}) {
  for (final token in msg.split(' ')) {
    try {
      stdout.write('$token ');
    } catch (_) {
      stdout.write('${'?' * token.length} ');
    }
  }
  if (end != null) {
    stdout.write(end);
  } else if (newline) {
    stdout.writeln();
  }
}

/// Set the console title.
void setConsoleTitle(String title) {
  try {
    if (Platform.isWindows) {
      Process.runSync('cmd', ['/c', 'title', title]);
    } else {
      stdout.write('\x1B]0;$title\x07');
    }
  } catch (_) {
    printAndLog('error', 'Cannot set console title to $title');
  }
}

void clearScreen() {
  if (_config != null && (_config.disableScreenClear as bool? ?? false)) {
    return;
  }
  if (Platform.isWindows) {
    Process.runSync('cmd', ['/c', 'cls']);
  } else {
    Process.runSync('clear', []);
  }
}

/// Open a UTF-8 text file for reading; handles BOMs.
Future<List<String>> openTextFileLines(String filename) async {
  final raw = await File(filename).readAsBytes();
  // Strip BOMs
  List<int> data = raw;
  if (data.length >= 3 &&
      data[0] == 0xEF &&
      data[1] == 0xBB &&
      data[2] == 0xBF) {
    data = data.sublist(3);
  }
  final text = utf8.decode(data, allowMalformed: true);
  return const LineSplitter().convert(text);
}

bool weAreFrozen() => false;

/// Path to the program directory.
String modulePath() => p.absolute(Directory.current.path);

String speedInStr(num totalSize, num totalTime) {
  if (totalTime > 0) {
    var speed = totalSize / totalTime;
    if (speed < 1024) return '${speed.toStringAsFixed(0)} B/s';
    speed /= 1024;
    if (speed < 1024) return '${speed.toStringAsFixed(2)} KiB/s';
    speed /= 1024;
    if (speed < 1024) return '${speed.toStringAsFixed(2)} MiB/s';
    speed /= 1024;
    return '${speed.toStringAsFixed(2)} GiB/s';
  }
  return ' infinity B/s';
}

String sizeInStr(num totalSize) {
  var ts = totalSize.toDouble();
  if (ts < 1024) return '${ts.toStringAsFixed(0)} B';
  ts /= 1024;
  if (ts < 1024) return '${ts.toStringAsFixed(2)} KiB';
  ts /= 1024;
  if (ts < 1024) return '${ts.toStringAsFixed(2)} MiB';
  ts /= 1024;
  return '${ts.toStringAsFixed(2)} GiB';
}

/// Dump HTML for debugging.
Future<void> dumpHtml(String filename, String htmlText,
    {bool exitOnError = true}) async {
  try {
    if (_config != null && !(_config.enableDump as bool)) return;
    final skipFilter = _config?.skipDumpFilter as String? ?? '';
    if (skipFilter.isNotEmpty && RegExp(skipFilter).hasMatch(filename)) {
      return;
    }
    await File(filename).writeAsString(htmlText);
  } catch (e) {
    if (exitOnError) rethrow;
  }
}

/// Print and log a message.
void printAndLog(String? level, String msg,
    {bool newline = true, String? end}) {
  final cleaned = msg.replaceAll(_ansiColor, '');
  final lvl = level?.toLowerCase();
  if (lvl != null) {
    switch (lvl) {
      case 'debug':
        getLogger().fine(cleaned);
        break;
      case 'info':
        getLogger().info(cleaned);
        break;
      case 'warn':
      case 'warning':
        getLogger().warning(cleaned);
        break;
      case 'error':
        getLogger().severe(cleaned);
        break;
      case 'critical':
        getLogger().shout(cleaned);
        break;
    }
  }
  safePrint(msg, newline: newline, end: end);
}

/// Wait between downloads. Used after each download.
Future<void> wait([int? result, dynamic config]) async {
  config ??= _config;
  if (config == null) return;
  if (result == pixiv_constant.PIXIVUTIL_SKIP_DUPLICATE_NO_WAIT) return;

  final delay = (config.downloadDelay as int?) ?? 5;
  if (delay > 0) {
    await Future<void>.delayed(Duration(seconds: delay));
  }
}

/// Sleep for the given number of seconds.
Future<void> printDelay(int seconds) async {
  await Future<void>.delayed(Duration(seconds: seconds));
}

/// Make subdirectories for the given filename.
Future<void> makeSubdirs(String filename) async {
  final dir = p.dirname(filename);
  if (dir.isNotEmpty) {
    await Directory(dir).create(recursive: true);
  }
}

/// Parse custom sanitizer: text of pairs `bad=replace,bad2=replace2`.
String parseCustomSanitizer(String value) {
  _customSanitizerDic.clear();
  if (value.isEmpty) return value;
  for (final pair in value.split(',')) {
    final parts = pair.split('=');
    if (parts.length == 2) {
      _customSanitizerDic[parts[0]] = {
        'regex': RegExp(RegExp.escape(parts[0])),
        'replace': parts[1],
      };
    }
  }
  return value;
}

/// Parse a custom-cleanup regex from config.
String parseCustomCleanUpRe(String value) => value;

/// Check if the (HTML) [page] contains any of the [strings].
bool haveStrings(dynamic page, List<String> strings) {
  final html = page is String ? page : page.toString();
  for (final s in strings) {
    if (RegExp(s).hasMatch(html)) return true;
  }
  return false;
}

/// Parse HTML page text into a Document.
dynamic parsePageHtml(String text) => html_parser.parse(text);

/// Stub for the "dummy notifier" callback used by handlers.
void dummyNotifier({String? title, String? message, dynamic type}) {}

/// Get content from a URL using the GLOBAL browser.
/// (Not implemented; placeholder for caller.)
Future<dynamic> getContent(String url) async {
  throw UnimplementedError('Use PixivBrowser.getContent instead');
}

/// Calculate the IPMS (image processed milliseconds) timing string.
String formatDuration(Duration d) {
  final h = d.inHours.toString().padLeft(2, '0');
  final m = (d.inMinutes % 60).toString().padLeft(2, '0');
  final s = (d.inSeconds % 60).toString().padLeft(2, '0');
  return '$h:$m:$s';
}

/// Generates a random string of [length] characters.
String randomString(int length) {
  const chars =
      'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  final r = Random();
  return List.generate(length, (_) => chars[r.nextInt(chars.length)]).join();
}

/// Check whether [url] is a Pixiv-hosted media URL.
bool isPixivMediaUrl(String url) =>
    url.contains('i.pximg.net') || url.contains('embed.pixiv.net');

/// Print the program header. Replaces colorama-based output with simple ANSI codes.
void printHeader() {
  printOriginalHeader();
  return;
  // ignore: dead_code
  const padding = 60;
  const yellow = '\x1B[33m';
  const cyan = '\x1B[36m';
  const reset = '\x1B[0m';
  final border = '─' * (padding - 2);
  print('┌$border┐');
  print(
      '│ $yellow${'PixivDownloader2 version ${pixiv_constant.PIXIVUTIL_VERSION}'.padRight(padding - 3)}$reset│');
  print('│ $cyan${pixiv_constant.PIXIVUTIL_LINK.padRight(padding - 3)}$reset│');
  print(
      '│ $yellow${'Donate at ${pixiv_constant.PIXIVUTIL_DONATE}'.padRight(padding - 3)}$reset│');
  print('└$border┘');
}

/// Try to format a [DateTime] using a Python-style strftime format string.
String strftime(String fmt, DateTime dt) {
  return DateFormat(_convertPyDateFormat(fmt)).format(dt);
}

void printOriginalHeader() {
  const padding = 60;
  const yellow = '\x1B[33m';
  const cyan = '\x1B[36m';
  const reset = '\x1B[0m';
  final border = '─' * (padding - 2);
  print('┌$border┐');
  print(
      '│ $yellow${'PixivDownloader2 version ${pixiv_constant.PIXIVUTIL_VERSION}'.padRight(padding - 3)}$reset│');
  print('│ $cyan${pixiv_constant.PIXIVUTIL_LINK.padRight(padding - 3)}$reset│');
  print(
      '│ $yellow${'Donate at ${pixiv_constant.PIXIVUTIL_DONATE}'.padRight(padding - 3)}$reset│');
  print('└$border┘');
}

/// Mark the given time as the application start time.
DateTime startTime = DateTime.now();

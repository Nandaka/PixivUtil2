/// Configuration manager ported from PixivConfig.py.
library;

import 'dart:io';

import 'package:ini/ini.dart';
import 'package:path/path.dart' as p;

import 'pixiv_helper.dart' as pixiv_helper;

bool _stringNotEmpty(String? value) => value != null && value.isNotEmpty;

String _defaultArtworkImageFormat() =>
    '%image_id%${Platform.pathSeparator}%urlFilename%';

String _defaultArtworkInfoFormat() => '%image_id%${Platform.pathSeparator}info';

class ConfigItem {
  final String section;
  final String option;
  final dynamic defaultValue;
  final dynamic Function(dynamic)? followup;
  final bool Function(dynamic)? restriction;
  final String? errorMessage;

  ConfigItem(
    this.section,
    this.option,
    this.defaultValue, {
    this.followup,
    this.restriction,
    this.errorMessage,
  });

  dynamic processValue(dynamic value) {
    var v = value;
    if (restriction != null) {
      if (!restriction!(v)) {
        if (errorMessage != null) {
          throw ArgumentError('$errorMessage $option: [$v]');
        } else {
          throw ArgumentError('Illegal value for $option: [$v]');
        }
      }
    }
    if (followup != null) v = followup!(v);
    return v;
  }
}

class PixivConfig {
  String configFileLocation = './config.ini';

  final Map<String, dynamic> _values = {};

  static final List<ConfigItem> _items = _buildItems();

  PixivConfig() {
    for (final item in _items) {
      _values[item.option] = item.processValue(item.defaultValue);
    }
  }

  dynamic getValue(String option) => _values[option];
  void setValue(String option, dynamic value) {
    _values[option] = value;
  }

  // Convenience getters used throughout the codebase.
  bool get useProxy => _values['useProxy'] as bool? ?? false;
  String get proxyAddress => _values['proxyAddress'] as String? ?? '';
  String get useragent => _values['useragent'] as String? ?? 'Mozilla/5.0';
  bool get useRobots => _values['useRobots'] as bool? ?? true;
  int get timeout => _values['timeout'] as int? ?? 60;
  int get retry => _values['retry'] as int? ?? 3;
  int get retryWait => _values['retryWait'] as int? ?? 5;
  int get downloadDelay => _values['downloadDelay'] as int? ?? 5;
  bool get checkNewVersion => _values['checkNewVersion'] as bool? ?? true;
  bool get notifyBetaVersion => _values['notifyBetaVersion'] as bool? ?? true;
  bool get openNewVersion => _values['openNewVersion'] as bool? ?? true;
  bool get enableSSLVerification =>
      _values['enableSSLVerification'] as bool? ?? true;

  String get logLevel => _values['logLevel'] as String? ?? 'DEBUG';
  bool get enableDump => _values['enableDump'] as bool? ?? true;
  String get skipDumpFilter => _values['skipDumpFilter'] as String? ?? '';
  bool get dumpMediumPage => _values['dumpMediumPage'] as bool? ?? false;
  bool get dumpTagSearchPage => _values['dumpTagSearchPage'] as bool? ?? false;
  bool get debugHttp => _values['debugHttp'] as bool? ?? false;
  bool get disableLog => _values['disableLog'] as bool? ?? false;
  bool get disableScreenClear =>
      _values['disableScreenClear'] as bool? ?? false;

  String get rootDirectory => _values['rootDirectory'] as String? ?? '.';
  bool get downloadAvatar => _values['downloadAvatar'] as bool? ?? false;
  String get downloadListDirectory =>
      _values['downloadListDirectory'] as String? ?? '.';
  bool get useList => _values['useList'] as bool? ?? false;
  bool get processFromDb => _values['processFromDb'] as bool? ?? true;
  bool get useSuppressTags => _values['useSuppressTags'] as bool? ?? false;
  int get tagsLimit => _values['tagsLimit'] as int? ?? -1;
  bool get writeImageJSON => _values['writeImageJSON'] as bool? ?? false;
  bool get writeImageInfo => _values['writeImageInfo'] as bool? ?? false;
  bool get writeRawJSON => _values['writeRawJSON'] as bool? ?? false;
  String get rawJSONFilter => _values['RawJSONFilter'] as String? ?? '';
  bool get includeSeriesJSON => _values['includeSeriesJSON'] as bool? ?? false;
  bool get writeImageXMP => _values['writeImageXMP'] as bool? ?? false;
  bool get writeImageXMPPerImage =>
      _values['writeImageXMPPerImage'] as bool? ?? false;
  bool get verifyImage => _values['verifyImage'] as bool? ?? false;
  bool get writeUrlInDescription =>
      _values['writeUrlInDescription'] as bool? ?? false;
  bool get stripHTMLTagsFromCaption =>
      _values['stripHTMLTagsFromCaption'] as bool? ?? false;
  String get urlBlacklistRegex => _values['urlBlacklistRegex'] as String? ?? '';
  String get dbPath => _values['dbPath'] as String? ?? '';
  bool get setLastModified => _values['setLastModified'] as bool? ?? true;
  bool get useLocalTimezone => _values['useLocalTimezone'] as bool? ?? false;
  String get defaultSketchOption =>
      _values['defaultSketchOption'] as String? ?? '';

  String get filenameFormat =>
      _values['filenameFormat'] as String? ?? _defaultArtworkImageFormat();
  String get filenameMangaFormat =>
      _values['filenameMangaFormat'] as String? ?? _defaultArtworkImageFormat();
  String get filenameInfoFormat =>
      _values['filenameInfoFormat'] as String? ?? _defaultArtworkInfoFormat();
  String get filenameMangaInfoFormat =>
      _values['filenameMangaInfoFormat'] as String? ??
      _defaultArtworkInfoFormat();
  String get filenameSeriesJSON =>
      _values['filenameSeriesJSON'] as String? ?? '';
  String get filenameFormatSketch =>
      _values['filenameFormatSketch'] as String? ?? '';
  String get filenameFormatNovel =>
      _values['filenameFormatNovel'] as String? ?? '';
  String get avatarNameFormat => _values['avatarNameFormat'] as String? ?? '';
  String get backgroundNameFormat =>
      _values['backgroundNameFormat'] as String? ?? '';
  String get tagsSeparator => _values['tagsSeparator'] as String? ?? ', ';
  bool get createMangaDir => _values['createMangaDir'] as bool? ?? false;
  bool get useTagsAsDir => _values['useTagsAsDir'] as bool? ?? false;
  String get urlDumpFilename =>
      _values['urlDumpFilename'] as String? ?? 'url_list_%Y%m%d';
  bool get useTranslatedTag => _values['useTranslatedTag'] as bool? ?? false;
  String get tagTranslationLocale =>
      _values['tagTranslationLocale'] as String? ?? 'en';
  String get customBadChars => _values['customBadChars'] as String? ?? '';
  String get customCleanUpRe => _values['customCleanUpRe'] as String? ?? '';

  String get username => _values['username'] as String? ?? '';
  String get password => _values['password'] as String? ?? '';
  String get cookie => _values['cookie'] as String? ?? '';
  String get cookieFanbox => _values['cookieFanbox'] as String? ?? '';
  String get cookieFanboxTemp => _values['cookieFanboxTemp'] as String? ?? '';
  String get refreshToken => _values['refresh_token'] as String? ?? '';
  String get cfClearance => _values['cf_clearance'] as String? ?? '';
  String get cfBm => _values['cf_bm'] as String? ?? '';

  int get numberOfPage => _values['numberOfPage'] as int? ?? 0;
  bool get r18mode => _values['r18mode'] as bool? ?? false;
  int get r18Type => _values['r18Type'] as int? ?? 0;
  String get dateFormat => _values['dateFormat'] as String? ?? '';
  bool get autoAddMember => _values['autoAddMember'] as bool? ?? false;
  bool get autoAddTag => _values['autoAddTag'] as bool? ?? false;
  bool get autoAddCaption => _values['autoAddCaption'] as bool? ?? false;
  bool get autoAddSeries => _values['autoAddSeries'] as bool? ?? false;
  bool get aiDisplayFewer => _values['aiDisplayFewer'] as bool? ?? false;

  String get ffmpeg => _values['ffmpeg'] as String? ?? 'ffmpeg.exe';
  String get ffmpegCodec => _values['ffmpegCodec'] as String? ?? 'libvpx-vp9';
  String get ffmpegExt => _values['ffmpegExt'] as String? ?? 'webm';
  String get ffmpegParam => _values['ffmpegParam'] as String? ?? '';
  String get mkvCodec => _values['mkvCodec'] as String? ?? 'copy';
  String get mkvParam => _values['mkvParam'] as String? ?? '';
  String get webpCodec => _values['webpCodec'] as String? ?? 'libwebp';
  String get webpParam => _values['webpParam'] as String? ?? '';
  String get gifParam => _values['gifParam'] as String? ?? '';
  String get apngParam => _values['apngParam'] as String? ?? '';
  String get avifCodec => _values['avifCodec'] as String? ?? 'libaom-av1';
  String get avifParam => _values['avifParam'] as String? ?? '';
  bool get verboseOutput => _values['verboseOutput'] as bool? ?? false;

  bool get writeUgoiraInfo => _values['writeUgoiraInfo'] as bool? ?? false;
  bool get createUgoira => _values['createUgoira'] as bool? ?? false;
  bool get createMkv => _values['createMkv'] as bool? ?? false;
  bool get createWebm => _values['createWebm'] as bool? ?? false;
  bool get createWebp => _values['createWebp'] as bool? ?? false;
  bool get createGif => _values['createGif'] as bool? ?? false;
  bool get createApng => _values['createApng'] as bool? ?? false;
  bool get createAvif => _values['createAvif'] as bool? ?? false;
  bool get deleteUgoira => _values['deleteUgoira'] as bool? ?? false;
  bool get deleteZipFile => _values['deleteZipFile'] as bool? ?? false;

  int get minFileSize => _values['minFileSize'] as int? ?? 0;
  int get maxFileSize => _values['maxFileSize'] as int? ?? 0;
  bool get checkLastModified => _values['checkLastModified'] as bool? ?? true;
  bool get alwaysCheckFileSize =>
      _values['alwaysCheckFileSize'] as bool? ?? false;
  bool get overwrite => _values['overwrite'] as bool? ?? false;
  bool get backupOldFile => _values['backupOldFile'] as bool? ?? false;
  int get dayLastUpdated => _values['dayLastUpdated'] as int? ?? 7;
  int get checkUpdatedLimit => _values['checkUpdatedLimit'] as int? ?? 0;
  int get checkUpdatedLimitFanbox =>
      _values['checkUpdatedLimitFanbox'] as int? ?? 0;
  bool get useBlacklistTags => _values['useBlacklistTags'] as bool? ?? false;
  bool get useBlacklistTitles =>
      _values['useBlacklistTitles'] as bool? ?? false;
  bool get useBlacklistTitlesRegex =>
      _values['useBlacklistTitlesRegex'] as bool? ?? false;
  int get dateDiff => _values['dateDiff'] as int? ?? 0;
  bool get enableInfiniteLoop =>
      _values['enableInfiniteLoop'] as bool? ?? false;
  bool get useBlacklistMembers =>
      _values['useBlacklistMembers'] as bool? ?? false;
  bool get downloadResized => _values['downloadResized'] as bool? ?? false;
  bool get skipUnknownSize => _values['skipUnknownSize'] as bool? ?? false;
  bool get enablePostProcessing =>
      _values['enablePostProcessing'] as bool? ?? false;
  String get postProcessingCmd => _values['postProcessingCmd'] as String? ?? '';
  String get extensionFilter => _values['extensionFilter'] as String? ?? '';
  int get downloadBuffer => _values['downloadBuffer'] as int? ?? 512;
  bool get createPixivArchive =>
      _values['createPixivArchive'] as bool? ?? false;
  String get createPixivArchiveCompressionType =>
      _values['createPixivArchiveCompressionType'] as String? ?? 'ZIP_STORED';
  int get createPixivArchiveCompressionLevel =>
      _values['createPixivArchiveCompressionLevel'] as int? ?? 0;

  String get filenameFormatFanboxCover =>
      _values['filenameFormatFanboxCover'] as String? ?? '';
  String get filenameFormatFanboxContent =>
      _values['filenameFormatFanboxContent'] as String? ?? '';
  String get filenameFormatFanboxInfo =>
      _values['filenameFormatFanboxInfo'] as String? ?? '';
  bool get writeHtml => _values['writeHtml'] as bool? ?? false;
  int get minTextLengthForNonArticle =>
      _values['minTextLengthForNonArticle'] as int? ?? 45;
  int get minImageCountForNonArticle =>
      _values['minImageCountForNonArticle'] as int? ?? 3;
  bool get useAbsolutePathsInHtml =>
      _values['useAbsolutePathsInHtml'] as bool? ?? false;
  bool get downloadCoverWhenRestricted =>
      _values['downloadCoverWhenRestricted'] as bool? ?? false;
  bool get downloadCover => _values['downloadCover'] as bool? ?? true;
  bool get checkDBProcessHistory =>
      _values['checkDBProcessHistory'] as bool? ?? false;
  String get listPathFanbox =>
      _values['listPathFanbox'] as String? ?? 'listfanbox.txt';

  /// Proxy as a `{'http': uri, 'https': uri}` map.
  Map<String, String>? get proxy {
    final value = proxyAddress;
    if (value.isEmpty) return null;
    final m = RegExp(r'^(?:(https?|socks[45]h?)://)?([\w.-]+)(:\d+)?$')
        .firstMatch(value);
    if (m == null) return null;
    final scheme = (m.group(1) ?? 'http');
    final netloc = m.group(2)!;
    final port = m.group(3) ?? '';
    final uri = '$scheme://$netloc$port';
    return {'http': uri, 'https': uri};
  }

  /// Load configuration from [path] (or `script_path/config.ini`).
  Future<void> loadConfig([String? path]) async {
    if (path != null) {
      configFileLocation = path;
    } else {
      configFileLocation =
          '${pixiv_helper.modulePath()}${Platform.pathSeparator}config.ini';
    }
    configFileLocation = p.absolute(configFileLocation);

    print('Reading $configFileLocation ...');

    final file = File(configFileLocation);
    if (!file.existsSync()) {
      print('Config file not found, writing defaults.');
      await writeConfig(error: true, path: configFileLocation);
      return;
    }

    final lines = await file.readAsLines();
    final config = Config.fromStrings(lines);
    var haveError = false;
    for (final item in _items) {
      dynamic value;
      try {
        final raw = config.get(item.section, item.option);
        if (raw == null) {
          haveError = true;
          for (final section in config.sections()) {
            final v = config.get(section, item.option);
            if (v != null) {
              value = v;
              break;
            }
          }
          if (value == null) {
            value = item.defaultValue;
          }
        } else {
          value = _coerce(raw, item.defaultValue);
        }
      } catch (_) {
        value = item.defaultValue;
        haveError = true;
      }

      try {
        value = item.processValue(value);
      } catch (_) {
        value = item.defaultValue;
        haveError = true;
      }
      _values[item.option] = value;
    }
    if (haveError) {
      print('Some configurations were invalid; defaults restored.');
      await writeConfig(error: true, path: configFileLocation);
    }
    print('Configuration loaded.');
  }

  dynamic _coerce(String raw, dynamic defaultValue) {
    if (defaultValue is bool) {
      final lower = raw.toLowerCase();
      return lower == 'true' || lower == '1' || lower == 'yes' || lower == 'on';
    }
    if (defaultValue is int) {
      return int.tryParse(raw) ?? defaultValue;
    }
    if (defaultValue is double) {
      return double.tryParse(raw) ?? defaultValue;
    }
    return raw;
  }

  Future<void> writeConfig({bool error = false, String? path}) async {
    print('Writing config file...');
    final config = Config();
    final sections = <String, List<ConfigItem>>{};
    for (final item in _items) {
      sections.putIfAbsent(item.section, () => []).add(item);
    }
    for (final entry in sections.entries) {
      config.addSection(entry.key);
      for (final item in entry.value) {
        config.set(entry.key, item.option, '${_values[item.option]}');
      }
    }
    final loc = path ?? 'config.ini';
    final tmp = '$loc.tmp';
    await File(tmp).writeAsString(config.toString());
    final f = File(loc);
    if (f.existsSync()) {
      if (error) {
        final backup =
            '$loc.error-${DateTime.now().millisecondsSinceEpoch ~/ 1000}';
        await f.rename(backup);
      } else {
        await f.rename('$loc.bak');
      }
    }
    await File(tmp).rename(loc);
    print('Configuration saved.');
  }

  void printConfig() {
    print('Configuration:');
    final groups = <String, List<ConfigItem>>{};
    for (final item in _items) {
      groups.putIfAbsent(item.section, () => []).add(item);
    }
    final orderedSections = [
      'Authentication',
      'Network',
      'Debug',
      'IrfanView',
      'Settings',
      'Filename',
      'Pixiv',
      'FANBOX',
      'FFmpeg',
      'Ugoira',
      'DownloadControl',
    ];
    for (final s in orderedSections) {
      final g = groups[s];
      if (g == null) continue;
      print(' [$s]');
      for (final item in g) {
        print(' - ${item.option.padRight(25)} = ${_values[item.option]}');
      }
    }
  }

  static List<ConfigItem> _buildItems() {
    return [
      ConfigItem('Network', 'useProxy', false),
      ConfigItem('Network', 'proxyAddress', ''),
      ConfigItem('Network', 'useragent', 'Mozilla/5.0'),
      ConfigItem('Network', 'useRobots', true),
      ConfigItem('Network', 'timeout', 60),
      ConfigItem('Network', 'retry', 3),
      ConfigItem('Network', 'retryWait', 5),
      ConfigItem('Network', 'downloadDelay', 5),
      ConfigItem('Network', 'checkNewVersion', true),
      ConfigItem('Network', 'notifyBetaVersion', true),
      ConfigItem('Network', 'openNewVersion', true),
      ConfigItem('Network', 'enableSSLVerification', true),
      ConfigItem('Debug', 'logLevel', 'DEBUG',
          followup: (v) => (v as String).toUpperCase(),
          restriction: (v) => const [
                'CRITICAL',
                'ERROR',
                'WARN',
                'WARNING',
                'INFO',
                'DEBUG',
                'NOTSET'
              ].contains((v as String).toUpperCase())),
      ConfigItem('Debug', 'enableDump', true),
      ConfigItem('Debug', 'skipDumpFilter', ''),
      ConfigItem('Debug', 'dumpMediumPage', false),
      ConfigItem('Debug', 'dumpTagSearchPage', false),
      ConfigItem('Debug', 'debugHttp', false),
      ConfigItem('Debug', 'disableLog', false),
      ConfigItem('Debug', 'disableScreenClear', false),
      ConfigItem('IrfanView', 'IrfanViewPath', r'C:\Program Files\IrfanView'),
      ConfigItem('IrfanView', 'startIrfanView', false),
      ConfigItem('IrfanView', 'startIrfanSlide', false),
      ConfigItem('IrfanView', 'createDownloadLists', false),
      ConfigItem('Settings', 'downloadListDirectory', '.'),
      ConfigItem('Settings', 'useList', false),
      ConfigItem('Settings', 'processFromDb', true),
      ConfigItem('Settings', 'rootDirectory', '.'),
      ConfigItem('Settings', 'downloadAvatar', false),
      ConfigItem('Settings', 'useSuppressTags', false),
      ConfigItem('Settings', 'tagsLimit', -1),
      ConfigItem('Settings', 'writeImageJSON', false),
      ConfigItem('Settings', 'writeImageInfo', false),
      ConfigItem('Settings', 'writeRawJSON', false),
      ConfigItem('Settings', 'RawJSONFilter',
          'id,title,description,alt,userIllusts,storableTags,zoneConfig,extraData,comicPromotion,fanboxPromotion'),
      ConfigItem('Settings', 'includeSeriesJSON', false),
      ConfigItem('Settings', 'writeImageXMP', false),
      ConfigItem('Settings', 'writeImageXMPPerImage', false),
      ConfigItem('Settings', 'verifyImage', false),
      ConfigItem('Settings', 'writeUrlInDescription', false),
      ConfigItem('Settings', 'stripHTMLTagsFromCaption', false),
      ConfigItem('Settings', 'urlBlacklistRegex', ''),
      ConfigItem('Settings', 'dbPath', ''),
      ConfigItem('Settings', 'setLastModified', true),
      ConfigItem('Settings', 'useLocalTimezone', false),
      ConfigItem('Settings', 'defaultSketchOption', ''),
      ConfigItem('Filename', 'filenameFormat', _defaultArtworkImageFormat(),
          restriction: (v) => _stringNotEmpty(v as String?)),
      ConfigItem(
          'Filename', 'filenameMangaFormat', _defaultArtworkImageFormat(),
          restriction: (v) {
        final s = v as String?;
        return _stringNotEmpty(s) &&
            (s!.contains('%urlFilename%') ||
                s.contains('%page_index%') ||
                s.contains('%page_number%'));
      },
          errorMessage:
              'At least %urlFilename%, %page_index%, or %page_number% is required in'),
      ConfigItem('Filename', 'filenameInfoFormat', _defaultArtworkInfoFormat(),
          restriction: (v) => _stringNotEmpty(v as String?)),
      ConfigItem(
          'Filename', 'filenameMangaInfoFormat', _defaultArtworkInfoFormat(),
          restriction: (v) => _stringNotEmpty(v as String?)),
      ConfigItem('Filename', 'filenameSeriesJSON',
          '%artist% (%member_id%)${Platform.pathSeparator}%manga_series_id% - %manga_series_title%',
          restriction: (v) => _stringNotEmpty(v as String?)),
      ConfigItem('Filename', 'filenameFormatSketch',
          '%artist% (%member_id%)${Platform.pathSeparator}%urlFilename% - %title%',
          restriction: (v) => _stringNotEmpty(v as String?)),
      ConfigItem('Filename', 'filenameFormatNovel',
          '%artist% (%member_id%)${Platform.pathSeparator}%manga_series_id% %manga_series_order% %urlFilename% - %title%',
          restriction: (v) => _stringNotEmpty(v as String?)),
      ConfigItem('Filename', 'avatarNameFormat', ''),
      ConfigItem('Filename', 'backgroundNameFormat', ''),
      ConfigItem('Filename', 'tagsSeparator', ', '),
      ConfigItem('Filename', 'createMangaDir', false),
      ConfigItem('Filename', 'useTagsAsDir', false),
      ConfigItem('Filename', 'urlDumpFilename', 'url_list_%Y%m%d'),
      ConfigItem('Filename', 'useTranslatedTag', false),
      ConfigItem('Filename', 'tagTranslationLocale', 'en'),
      ConfigItem('Filename', 'customBadChars', '',
          followup: (v) => pixiv_helper.parseCustomSanitizer(v as String)),
      ConfigItem('Filename', 'customCleanUpRe', '',
          followup: (v) => pixiv_helper.parseCustomCleanUpRe(v as String)),
      ConfigItem('Authentication', 'username', ''),
      ConfigItem('Authentication', 'password', ''),
      ConfigItem('Authentication', 'cookie', ''),
      ConfigItem('Authentication', 'cookieFanbox', ''),
      ConfigItem('Authentication', 'cookieFanboxTemp', ''),
      ConfigItem('Authentication', 'refresh_token', ''),
      ConfigItem('Authentication', 'cf_clearance', ''),
      ConfigItem('Authentication', 'cf_bm', ''),
      ConfigItem('Pixiv', 'numberOfPage', 0),
      ConfigItem('Pixiv', 'r18mode', false),
      ConfigItem('Pixiv', 'r18Type', 0),
      ConfigItem('Pixiv', 'dateFormat', ''),
      ConfigItem('Pixiv', 'autoAddMember', false),
      ConfigItem('Pixiv', 'autoAddTag', false),
      ConfigItem('Pixiv', 'autoAddCaption', false),
      ConfigItem('Pixiv', 'autoAddSeries', false),
      ConfigItem('Pixiv', 'aiDisplayFewer', false),
      ConfigItem('FANBOX', 'filenameFormatFanboxCover',
          'FANBOX %artist% (%member_id%)${Platform.pathSeparator}%urlFilename% - %title%',
          restriction: (v) => _stringNotEmpty(v as String?)),
      ConfigItem('FANBOX', 'filenameFormatFanboxContent',
          'FANBOX %artist% (%member_id%)${Platform.pathSeparator}%urlFilename% - %title%',
          restriction: (v) {
        final s = v as String?;
        return _stringNotEmpty(s) &&
            (s!.contains('%urlFilename%') ||
                s.contains('%page_index%') ||
                s.contains('%page_number%'));
      },
          errorMessage:
              'At least %urlFilename%, %page_index%, or %page_number% is required in'),
      ConfigItem('FANBOX', 'filenameFormatFanboxInfo',
          'FANBOX %artist% (%member_id%)${Platform.pathSeparator}%urlFilename% - %title%',
          restriction: (v) => _stringNotEmpty(v as String?)),
      ConfigItem('FANBOX', 'writeHtml', false),
      ConfigItem('FANBOX', 'minTextLengthForNonArticle', 45),
      ConfigItem('FANBOX', 'minImageCountForNonArticle', 3),
      ConfigItem('FANBOX', 'useAbsolutePathsInHtml', false),
      ConfigItem('FANBOX', 'downloadCoverWhenRestricted', false),
      ConfigItem('FANBOX', 'downloadCover', true),
      ConfigItem('FANBOX', 'checkDBProcessHistory', false),
      ConfigItem('FANBOX', 'checkUpdatedLimitFanbox', 0),
      ConfigItem('FANBOX', 'listPathFanbox', 'listfanbox.txt'),
      ConfigItem('FFmpeg', 'ffmpeg', 'ffmpeg.exe'),
      ConfigItem('FFmpeg', 'ffmpegCodec', 'libvpx-vp9'),
      ConfigItem('FFmpeg', 'ffmpegExt', 'webm'),
      ConfigItem('FFmpeg', 'ffmpegParam',
          '-lossless 0 -crf 15 -b 0 -vsync 0 -pix_fmt yuv420p'),
      ConfigItem('FFmpeg', 'mkvCodec', 'copy'),
      ConfigItem('FFmpeg', 'mkvParam', ''),
      ConfigItem('FFmpeg', 'webpCodec', 'libwebp'),
      ConfigItem('FFmpeg', 'webpParam',
          '-lossless 0 -compression_level 5 -quality 100 -loop 0 -vsync 0'),
      ConfigItem('FFmpeg', 'gifParam',
          '-filter_complex [0:v]split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=5:diff_mode=rectangle -vsync 0'),
      ConfigItem('FFmpeg', 'apngParam', '-plays 0 -vsync 0'),
      ConfigItem('FFmpeg', 'avifCodec', 'libaom-av1'),
      ConfigItem('FFmpeg', 'avifParam',
          '-cpu-used 4 -crf 0 -row-mt 1 -tile-columns 2 -tile-rows 2 -vsync 0'),
      ConfigItem('FFmpeg', 'verboseOutput', false),
      ConfigItem('Ugoira', 'writeUgoiraInfo', false),
      ConfigItem('Ugoira', 'createUgoira', false),
      ConfigItem('Ugoira', 'createMkv', false),
      ConfigItem('Ugoira', 'createWebm', false),
      ConfigItem('Ugoira', 'createWebp', false),
      ConfigItem('Ugoira', 'createGif', false),
      ConfigItem('Ugoira', 'createApng', false),
      ConfigItem('Ugoira', 'createAvif', false),
      ConfigItem('Ugoira', 'deleteUgoira', false),
      ConfigItem('Ugoira', 'deleteZipFile', false),
      ConfigItem('DownloadControl', 'minFileSize', 0),
      ConfigItem('DownloadControl', 'maxFileSize', 0),
      ConfigItem('DownloadControl', 'checkLastModified', true),
      ConfigItem('DownloadControl', 'alwaysCheckFileSize', false),
      ConfigItem('DownloadControl', 'overwrite', false),
      ConfigItem('DownloadControl', 'backupOldFile', false),
      ConfigItem('DownloadControl', 'dayLastUpdated', 7),
      ConfigItem('DownloadControl', 'checkUpdatedLimit', 0),
      ConfigItem('DownloadControl', 'useBlacklistTags', false),
      ConfigItem('DownloadControl', 'useBlacklistTitles', false),
      ConfigItem('DownloadControl', 'useBlacklistTitlesRegex', false),
      ConfigItem('DownloadControl', 'dateDiff', 0),
      ConfigItem('DownloadControl', 'enableInfiniteLoop', false),
      ConfigItem('DownloadControl', 'useBlacklistMembers', false),
      ConfigItem('DownloadControl', 'downloadResized', false),
      ConfigItem('DownloadControl', 'skipUnknownSize', false),
      ConfigItem('DownloadControl', 'enablePostProcessing', false),
      ConfigItem('DownloadControl', 'postProcessingCmd', ''),
      ConfigItem('DownloadControl', 'extensionFilter', ''),
      ConfigItem('DownloadControl', 'downloadBuffer', 512,
          restriction: (v) => (v as int) > 0),
      ConfigItem('DownloadControl', 'createPixivArchive', false),
      ConfigItem(
          'DownloadControl', 'createPixivArchiveCompressionType', 'ZIP_STORED',
          restriction: (v) => const {
                'ZIP_STORED',
                'ZIP_DEFLATED',
                'ZIP_BZIP2',
                'ZIP_LZMA'
              }.contains(v as String)),
      ConfigItem('DownloadControl', 'createPixivArchiveCompressionLevel', 0,
          restriction: (v) => (v as int) >= 0 && v < 10),
    ];
  }
}

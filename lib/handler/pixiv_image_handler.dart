/// Image (illustration) handler.
library;

import 'dart:io';

import '../common/pixiv_browser.dart';
import '../common/pixiv_config.dart';
import '../common/pixiv_constant.dart' as pixiv_constant;
import '../common/pixiv_exception.dart';
import '../common/pixiv_helper.dart' as pixiv_helper;
import '../model/pixiv_artist.dart';
import 'pixiv_download_handler.dart' as download_handler;

/// Process a single image: fetch its metadata, build the file name, and
/// download every image URL it contains.
Future<int> processImage({
  required dynamic caller,
  required PixivConfig config,
  PixivArtist? artist,
  required int imageId,
  String userDir = '',
  bool bookmark = false,
  String searchTags = '',
  String titlePrefix = '',
  int imageResponseCount = -1,
  int mangaSeriesOrder = -1,
  dynamic mangaSeriesParent,
  void Function({String? title, String? message, dynamic type})? notifier,
}) async {
  notifier ??= pixiv_helper.dummyNotifier;
  pixiv_helper.printAndLog('info', 'Processing Image: $imageId ($titlePrefix)');
  final br = caller.br as PixivBrowser;
  try {
    final (image, _) = await br.getImagePage(
      imageId,
      parent: artist,
      fromBookmark: bookmark,
      imageResponseCount: imageResponseCount,
      mangaSeriesOrder: mangaSeriesOrder,
      mangaSeriesParent: mangaSeriesParent,
      writeRawJSON: config.writeRawJSON,
      stripHTMLTagsFromCaption: config.stripHTMLTagsFromCaption,
    );
    image.printInfo();

    if (image.imageUrls.isEmpty) {
      pixiv_helper.printAndLog('warn', 'Image $imageId has no URLs.');
      return pixiv_constant.PIXIVUTIL_NOT_OK;
    }
    final resolvedArtist = artist ?? image.artist;

    final format = image.imageMode == 'manga'
        ? config.filenameMangaFormat
        : config.filenameFormat;

    final downloadedPaths = <String>[];
    var allOk = true;
    for (var i = 0; i < image.imageUrls.length; i++) {
      if (_isStopRequested(caller)) {
        pixiv_helper.printAndLog(
            'warn', 'Stop requested; skipping remaining pages for $imageId.');
        allOk = false;
        break;
      }
      final url = image.imageUrls[i];
      final filename = pixiv_helper.makeFilename(
        format,
        image,
        artistInfo: resolvedArtist,
        tagsSeparator: config.tagsSeparator,
        tagsLimit: config.tagsLimit,
        fileUrl: url,
        bookmark: bookmark,
        searchTags: searchTags,
        useTranslatedTag: config.useTranslatedTag,
        tagTranslationLocale: config.tagTranslationLocale,
      );
      final fullPath = pixiv_helper.sanitizeFilename(
          filename, userDir.isNotEmpty ? userDir : config.rootDirectory);
      downloadedPaths.add(fullPath);
      pixiv_helper.printAndLog(null, 'Filename: $fullPath');

      final result = await download_handler.downloadImage(
        caller: caller,
        config: config,
        url: url,
        filename: fullPath,
        referer: 'https://www.pixiv.net/artworks/$imageId',
      );
      if (result != pixiv_constant.PIXIVUTIL_OK &&
          result != pixiv_constant.PIXIVUTIL_SKIP_DUPLICATE) {
        allOk = false;
      }
    }

    if (config.writeImageInfo) {
      final infoFormat = image.imageMode == 'manga'
          ? config.filenameMangaInfoFormat
          : config.filenameInfoFormat;
      final infoFilename = pixiv_helper.makeFilename(
        infoFormat,
        image,
        artistInfo: resolvedArtist,
        tagsSeparator: config.tagsSeparator,
        tagsLimit: config.tagsLimit,
        fileUrl: image.imageUrls.first,
        bookmark: bookmark,
        searchTags: searchTags,
        appendExtension: false,
      );
      final infoPath = pixiv_helper.sanitizeFilename('$infoFilename.txt',
          userDir.isNotEmpty ? userDir : config.rootDirectory);
      await image.writeInfo(infoPath);
    }
    if (config.writeImageJSON) {
      final infoFormat = image.imageMode == 'manga'
          ? config.filenameMangaInfoFormat
          : config.filenameInfoFormat;
      final jsonName = pixiv_helper.makeFilename(
        infoFormat,
        image,
        artistInfo: resolvedArtist,
        tagsSeparator: config.tagsSeparator,
        tagsLimit: config.tagsLimit,
        fileUrl: image.imageUrls.first,
        bookmark: bookmark,
        searchTags: searchTags,
        appendExtension: false,
      );
      final jsonPath = pixiv_helper.sanitizeFilename('$jsonName.json',
          userDir.isNotEmpty ? userDir : config.rootDirectory);
      await image.writeJson(jsonPath,
          includeSeriesJson: config.includeSeriesJSON);
    }

    if (config.setLastModified) {
      _touchFiles(downloadedPaths, image.worksDateDateTime);
    }

    caller.dbManager.insertImage(imageId, resolvedArtist?.artistId ?? 0,
        title: image.imageTitle,
        saveName: image.imageUrls.join(','),
        isManga: image.imageMode == 'manga' ? 'Y' : 'N',
        caption: image.imageCaption);
    caller.dbManager.insertDownloadMetadata(
      imageId: imageId,
      title: image.imageTitle,
      caption: image.imageCaption,
      tags: image.imageTags,
      pages: image.imageCount,
      worksDate: image.worksDate,
      totalViews: image.jd_rtv,
      totalRating: image.jd_rtc,
      bookmarkCount: image.bookmark_count,
    );
    if (image.ai_type > 0) {
      caller.dbManager.insertAiInfo(imageId, image.ai_type);
    }

    return allOk
        ? pixiv_constant.PIXIVUTIL_OK
        : pixiv_constant.PIXIVUTIL_NOT_OK;
  } on PixivException catch (e) {
    pixiv_helper.printAndLog('error', 'Image $imageId failed: $e');
    return e.errorCode == PixivException.IMAGE_DELETED
        ? pixiv_constant.PIXIVUTIL_SKIP_BLACKLIST
        : pixiv_constant.PIXIVUTIL_NOT_OK;
  }
}

Future<void> processImageMetadata({
  required dynamic caller,
  required PixivConfig config,
  required int imageId,
  void Function({String? title, String? message, dynamic type})? notifier,
}) async {
  notifier ??= pixiv_helper.dummyNotifier;
  pixiv_helper.printAndLog('info', 'Processing Image Metadata: $imageId');
  final br = caller.br as PixivBrowser;
  final (image, _) = await br.getImagePage(
    imageId,
    writeRawJSON: config.writeRawJSON,
    stripHTMLTagsFromCaption: config.stripHTMLTagsFromCaption,
  );
  image.printInfo();
  final resolvedArtist = image.artist;
  caller.dbManager.insertImage(
    imageId,
    resolvedArtist?.artistId ?? 0,
    title: image.imageTitle,
    saveName: image.imageUrls.join(','),
    isManga: image.imageMode == 'manga' ? 'Y' : 'N',
    caption: image.imageCaption,
  );
  caller.dbManager.insertDownloadMetadata(
    imageId: imageId,
    title: image.imageTitle,
    caption: image.imageCaption,
    tags: image.imageTags,
    pages: image.imageCount,
    worksDate: image.worksDate,
    totalViews: image.jd_rtv,
    totalRating: image.jd_rtc,
    bookmarkCount: image.bookmark_count,
  );
  if (image.ai_type > 0) {
    caller.dbManager.insertAiInfo(imageId, image.ai_type);
  }
}

Future<void> processImageMetadataFromDb({
  required dynamic caller,
  required PixivConfig config,
  int limit = 0,
  bool refreshExisting = false,
  void Function({String? title, String? message, dynamic type})? notifier,
}) async {
  notifier ??= pixiv_helper.dummyNotifier;
  final rows = caller.dbManager.raw.select('''
    SELECT i.image_id
    FROM pixiv_master_image i
    LEFT JOIN pixiv_download_metadata m ON m.image_id = i.image_id
    WHERE ? = 1
       OR m.image_id IS NULL
       OR COALESCE(m.title, '') = ''
       OR COALESCE(m.caption, '') = ''
       OR COALESCE(m.tags, '') = ''
    ORDER BY i.image_id DESC
    ${limit > 0 ? 'LIMIT $limit' : ''}
  ''', [refreshExisting ? 1 : 0]);

  pixiv_helper.printAndLog(
      'info', 'Metadata refresh queue: ${rows.length} artwork(s).');
  var attempted = 0;
  var done = 0;
  var failed = 0;
  for (final row in rows) {
    if (_isStopRequested(caller)) {
      pixiv_helper.printAndLog(
          'warn', 'Stop requested; metadata refresh paused.');
      break;
    }
    final imageId = int.parse('${row['image_id']}');
    attempted++;
    try {
      pixiv_helper.printAndLog(
          null, 'Metadata $attempted/${rows.length}: $imageId');
      await processImageMetadata(
        caller: caller,
        config: config,
        imageId: imageId,
        notifier: notifier,
      );
      done++;
      await pixiv_helper.wait(pixiv_constant.PIXIVUTIL_OK, config);
    } catch (e) {
      failed++;
      pixiv_helper.printAndLog(
          'error', 'Failed metadata refresh for image $imageId: $e');
    }
  }
  pixiv_helper.printAndLog(
      'info', 'Metadata refresh completed: $done updated, $failed failed.');
}

Future<int> processUnlistedImage({
  required dynamic caller,
  required PixivConfig config,
  required String unlistedId,
  String titlePrefix = '',
  void Function({String? title, String? message, dynamic type})? notifier,
}) async {
  notifier ??= pixiv_helper.dummyNotifier;
  pixiv_helper.printAndLog(
      'info', 'Processing Unlisted Image: $unlistedId ($titlePrefix)');
  final br = caller.br as PixivBrowser;
  try {
    final (image, _) = await br.getUnlistedImagePage(
      unlistedId,
      writeRawJSON: config.writeRawJSON,
      stripHTMLTagsFromCaption: config.stripHTMLTagsFromCaption,
    );
    return processImage(
      caller: caller,
      config: config,
      artist: image.artist,
      imageId: image.imageId,
      titlePrefix: titlePrefix,
      notifier: notifier,
    );
  } on PixivException catch (e) {
    pixiv_helper.printAndLog('error', 'Unlisted image $unlistedId failed: $e');
    return e.errorCode == PixivException.IMAGE_DELETED
        ? pixiv_constant.PIXIVUTIL_SKIP_BLACKLIST
        : pixiv_constant.PIXIVUTIL_NOT_OK;
  }
}

Future<void> processMangaSeries({
  required dynamic caller,
  required PixivConfig config,
  required int mangaSeriesId,
  int startPage = 1,
  int endPage = 0,
  void Function({String? title, String? message, dynamic type})? notifier,
}) async {
  notifier ??= pixiv_helper.dummyNotifier;
  pixiv_helper.printAndLog(
      'info', 'Processing Manga Series Id: $mangaSeriesId');

  final br = caller.br as PixivBrowser;
  var currentPage = startPage;
  while (true) {
    final series = await br.getMangaSeries(mangaSeriesId, currentPage);
    series.printInfo();
    updateMangaSeriesMappingFromPage(caller, series);

    if (series.pagesWithOrder.isEmpty) {
      pixiv_helper.printAndLog('info', 'No more works.');
      break;
    }

    for (final work in series.pagesWithOrder) {
      if (_isStopRequested(caller)) {
        pixiv_helper.printAndLog(
            'warn', 'Stop requested; manga series download paused.');
        return;
      }
      final result = await processImage(
        caller: caller,
        config: config,
        artist: series.artist,
        imageId: work.imageId,
        mangaSeriesOrder: work.order,
        mangaSeriesParent: series,
        notifier: notifier,
      );
      await pixiv_helper.wait(result, config);
    }

    if (series.isLastPage) {
      pixiv_helper.printAndLog('info', 'Last Page ${series.currentPage}');
      break;
    }
    currentPage++;
    if (endPage > 0 && currentPage > endPage) {
      pixiv_helper.printAndLog('info', 'End Page reached $endPage');
      break;
    }
  }
}

Future<void> processMangaSeriesMetadata({
  required dynamic caller,
  required PixivConfig config,
  required int mangaSeriesId,
  void Function({String? title, String? message, dynamic type})? notifier,
}) async {
  notifier ??= pixiv_helper.dummyNotifier;
  pixiv_helper.printAndLog(
      'info', 'Processing Manga Series Metadata: $mangaSeriesId');
  final br = caller.br as PixivBrowser;
  var currentPage = 1;
  var totalWorks = 0;
  while (true) {
    final series = await br.getMangaSeries(mangaSeriesId, currentPage);
    updateMangaSeriesMappingFromPage(caller, series);
    totalWorks += series.pagesWithOrder.length;
    if (series.isLastPage || series.pagesWithOrder.isEmpty) break;
    currentPage++;
  }
  pixiv_helper.printAndLog(
      'info', 'Updated series $mangaSeriesId with $totalWorks works.');
}

void updateMangaSeriesMappingFromPage(dynamic caller, dynamic series) {
  caller.dbManager.insertSeries(
    '${series.mangaSeriesId}',
    series.title,
    type: 'manga',
    description: series.description,
  );
  for (final work in series.pagesWithOrder) {
    caller.dbManager.insertImageToSeries(
      '${series.mangaSeriesId}',
      work.order,
      work.imageId,
    );
  }
}

void _touchFiles(List<String> paths, DateTime worksDateDateTime) {
  // Best-effort: update downloaded file mtimes to the Pixiv works date.
  for (final path in paths) {
    final candidate = File(path);
    if (candidate.existsSync()) {
      try {
        candidate.setLastModifiedSync(worksDateDateTime);
      } catch (_) {}
    }
  }
}

bool _isStopRequested(dynamic caller) {
  try {
    return caller.stopRequested == true;
  } catch (_) {
    return false;
  }
}

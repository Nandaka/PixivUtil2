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

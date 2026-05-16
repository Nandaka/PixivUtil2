/// Bookmark handler.
library;

import 'dart:io';

import '../common/pixiv_browser.dart';
import '../common/pixiv_config.dart';
import '../common/pixiv_constant.dart' as pixiv_constant;
import '../common/pixiv_helper.dart' as pixiv_helper;
import 'pixiv_download_handler.dart' as download_handler;
import 'pixiv_image_handler.dart' as image_handler;

Future<void> processBookmark({
  required dynamic caller,
  required PixivConfig config,
  bool hide = false,
  int startPage = 1,
  int endPage = 0,
  String tag = '',
  String sortOrder = 'desc',
  void Function({String? title, String? message, dynamic type})? notifier,
}) async {
  notifier ??= pixiv_helper.dummyNotifier;
  pixiv_helper.printAndLog('info', 'Processing Bookmarks (hide=$hide).');
  final br = caller.br as PixivBrowser;

  var page = startPage;
  while (true) {
    pixiv_helper.printAndLog(null, 'Bookmarks - page $page');
    final pageData = await br.getNewIllustBookmark(page: page);
    if (!pageData.haveImages) break;
    var i = 1;
    for (final imageId in pageData.imageList) {
      try {
        pixiv_helper.printAndLog(null, '#$i - $imageId from bookmarks');
        final result = await image_handler.processImage(
            caller: caller,
            config: config,
            imageId: imageId,
            bookmark: true,
            notifier: notifier);
        await pixiv_helper.wait(result, config);
      } catch (e) {
        pixiv_helper.printAndLog('error', 'Failed bookmark image $imageId: $e');
      }
      i++;
    }
    page++;
    if (endPage > 0 && page > endPage) {
      pixiv_helper.printAndLog('info', 'Reached end_page = $endPage');
      break;
    }
  }
}

Future<void> processImageBookmark({
  required dynamic caller,
  required PixivConfig config,
  required int memberId,
  int startPage = 1,
  int endPage = 0,
  String? tags,
  String? sort,
  bool hide = false,
}) async {
  pixiv_helper.printAndLog('info', 'Processing image bookmarks for $memberId.');
  // The actual API endpoint is /ajax/user/{member_id}/illusts/bookmarks
  final br = caller.br as PixivBrowser;
  var offset = (startPage - 1) * 48;
  while (true) {
    final url =
        'https://www.pixiv.net/ajax/user/$memberId/illusts/bookmarks?tag=${tags ?? ''}&offset=$offset&limit=48&rest=${hide ? 'hide' : 'show'}';
    final body = await br.getContent(url);
    final (imageList, _) = _parseBookmarks(body, tags);
    if (imageList.isEmpty) break;
    for (final imageId in imageList) {
      try {
        await image_handler.processImage(
          caller: caller,
          config: config,
          imageId: imageId,
          bookmark: true,
        );
      } catch (e) {
        pixiv_helper.printAndLog('error', 'Failed bookmark image $imageId: $e');
      }
    }
    offset += 48;
    if (endPage > 0 && offset >= endPage * 48) break;
  }
}

Future<void> processFromGroup({
  required dynamic caller,
  required PixivConfig config,
  required String groupId,
  int limit = 0,
  bool processExternal = true,
}) async {
  final br = caller.br as PixivBrowser;
  pixiv_helper.printAndLog('info', 'Download by Group Id: $groupId');
  if (limit != 0) pixiv_helper.printAndLog('info', 'Limit: $limit');
  if (processExternal) {
    pixiv_helper.printAndLog(
        'info', 'Include External Image: $processExternal');
  }

  var maxId = 0;
  var imageCount = 0;
  while (true) {
    final group = await br.getGroupImages(groupId, maxId: maxId);
    maxId = group.maxId ?? 0;

    for (final imageId in group.imageList) {
      if (limit != 0 && imageCount >= limit) return;
      pixiv_helper.printAndLog(null, 'Image #$imageCount');
      pixiv_helper.printAndLog(null, 'ImageId: $imageId');
      final result = await image_handler.processImage(
        caller: caller,
        config: config,
        imageId: imageId,
      );
      imageCount++;
      await pixiv_helper.wait(result, config);
    }

    if (processExternal) {
      for (final image in group.externalImageList) {
        if (limit != 0 && imageCount >= limit) return;
        pixiv_helper.printAndLog(null, 'Image #$imageCount');
        pixiv_helper.printAndLog(
            null, 'Member Id    : ${image.artist?.artistId ?? 0}');
        pixiv_helper
            .safePrint('Member Name  : ${image.artist?.artistName ?? ''}');
        pixiv_helper.printAndLog(
            null, 'Member Token : ${image.artist?.artistToken ?? ''}');
        pixiv_helper.printAndLog(
            null, 'Image Url    : ${image.imageUrls.first}');

        final filename = pixiv_helper.makeFilename(
          config.filenameFormat,
          image,
          tagsSeparator: config.tagsSeparator,
          tagsLimit: config.tagsLimit,
          fileUrl: image.imageUrls.first,
          useTranslatedTag: config.useTranslatedTag,
          tagTranslationLocale: config.tagTranslationLocale,
        );
        final fullPath =
            pixiv_helper.sanitizeFilename(filename, config.rootDirectory);
        pixiv_helper.safePrint('Filename  : $fullPath');
        final result = await download_handler.downloadImage(
          caller: caller,
          config: config,
          url: image.imageUrls.first,
          filename: fullPath,
          referer: 'https://www.pixiv.net/group/$groupId',
        );
        if (config.setLastModified &&
            result == pixiv_constant.PIXIVUTIL_OK &&
            File(fullPath).existsSync()) {
          try {
            File(fullPath).setLastModifiedSync(image.worksDateDateTime);
          } catch (_) {}
        }
        imageCount++;
      }
    }

    if (group.imageList.isEmpty && group.externalImageList.isEmpty) break;
    if (maxId == 0) break;
  }
}

(List<int>, int) _parseBookmarks(String body, String? tag) {
  // Simple inline parser using PixivBookmark.parseImageBookmark would be
  // preferable, but we keep this small to avoid extra imports.
  final ids = RegExp(r'"id":"(\d+)"').allMatches(body);
  return (ids.map((m) => int.parse(m.group(1)!)).toList(), ids.length);
}

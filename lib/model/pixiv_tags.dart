/// PixivTags model: tag search results, tag list parsing, and tag info.
library;

import 'dart:convert';
import 'dart:io';

import '../common/pixiv_exception.dart';
import '../common/pixiv_helper.dart' as pixiv_helper;
import 'pixiv_artist.dart';

class PixivTagsItem {
  final int imageId;
  final int bookmarkCount;
  final int imageResponse;
  final int aiType;

  PixivTagsItem(this.imageId, this.bookmarkCount, this.imageResponse,
      [this.aiType = -1]);
}

class PixivTags {
  static const int POSTS_PER_PAGE = 60;

  List<PixivTagsItem>? itemList;
  bool? haveImage;
  bool? isLastPage;
  int availableImages = 0;
  String query = '';
  int memberId = 0;
  int page = -1;

  /// Process member result and return the image list.
  void parseMemberTags(PixivArtist artist, int memberId,
      {String query = ''}) {
    itemList = [];
    this.memberId = memberId;
    this.query = query;
    haveImage = artist.haveImages;
    isLastPage = artist.isLastPage;
    for (final image in artist.imageList) {
      itemList!.add(PixivTagsItem(image, 0, 0));
    }
  }

  /// Parse from search-by-tags page.
  List<PixivTagsItem> parseTags(String page,
      {String query = '', int currPage = 1}) {
    final payload = jsonDecode(page) as Map<String, dynamic>;
    this.query = query;
    this.page = currPage;
    if (payload['error'] == true) {
      throw PixivException(
        'Image Error: ${payload['message']}',
        errorCode: PixivException.SERVER_ERROR,
      );
    }
    itemList = [];
    int adContainerCount = 0;
    for (final item in payload['body']['illustManga']['data'] as List) {
      if (item is Map && item['isAdContainer'] == true) {
        adContainerCount++;
        continue;
      }
      final imageId = int.parse('${item['id']}');
      var aiType = -1;
      if (item['aiType'] != null) aiType = (item['aiType'] as num).toInt();
      itemList!.add(PixivTagsItem(imageId, 0, 0, aiType));
    }

    haveImage = itemList!.isNotEmpty;
    availableImages =
        (payload['body']['illustManga']['total'] as num).toInt();
    isLastPage =
        itemList!.length + adContainerCount != PixivTags.POSTS_PER_PAGE;
    return itemList!;
  }

  void printInfo() {
    pixiv_helper.safePrint('Search Result');
    if (memberId > 0) {
      pixiv_helper.safePrint('Member Id: $memberId');
    }
    pixiv_helper.safePrint('Query: $query');
    pixiv_helper.safePrint('haveImage  : $haveImage');
    pixiv_helper.safePrint('urls  : ${itemList?.length ?? 0}');
    if (itemList != null) {
      for (final item in itemList!) {
        print(
            '\tImage Id: ${item.imageId}\tFav Count:${item.bookmarkCount}');
      }
    }
    pixiv_helper.safePrint('total : $availableImages');
    pixiv_helper.safePrint('last? : $isLastPage');
  }

  /// Read tags.txt and return the list.
  static Future<List<String>> parseTagsList(String filename) async {
    if (!await File(filename).exists()) {
      throw PixivException(
        "File doesn't exists or no permission to read: $filename",
        errorCode: PixivException.FILE_NOT_EXISTS_OR_NO_PERMISSION,
      );
    }
    final lines = await pixiv_helper.openTextFileLines(filename);
    final tags = <String>[];
    for (final line in lines) {
      if (line.startsWith('#') || line.isEmpty) continue;
      final t = line.trim();
      if (t.isNotEmpty) tags.add(t);
    }
    return tags;
  }
}

class PixPediaInfo {
  final String abstract;
  final String image;
  final String id;
  final String tag;

  PixPediaInfo(Map<String, dynamic> payload)
      : abstract = (payload['abstract'] ?? '').toString(),
        image = (payload['image'] ?? '').toString(),
        id = (payload['id'] ?? '').toString(),
        tag = (payload['tag'] ?? '').toString();
}

/// AJAX response of `https://www.pixiv.net/ajax/search/tags/{tag_id}`.
class PixivTag {
  late String tag;
  late String word;
  PixPediaInfo? pixpedia;
  late List<String> myFavoriteTags;
  late Map<String, dynamic> tagTranslation;

  PixivTag(Map<String, dynamic>? payload) {
    if (payload == null) {
      throw PixivException('Tag payload is empty',
          errorCode: PixivException.OTHER_ERROR);
    }
    if (payload['error'] == true) {
      throw PixivException(
        (payload['message'] ?? 'Tag info error').toString(),
        errorCode: PixivException.OTHER_ERROR,
        htmlPage: payload,
      );
    }
    final body = payload['body'] as Map<String, dynamic>? ?? const {};
    tag = (body['tag'] ?? '').toString();
    word = (body['word'] ?? '').toString();
    final p = body['pixpedia'];
    pixpedia = (p is Map<String, dynamic>) ? PixPediaInfo(p) : null;
    myFavoriteTags =
        (body['myFavoriteTags'] as List? ?? const []).map((e) => '$e').toList();
    tagTranslation =
        (body['tagTranslation'] as Map<String, dynamic>? ?? {});
  }
}

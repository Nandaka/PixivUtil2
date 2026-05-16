/// PixivImage model: parses image pages, manga, and ugoira.
library;

import 'dart:convert';
import 'dart:io';

import 'package:html/parser.dart' as html_parser;

import '../common/datetime_z.dart' as datetime_z;
import '../common/pixiv_exception.dart';
import '../common/pixiv_helper.dart' as pixiv_helper;
import 'pixiv_artist.dart';

class PixivTagData {
  final String tag;
  String romaji;
  Map<String, dynamic>? translationData;

  PixivTagData(this.tag, dynamic tagNode)
      : romaji = (tagNode is Map && tagNode['romaji'] != null)
            ? '${tagNode['romaji']}'
            : tag.toLowerCase() {
    if (tagNode is Map && tagNode['translation'] is Map) {
      translationData =
          Map<String, dynamic>.from(tagNode['translation'] as Map);
    }
  }

  String getTranslation([String locale = 'en']) {
    if (translationData != null && translationData!.containsKey(locale)) {
      return '${translationData![locale]}';
    }
    return tag;
  }
}

class PixivImage {
  PixivArtist? artist;
  PixivArtist? originalArtist;
  int imageId;
  String imageTitle = '';
  String imageCaption = '';
  List<String> imageTags = [];
  String imageMode = '';
  List<String> imageUrls = [];
  List<String> imageResizedUrls = [];
  String worksDate = '';
  String worksResolution = '';
  Map<String, dynamic>? seriesNavData;
  dynamic rawJSON;
  int jd_rtv = 0;
  int jd_rtc = 0;
  int imageCount = 0;
  bool fromBookmark;
  DateTime worksDateDateTime = DateTime.fromMillisecondsSinceEpoch(0, isUtc: true);
  String? jsCreateDate;
  int bookmark_count;
  int image_response_count;
  String ugoira_data = '';
  String? dateFormat;
  List<String> descriptionUrlList = [];
  Duration? _tzInfo;
  List<PixivTagData> tags = [];
  bool stripHTMLTagsFromCaption;

  // Manga series
  int mangaSeriesOrder;
  PixivImage? mangaSeriesParent;

  // Title/caption translations
  String translatedWorkTitle = '';
  String translatedWorkCaption = '';

  // AI metadata: 1 == non-AI, 2 == AI-generated
  int ai_type = -1;

  PixivImage({
    int iid = 0,
    String? page,
    PixivArtist? parent,
    this.fromBookmark = false,
    this.bookmark_count = -1,
    this.image_response_count = -1,
    this.dateFormat,
    Duration? tzInfo,
    this.mangaSeriesOrder = -1,
    this.mangaSeriesParent,
    bool writeRawJSON = false,
    this.stripHTMLTagsFromCaption = false,
  })  : imageId = iid,
        artist = parent,
        _tzInfo = tzInfo {
    if (page != null) {
      final payloadRoot = jsonDecode(page) as Map<String, dynamic>?;
      if (payloadRoot == null) {
        throw PixivException(
          'Image Error: Cannot load image info from payload',
          errorCode: PixivException.SERVER_ERROR,
          htmlPage: page,
        );
      }
      if (payloadRoot['error'] == true) {
        throw PixivException(
          'Image Error: ${payloadRoot['message']}',
          errorCode: PixivException.SERVER_ERROR,
          htmlPage: page,
        );
      }
      final payload = payloadRoot['body'] as Map<String, dynamic>;
      if (payload['urls'] == null || payload['urls']['original'] == null) {
        throw PixivException(
          'Image Error: Unable to get the image urls, possibly not logged in.',
          errorCode: PixivException.NOT_LOGGED_IN,
          htmlPage: page,
        );
      }
      originalArtist ??= artist;
      parseInfo(payload, writeRawJSON);
    }
  }

  void parseInfo(Map<String, dynamic> page, bool writeRawJSON) {
    assert(int.parse('${page['illustId']}') == imageId);
    final root = page;
    if (writeRawJSON) rawJSON = root;

    imageUrls = [];
    imageResizedUrls = [];
    imageCount = (root['pageCount'] as num).toInt();
    final tempUrl = root['urls']['original'] as String;
    final tempResizedUrl = root['urls']['regular'] as String;
    if (imageCount == 1) {
      if (tempUrl.contains('ugoira')) {
        imageMode = 'ugoira_view';
        var tempUrlOri = tempUrl
            .replaceAll('/img-original/', '/img-zip-ugoira/')
            .split('_ugoira0')[0];
        tempUrlOri = '${tempUrlOri}_ugoira1920x1080.zip';
        imageUrls.add(tempUrlOri);

        var tempResizedOri = tempUrl
            .replaceAll('/img-original/', '/img-zip-ugoira/')
            .split('_ugoira0')[0];
        tempResizedOri = '${tempResizedOri}_ugoira600x600.zip';
        imageResizedUrls.add(tempResizedOri);
      } else {
        imageMode = 'big';
        imageUrls.add(tempUrl);
        imageResizedUrls.add(tempResizedUrl);
      }
    } else if (imageCount > 1) {
      imageMode = 'manga';
      for (var i = 0; i < imageCount; i++) {
        imageUrls.add(tempUrl.replaceAll('_p0', '_p$i'));
        imageResizedUrls.add(tempResizedUrl.replaceAll('_p0', '_p$i'));
      }
    }

    imageTitle = root['illustTitle'] as String? ?? '';
    imageCaption = root['illustComment'] as String? ?? '';
    seriesNavData = root['seriesNavData'] as Map<String, dynamic>?;
    jd_rtv = (root['viewCount'] as num? ?? 0).toInt();
    jd_rtc = (root['likeCount'] as num? ?? 0).toInt();

    imageTags = [];
    final tagsRoot = root['tags'];
    if (tagsRoot is Map && tagsRoot['tags'] is List) {
      for (final t in tagsRoot['tags'] as List) {
        imageTags.add('${t['tag']}');
        tags.add(PixivTagData('${t['tag']}', t));
      }
    }

    final created = root['createDate'] as String;
    worksDateDateTime =
        datetime_z.parseDatetime(created) ?? worksDateDateTime;
    jsCreateDate = created;
    if (_tzInfo != null) {
      worksDateDateTime = worksDateDateTime.add(_tzInfo!);
    }
    final fmt = dateFormat ?? '%Y-%m-%d';
    worksDate = pixiv_helper.strftime(fmt, worksDateDateTime);

    worksResolution = '${root['width']}x${root['height']}';
    if (imageCount > 1) {
      worksResolution = 'Multiple images: ${imageCount}P';
    }
    bookmark_count = (root['bookmarkCount'] as num? ?? 0).toInt();
    image_response_count = (root['responseCount'] as num? ?? 0).toInt();

    parseUrlFromCaption(imageCaption);
    if (stripHTMLTagsFromCaption) {
      imageCaption = html_parser.parse(imageCaption).body?.text ?? imageCaption;
    }

    final tct = root['titleCaptionTranslation'];
    if (tct is Map) {
      final wt = tct['workTitle'] as String?;
      final wc = tct['workCaption'] as String?;
      if (wt != null && wt.isNotEmpty) translatedWorkTitle = wt;
      if (wc != null && wc.isNotEmpty) {
        translatedWorkCaption = wc;
        parseUrlFromCaption(translatedWorkCaption);
        if (stripHTMLTagsFromCaption) {
          translatedWorkCaption =
              html_parser.parse(translatedWorkCaption).body?.text ??
                  translatedWorkCaption;
        }
      }
    }

    if (root['aiType'] != null) {
      ai_type = (root['aiType'] as num).toInt();
      if (ai_type == 2) imageTags.insert(0, 'AI-generated');
    }
  }

  void parseUrlFromCaption(String captionToParse) {
    final parsed = html_parser.parse(captionToParse);
    final links = parsed.querySelectorAll('a');
    for (final link in links) {
      var href = link.attributes['href'] ?? '';
      if (href.startsWith('/jump.php?')) {
        href = Uri.decodeFull(href.substring(10));
      }
      if (href.isNotEmpty && !descriptionUrlList.contains(href)) {
        descriptionUrlList.add(href);
      }
    }
  }

  String parseUgoira(String page) {
    final js = jsonDecode(page) as Map<String, dynamic>;
    imageCount = 1;
    final body = Map<String, dynamic>.from(js['body'] as Map);
    body['src'] = (body['src'] as String)
        .replaceAll('ugoira600x600.zip', 'ugoira1920x1080.zip');
    ugoira_data = jsonEncode(body);
    return body['src'] as String;
  }

  bool isNotLoggedIn(dynamic page) {
    if (page is! String) return false;
    return page.contains('signup_button') ||
        page.contains('ui-button _signup');
  }

  bool isNeedAppropriateLevel(dynamic page) {
    return pixiv_helper.haveStrings(page, ['該当作品の公開レベルにより閲覧できません。']);
  }

  bool isNeedPermission(dynamic page) {
    return pixiv_helper.haveStrings(page, [
      'この作品は.+さんのマイピクにのみ公開されています',
      'This work is viewable only for users who are in .+\'s My pixiv list',
      "Only .+'s My pixiv list can view this.",
      '<section class="restricted-content">',
    ]);
  }

  bool isDeleted(dynamic page) {
    return pixiv_helper.haveStrings(page, [
      '該当イラストは削除されたか、存在しないイラストIDです。|該当作品は削除されたか、存在しない作品IDです。',
      'この作品は削除されました。',
      'The following work is either deleted, or the ID does not exist.',
      'This work was deleted.',
      'Work has been deleted or the ID does not exist.',
    ]);
  }

  bool isGuroDisabled(dynamic page) {
    return pixiv_helper.haveStrings(page, [
      '表示されるページには、18歳未満の方には不適切な表現内容が含まれています。',
      'The page you are trying to access contains content that may be unsuitable for minors',
    ]);
  }

  void printInfo() {
    pixiv_helper.safePrint('Image Info');
    pixiv_helper.safePrint('img id: $imageId');
    pixiv_helper.safePrint('title : $imageTitle');
    pixiv_helper.safePrint('caption : $imageCaption');
    pixiv_helper.safePrint('mode  : $imageMode');
    pixiv_helper.safePrint('tags  : ${imageTags.join(', ')}');
    pixiv_helper.safePrint('views : $jd_rtv');
    pixiv_helper.safePrint('rating: $jd_rtc');
    pixiv_helper.safePrint('Date  : $worksDate');
    pixiv_helper.safePrint('Resolution : $worksResolution');
  }

  Future<void> writeInfo(String filename) async {
    await pixiv_helper.makeSubdirs(filename);
    final f = File(filename).openWrite(encoding: utf8);
    final aId = artist?.artistId ?? 0;
    final aName = artist?.artistName ?? '';
    f.writeln('ArtistID      = $aId');
    f.writeln('ArtistName    = $aName');
    f.writeln('ImageID       = $imageId');
    f.writeln('Title         = $imageTitle');
    if (seriesNavData != null) {
      f.writeln('SeriesTitle   = ${seriesNavData!['title']}');
      f.writeln('SeriesOrder   = ${seriesNavData!['order']}');
      f.writeln('SeriesId      = ${seriesNavData!['seriesId']}');
    }
    f.writeln('Caption       = $imageCaption');
    f.writeln('Tags          = ${imageTags.join(', ')}');
    f.writeln('Image Mode    = $imageMode');
    f.writeln('Pages         = $imageCount');
    f.writeln('Date          = $worksDate');
    f.writeln('Resolution    = $worksResolution');
    f.writeln('Total Views   = $jd_rtv');
    f.writeln('Total Rating  = $jd_rtc');
    f.writeln('Bookmark Count= $bookmark_count');
    f.writeln('Image Response= $image_response_count');
    if (descriptionUrlList.isNotEmpty) {
      f.writeln('Description URLs:');
      for (final u in descriptionUrlList) {
        f.writeln('  $u');
      }
    }
    await f.close();
  }

  Future<void> writeJson(String filename, {bool includeSeriesJson = false,
      String? seriesJson}) async {
    await pixiv_helper.makeSubdirs(filename);
    final out = <String, dynamic>{
      'imageId': imageId,
      'imageTitle': imageTitle,
      'imageCaption': imageCaption,
      'imageMode': imageMode,
      'imageUrls': imageUrls,
      'imageTags': imageTags,
      'imageCount': imageCount,
      'worksDate': worksDate,
      'worksResolution': worksResolution,
      'viewCount': jd_rtv,
      'likeCount': jd_rtc,
      'bookmarkCount': bookmark_count,
      'imageResponse': image_response_count,
      'aiType': ai_type,
      'translatedWorkTitle': translatedWorkTitle,
      'translatedWorkCaption': translatedWorkCaption,
      'descriptionUrlList': descriptionUrlList,
      'artist': {
        'artistId': artist?.artistId ?? 0,
        'artistName': artist?.artistName ?? '',
        'artistToken': artist?.artistToken ?? '',
      },
      if (rawJSON != null) 'rawJSON': rawJSON,
      if (includeSeriesJson && seriesJson != null) 'seriesJson': seriesJson,
    };
    await File(filename).writeAsString(jsonEncode(out));
  }
}

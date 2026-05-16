/// PixivNovel model.
library;

import 'dart:convert';
import 'dart:io';

import '../common/datetime_z.dart' as datetime_z;
import '../common/pixiv_exception.dart';
import '../common/pixiv_helper.dart' as pixiv_helper;
import 'pixiv_image.dart';

const int MAX_LIMIT = 10;

class PixivNovel {
  final int novelId;
  int get imageId => novelId;
  final String novelJsonStr;
  String content = '';

  // compatibility
  dynamic artist;
  int artistId = 0;
  String imageTitle = '';
  String worksDate = '';
  DateTime worksDateDateTime = DateTime.fromMillisecondsSinceEpoch(0, isUtc: true);
  List<String>? imageTags;
  List<PixivTagData>? tags;
  int bookmark_count = 0;
  int image_response_count = 0;

  // Series
  Map<String, dynamic>? seriesNavData;
  int seriesId = 0;
  int seriesOrder = 0;

  // Novel-specific
  bool isOriginal = false;
  bool isBungei = false;
  String language = '';
  bool xRestrict = false;
  DateTime uploadDate = DateTime.fromMillisecondsSinceEpoch(0, isUtc: true);

  String worksResolution = '';
  String imageMode = 'Novel';

  Duration? _tzInfo;
  String? dateFormat;
  String? jsCreateDate;

  PixivNovel(this.novelId, this.novelJsonStr,
      {Duration? tzInfo, this.dateFormat})
      : _tzInfo = tzInfo {
    parse();
  }

  void parse() {
    final js = jsonDecode(novelJsonStr) as Map<String, dynamic>;
    if (js['error'] == true) {
      throw PixivException(
        'Cannot get novel details',
        errorCode: PixivException.UNKNOWN_IMAGE_ERROR,
        htmlPage: novelJsonStr,
      );
    }
    final root = js['body'] as Map<String, dynamic>;
    imageTitle = '${root['title']}';
    content = '${root['content']}';
    artistId = int.parse('${root['userId']}');
    bookmark_count = (root['bookmarkCount'] as num? ?? 0).toInt();
    image_response_count = (root['imageResponseCount'] as num? ?? 0).toInt();
    seriesNavData = root['seriesNavData'] as Map<String, dynamic>?;
    if (seriesNavData != null) {
      seriesId = int.parse('${seriesNavData!['seriesId']}');
      seriesOrder = int.parse('${seriesNavData!['order']}');
    }
    isOriginal = root['isOriginal'] as bool? ?? false;
    isBungei = root['isBungei'] as bool? ?? false;
    language = root['language'] as String? ?? '';
    xRestrict = (root['xRestrict'] as bool?) ??
        ((root['xRestrict'] as num?)?.toInt() == 1);

    worksDateDateTime =
        datetime_z.parseDatetime(root['createDate'] as String) ?? worksDateDateTime;
    uploadDate =
        datetime_z.parseDatetime(root['uploadDate'] as String) ?? uploadDate;
    jsCreateDate = root['createDate'] as String?;
    if (_tzInfo != null) {
      worksDateDateTime = worksDateDateTime.add(_tzInfo!);
      uploadDate = uploadDate.add(_tzInfo!);
    }
    final fmt = dateFormat ?? '%Y-%m-%d';
    worksDate = pixiv_helper.strftime(fmt, worksDateDateTime);

    imageTags = [];
    tags = [];
    if (root['tags'] is Map && root['tags']['tags'] is List) {
      for (final tag in root['tags']['tags'] as List) {
        imageTags!.add('${tag['tag']}');
        tags!.add(PixivTagData('${tag['tag']}', tag));
      }
    }

    if (isOriginal) {
      imageTags!.add('オリジナル');
      final orig = {
        'tag': 'オリジナル',
        'romaji': 'original',
        'translation': {'en': 'original'},
      };
      tags!.add(PixivTagData(orig['tag'] as String, orig));
    }
  }

  Future<void> writeContent(String filename) async {
    final templateFile = File('novel_template.html');
    String template;
    try {
      template = await templateFile.readAsString();
    } catch (_) {
      template = '<html><body>%novel_json_str%</body></html>';
    }
    var contentStr = template.replaceAll('%title%', imageTitle);
    contentStr = contentStr.replaceAll('%novel_json_str%', novelJsonStr);
    try {
      await pixiv_helper.makeSubdirs(filename);
      await File(filename).writeAsString(contentStr);
    } on FileSystemException {
      await File('$novelId.html').writeAsString(contentStr);
    }
  }
}

class NovelSeries {
  final int seriesId;
  final String seriesStr;
  List<dynamic> seriesList = [];
  Map<int, String> seriesListStr = {};
  int total = 0;
  String seriesName = '';

  NovelSeries(this.seriesId, this.seriesStr) {
    parse();
  }

  void parse() {
    final js = jsonDecode(seriesStr) as Map<String, dynamic>;
    if (js['error'] == true) {
      throw PixivException(
        'Cannot get novel series content details',
        errorCode: PixivException.UNKNOWN_IMAGE_ERROR,
        htmlPage: seriesStr,
      );
    }
    total = (js['body']['total'] as num).toInt();
    seriesName = '${js['body']['title']}';
  }

  void parseSeriesContent(String pageInfo, int currentPage) {
    final js = jsonDecode(pageInfo) as Map<String, dynamic>;
    if (js['error'] == true) {
      throw PixivException(
        'Cannot get novel series content details',
        errorCode: PixivException.UNKNOWN_IMAGE_ERROR,
        htmlPage: pageInfo,
      );
    }
    seriesList.addAll(js['body']['page']['seriesContents'] as List);
    seriesListStr[currentPage] = pageInfo;
  }
}

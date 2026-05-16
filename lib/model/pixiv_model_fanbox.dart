/// Fanbox model: artist, post, and helpers.
library;

import 'dart:convert';
import 'dart:io';

import 'package:html/parser.dart' as html_parser;

import '../common/datetime_z.dart' as datetime_z;
import '../common/pixiv_exception.dart';
import '../common/pixiv_helper.dart' as pixiv_helper;

final RegExp _reFanboxCover = RegExp(r'c\/.*\/fanbox');
final RegExp _urlPattern = RegExp(
    r'(https?|ftp|file)://[-A-Za-z0-9+&@#/%?=~_|!:,.;]+[-A-Za-z0-9+&@#/%=~_|]');

class FanboxArtist {
  static const int SUPPORTING = 1;
  static const int FOLLOWING = 2;
  static const int CUSTOM = 3;

  int artistId = 0;
  String creatorId = '';
  String artistName = '';
  String artistToken = '';
  String coverImageUrl = '';
  bool hasNextPage = false;
  String? nextUrl;
  List<FanboxPost> posts = [];
  String? dateFormat;
  String fanbox_name = '';
  String description = '';
  String profileImageUrl = '';
  Duration? _tzInfo;

  FanboxArtist({
    this.artistId = 0,
    this.creatorId = '',
    String page = '',
    Duration? tzInfo,
    this.dateFormat,
  }) : _tzInfo = tzInfo {
    if (page.isNotEmpty) {
      final js = jsonDecode(page) as Map<String, dynamic>;
      _parseArtist(js['body'] ?? js);
    }
  }

  void _parseArtist(dynamic body) {
    if (body is Map) {
      if (body['user'] != null) {
        artistId = int.tryParse('${body['user']['userId']}') ?? 0;
        artistName = '${body['user']['name'] ?? ''}';
        profileImageUrl = '${body['user']['iconUrl'] ?? ''}';
      }
      if (body['creatorId'] != null) creatorId = '${body['creatorId']}';
      if (body['description'] != null) description = '${body['description']}';
      if (body['coverImageUrl'] != null) {
        coverImageUrl = '${body['coverImageUrl']}';
      }
    }
    fanbox_name = artistName;
  }

  void parsePosts(String page) {
    final js = jsonDecode(page) as Map<String, dynamic>;
    posts = [];
    final body = js['body'];
    final items = (body is Map && body['items'] is List)
        ? body['items'] as List
        : (body as List? ?? const []);
    for (final item in items) {
      final post = FanboxPost(
        int.parse('${(item as Map)['id']}'),
        this,
        item,
        tzInfo: _tzInfo,
      );
      posts.add(post);
    }
    if (body is Map && body['nextUrl'] != null) {
      nextUrl = '${body['nextUrl']}';
      hasNextPage = nextUrl != null && nextUrl!.isNotEmpty;
    } else {
      hasNextPage = false;
    }
  }

  @override
  String toString() =>
      'FanboxArtist($artistId, $artistName, $creatorId, ${posts.length})';
}

class FanboxPost {
  static const List<String> supportedTypes = [
    'image', 'text', 'file', 'article', 'video', 'entry'
  ];

  int imageId;
  String imageTitle = '';
  String coverImageUrl = '';
  String worksDate = '';
  DateTime? worksDateDateTime;
  String updatedDate = '';
  DateTime? updatedDateDatetime;
  String type = '';
  String body_text = '';
  List<String> images = [];
  int likeCount = 0;
  FanboxArtist? parent;
  bool isRestricted = false;
  int feeRequired = 0;

  String imageMode = '';
  int imageCount = 0;
  Duration? _tzInfo;

  Map<String, String>? linkToFile;

  String worksResolution = '';
  String worksTools = '';
  String searchTags = '';
  List<String> imageTags = [];
  int bookmark_count = 0;
  int image_response_count = 0;
  List<String>? embeddedFiles;
  String? provider;
  List<String>? descriptionUrlList;

  FanboxPost(this.imageId, this.parent, dynamic page, {Duration? tzInfo})
      : _tzInfo = tzInfo {
    embeddedFiles = [];
    descriptionUrlList = [];
    linkToFile = {};
    parsePost(page as Map<String, dynamic>);
    parsePostDetails(page);
  }

  void parsePostDetails(Map<String, dynamic> page) {
    if (!isRestricted && page.containsKey('body')) {
      parseBody(page);
      if (type == 'image') parseImages(page);
      if (type == 'file') parseFiles(page);
    }
    imageCount = images.length;
    if (imageCount > 0) imageMode = 'manga';
  }

  void parsePost(Map<String, dynamic> jsPost) {
    imageTitle = '${jsPost['title'] ?? ''}';
    String? coverUrl;
    if (jsPost['coverImageUrl'] != null) {
      coverUrl = '${jsPost['coverImageUrl']}';
    } else if (jsPost['cover'] is Map &&
        jsPost['cover']['type'] == 'cover_image') {
      coverUrl = '${jsPost['cover']['url']}';
    }
    if (coverImageUrl.isEmpty && coverUrl != null) {
      coverImageUrl = coverUrl.replaceAll(_reFanboxCover, 'fanbox');
      _tryAdd(coverUrl, embeddedFiles!);
    }
    worksDate = '${jsPost['publishedDatetime']}';
    worksDateDateTime = datetime_z.parseDatetime(worksDate);
    updatedDate = '${jsPost['updatedDatetime']}';
    updatedDateDatetime = datetime_z.parseDatetime(updatedDate);

    if (jsPost.containsKey('feeRequired')) {
      feeRequired = (jsPost['feeRequired'] as num).toInt();
    }
    if (_tzInfo != null && worksDateDateTime != null) {
      worksDateDateTime = worksDateDateTime!.add(_tzInfo!);
    }
    if (jsPost.containsKey('type')) {
      type = '${jsPost['type']}';
      if (!supportedTypes.contains(type)) {
        throw PixivException(
            'Unsupported post type = $type for post = $imageId',
            errorCode: 9999, htmlPage: jsPost);
      }
    } else {
      type = 'image';
    }
    likeCount = (jsPost['likeCount'] as num? ?? 0).toInt();

    if (jsPost['body'] == null) isRestricted = true;
    if (jsPost.containsKey('isRestricted')) {
      isRestricted = jsPost['isRestricted'] as bool;
    }
  }

  void parseBody(Map<String, dynamic> jsPost) {
    final body = jsPost['body'] as Map<String, dynamic>?;
    if (body == null) return;
    body_text = '';
    if (body['text'] != null) {
      body_text = '${body['text']}';
    } else if (body['html'] != null) {
      body_text = '${body['html']}';
      final parsed = html_parser.parse(body_text);
      for (final link in parsed.querySelectorAll('a')) {
        final href = link.attributes['href'] ?? '';
        if (href.contains('//fanbox.pixiv.net/images/entry/') ||
            href.contains('//downloads.fanbox.cc/')) {
          _tryAdd(href, embeddedFiles!);
        }
      }
    }
    if (body['blocks'] is List) {
      for (final block in body['blocks'] as List) {
        if (block is Map && block['text'] is String) {
          body_text += '${block['text']}\n';
        }
      }
    }
    final urlMatches = _urlPattern.allMatches(body_text);
    for (final m in urlMatches) {
      _tryAdd(m.group(0)!, descriptionUrlList!);
    }
  }

  void parseImages(Map<String, dynamic> jsPost) {
    final body = jsPost['body'] as Map<String, dynamic>?;
    if (body == null) return;
    final imgs = body['images'] as List? ?? const [];
    for (final img in imgs) {
      images.add('${img['originalUrl']}');
    }
  }

  void parseFiles(Map<String, dynamic> jsPost) {
    final body = jsPost['body'] as Map<String, dynamic>?;
    if (body == null) return;
    final files = body['files'] as List? ?? const [];
    for (final file in files) {
      final url = '${file['url']}';
      images.add(url);
      linkToFile?[url] = '${file['name']}.${file['extension']}';
    }
  }

  void _tryAdd(String url, List<String> bucket) {
    if (!bucket.contains(url)) bucket.add(url);
  }

  Future<void> writeInfo(String filename) async {
    await pixiv_helper.makeSubdirs(filename);
    final f = File(filename).openWrite(encoding: utf8);
    f.writeln('PostId        = $imageId');
    f.writeln('Title         = $imageTitle');
    f.writeln('Type          = $type');
    f.writeln('Date          = $worksDate');
    f.writeln('Updated       = $updatedDate');
    f.writeln('Like Count    = $likeCount');
    f.writeln('Fee Required  = $feeRequired');
    f.writeln('Body:');
    f.writeln(body_text);
    if ((descriptionUrlList ?? const []).isNotEmpty) {
      f.writeln('URLs:');
      for (final u in descriptionUrlList!) {
        f.writeln('  $u');
      }
    }
    await f.close();
  }

  @override
  String toString() {
    if (parent != null) {
      return 'FanboxPost($parent: $imageId, $imageTitle, $type, $feeRequired)';
    }
    return 'FanboxPost($imageId, $imageTitle, $type, $feeRequired)';
  }
}

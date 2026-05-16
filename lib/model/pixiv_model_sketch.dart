/// Pixiv Sketch model.
library;

import 'dart:convert';

import '../common/datetime_z.dart' as datetime_z;
import '../common/pixiv_helper.dart' as pixiv_helper;
import 'pixiv_image.dart';

class SketchArtist {
  int artistId = 0;
  int sketchArtistId = 0;
  String artistName = '';
  String artistAvatar = '';
  String artistToken = '';
  String artistBackground = '';
  List<SketchPost> posts = [];
  String? dateFormat;
  Duration? _tzInfo;
  String? nextPage;

  SketchArtist(int artistId, String? page,
      {Duration? tzInfo, String? dateFormat}) {
    this.dateFormat = dateFormat;
    _tzInfo = tzInfo;
    if (page != null) {
      final postJson = jsonDecode(page) as Map<String, dynamic>;
      parseArtist(postJson['data'] as Map<String, dynamic>);
    } else {
      this.artistId = artistId;
    }
  }

  void parseArtist(Map<String, dynamic> page) {
    Map<String, dynamic> root = page;
    if (page.containsKey('item')) {
      root = page['item']['user'] as Map<String, dynamic>;
    }
    if (root.containsKey('pixiv_user_id')) {
      artistId = (root['pixiv_user_id'] as num).toInt();
    } else {
      artistId = (root['id'] as num).toInt();
    }
    sketchArtistId = (root['id'] as num).toInt();
    artistName = '${root['name']}';
    artistToken = '${root['unique_name']}';
    artistAvatar = '${root['icon']['photo']['original']['url']}';
  }

  void parsePosts(String page) {
    final postJson = jsonDecode(page) as Map<String, dynamic>;
    final linksRoot = postJson['_links'] as Map<String, dynamic>?;
    if (linksRoot != null && linksRoot.containsKey('next')) {
      nextPage = '${linksRoot['next']['href']}';
    } else {
      nextPage = null;
    }
    for (final item in postJson['data']['items'] as List) {
      final postId = item['id'];
      final post = SketchPost(postId is num ? postId.toInt() : int.parse('$postId'),
          this, null, tzInfo: _tzInfo, dateFormat: dateFormat);
      post.parsePost(item as Map<String, dynamic>);
      post.artist = this;
      posts.add(post);
    }
  }

  @override
  String toString() =>
      'SketchArtist($artistId, $artistName, $artistToken, ${posts.length})';
}

class SketchPost {
  int imageId;
  String imageTitle = '';
  String imageCaption = '';
  List<String>? imageTags;
  List<PixivTagData>? tags;
  List<String> imageUrls = [];
  List<String> imageResizedUrls = [];
  String imageMode = '';
  String worksDate = '';
  DateTime? worksDateDateTime;
  String worksUpdateDate = '';
  DateTime? worksUpdateDateTime;

  SketchArtist? artist;
  String? dateFormat;
  Duration? _tzInfo;

  SketchArtist? originalArtist;
  String worksResolution = '';
  String worksTools = '';
  int jd_rtv = 0;
  int jd_rtc = 0;
  int imageCount = 0;
  bool fromBookmark = false;
  int bookmark_count = -1;
  int image_response_count = -1;

  SketchPost(this.imageId, this.artist, String? page,
      {Duration? tzInfo, this.dateFormat})
      : _tzInfo = tzInfo {
    if (page != null) {
      final postJson = jsonDecode(page) as Map<String, dynamic>;
      if (artist == null) {
        final artistId =
            (postJson['data']['item']['user']['id'] as num).toInt();
        this.artist =
            SketchArtist(artistId, page, tzInfo: tzInfo, dateFormat: dateFormat);
      }
      parsePost(postJson['data']['item'] as Map<String, dynamic>);
    }
  }

  void parsePost(Map<String, dynamic> page) {
    imageTitle = '${page['user']['name']}';
    imageCaption = '${page['text'] ?? ''}';
    imageTags = [];
    tags = [];
    for (final tag in page['tags'] as List) {
      imageTags!.add('$tag');
      tags!.add(PixivTagData('$tag', null));
    }
    if (page['is_r18'] == true) {
      imageTags!.add('R-18');
      tags!.add(PixivTagData('R-18', null));
    }
    for (final media in page['media'] as List) {
      imageMode = '${media['type']}';
      imageUrls.add('${media['photo']['original']['url']}');
      imageResizedUrls.add('${media['photo']['w540']['url']}');
    }
    worksDateDateTime =
        datetime_z.parseDatetime('${page['published_at']}');
    worksUpdateDateTime =
        datetime_z.parseDatetime('${page['updated_at']}');
    if (_tzInfo != null && worksDateDateTime != null) {
      worksDateDateTime = worksDateDateTime!.add(_tzInfo!);
    }
    if (_tzInfo != null && worksUpdateDateTime != null) {
      worksUpdateDateTime = worksUpdateDateTime!.add(_tzInfo!);
    }
    final fmt = dateFormat ?? '%Y-%m-%d';
    if (worksDateDateTime != null) {
      worksDate = pixiv_helper.strftime(fmt, worksDateDateTime!);
    }
    if (worksUpdateDateTime != null) {
      worksUpdateDate =
          pixiv_helper.strftime(fmt, worksUpdateDateTime!);
    }
    imageCount = imageUrls.length;
  }

  @override
  String toString() {
    final firstUrl = imageUrls.isNotEmpty ? imageUrls.first : '';
    if (artist != null) {
      return 'SketchPost($artist: $imageId, $imageTitle, $imageMode, $firstUrl)';
    }
    return 'SketchPost($imageId, $imageTitle, $imageMode, $firstUrl)';
  }
}

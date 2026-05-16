/// PixivGroup model: groups (ngroups) parsing.
library;

import 'dart:convert';

import 'pixiv_artist.dart';
import 'pixiv_image.dart';

class PixivGroup {
  static final RegExp shortPattern = RegExp(
      r'https?://www\.pixiv\.net/member_illust\.php\?mode=(.*)&illust_id=(\d+)');

  int? maxId;
  List<int> imageList = [];
  List<PixivImage> externalImageList = [];

  PixivGroup(String jsonResponse) {
    final data = jsonDecode(jsonResponse) as Map<String, dynamic>;
    maxId = int.tryParse('${data['max_id'] ?? 0}');
    for (final imageData in data['imageArticles'] as List? ?? const []) {
      final detail = imageData['detail'] as Map<String, dynamic>;
      if (detail.containsKey('id')) {
        imageList.add(int.parse('${detail['id']}'));
      } else if (detail.containsKey('fullscale_url')) {
        final fullscaleUrl = detail['fullscale_url'] as String;
        final memberId = PixivArtist();
        memberId.artistId = int.tryParse('${imageData['user_id']}') ?? 0;
        if (imageData['user_name'] != null) {
          memberId.artistName = '${imageData['user_name']}';
          memberId.artistAvatar = parseAvatar(imageData['img'] as String);
          memberId.artistToken = parseToken(imageData['img'] as String) ?? '';
        } else {
          memberId.artistName = '${imageData['user_id']}';
          memberId.artistAvatar = '';
          memberId.artistToken = '';
        }

        final imageDataModel = PixivImage();
        imageDataModel.artist = memberId;
        imageDataModel.originalArtist = memberId;
        imageDataModel.imageId = 0;
        imageDataModel.imageTitle =
            shortenPixivUrlInBody(imageData['body'] as String? ?? '');
        imageDataModel.imageCaption =
            shortenPixivUrlInBody(imageData['body'] as String? ?? '');
        imageDataModel.imageTags = [];
        imageDataModel.imageMode = '';
        imageDataModel.imageUrls = [fullscaleUrl];
        imageDataModel.worksDate = imageData['create_time'] as String? ?? '';
        imageDataModel.worksResolution = '';
        imageDataModel.jd_rtv = 0;
        imageDataModel.jd_rtc = 0;
        imageDataModel.imageCount = 0;
        imageDataModel.fromBookmark = false;

        try {
          imageDataModel.worksDateDateTime =
              DateTime.parse(imageDataModel.worksDate);
        } catch (_) {}

        externalImageList.add(imageDataModel);
      }
    }
  }

  static String parseAvatar(String url) => url.replaceAll('_s', '');

  static String? parseToken(String url) {
    final parts = url.split('/');
    if (parts.length >= 2) {
      final token = parts[parts.length - 2];
      if (token != 'Common') return token;
    }
    return null;
  }

  String shortenPixivUrlInBody(String s) {
    var shortened = '';
    final m = shortPattern.firstMatch(s);
    if (m != null) {
      if (m.group(1) == 'medium') {
        shortened = 'Illust=${m.group(2)}';
      } else {
        shortened = 'Manga=${m.group(2)}';
      }
    }
    var out = s.replaceAll(shortPattern, '').trim();
    out = '$out $shortened';
    return out;
  }
}

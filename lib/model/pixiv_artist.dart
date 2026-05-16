/// PixivArtist model: parses member pages.
library;

import 'dart:convert';

import '../common/pixiv_exception.dart';

class PixivArtist {
  int artistId;
  String artistName = '';
  String artistAvatar = '';
  String artistToken = '';
  String artistBackground = '';
  List<int> imageList = [];
  bool? isLastPage;
  bool? haveImages;
  int totalImages = 0;
  int offset;
  int limit;
  int referenceImageId = 0;
  List<int> mangaSeries = [];
  List<int> novelSeries = [];

  PixivArtist({
    this.artistId = 0,
    String page = '',
    bool fromImage = false,
    this.offset = -1,
    this.limit = -1,
  }) {
    if (page.isNotEmpty) {
      Map<String, dynamic> payload;
      if (!fromImage) {
        payload = jsonDecode(page) as Map<String, dynamic>;
        if (payload['error'] == true) {
          throw PixivException(
            payload['message']?.toString() ?? '',
            errorCode: PixivException.OTHER_MEMBER_ERROR,
            htmlPage: page,
          );
        }
        if (payload['body'] == null) {
          throw PixivException(
            "Missing body content, possible artist id doesn't exist.",
            errorCode: PixivException.USER_ID_NOT_EXISTS,
            htmlPage: page,
          );
        }
        parseImages(payload['body'] as Map<String, dynamic>);
        parseMangaList(payload['body'] as Map<String, dynamic>);
        parseNovelList(payload['body'] as Map<String, dynamic>);
        parseInfo(payload['body'], false);
      } else {
        payload = jsonDecode(page) as Map<String, dynamic>;
        isLastPage = true;
        haveImages = true;
        parseInfo(payload, true);
      }
    }
  }

  void parseMangaList(Map<String, dynamic>? payload) {
    if (payload == null || !payload.containsKey('mangaSeries')) return;
    final list = payload['mangaSeries'] as List? ?? const [];
    for (final m in list) {
      mangaSeries.add(int.parse('${m['id']}'));
    }
  }

  void parseNovelList(Map<String, dynamic>? payload) {
    if (payload == null || !payload.containsKey('novelSeries')) return;
    final list = payload['novelSeries'] as List? ?? const [];
    for (final n in list) {
      novelSeries.add(int.parse('${n['id']}'));
    }
  }

  /// Parse `artistId, artistAvatar, artistToken, artistName, artistBackground`.
  void parseInfo(dynamic page, bool fromImage, {bool bookmark = false}) {
    artistId = 0;
    artistAvatar = 'no_profile';
    artistToken = 'self';
    artistName = 'self';
    artistBackground = 'no_background';

    if (page == null) return;
    if (fromImage) {
      parseInfoFromImage(page as Map<String, dynamic>);
      return;
    }

    final body = page['body'];
    if (body is Map &&
        body['illust'] != null &&
        (body['illust'] as Map).isNotEmpty) {
      final root = body['illust'] as Map;
      artistId = (root['illust_user_id'] as num).toInt();
      artistToken = '${root['user_account']}';
      artistName = '${root['user_name']}';
    } else if (body is Map &&
        body['novel'] != null &&
        (body['novel'] as Map).isNotEmpty) {
      final root = body['novel'] as Map;
      artistId = (root['user_id'] as num).toInt();
      artistToken = '${root['user_account']}';
      artistName = '${root['user_name']}';
    } else {
      Map? data;
      if (page['user'] != null) {
        data = page as Map;
      } else if (page['illusts'] is List &&
          (page['illusts'] as List).isNotEmpty &&
          (page['illusts'] as List).first is Map) {
        data = (page['illusts'] as List).first as Map;
      }
      if (data != null) {
        artistId = (data['user']['id'] as num).toInt();
        artistToken = '${data['user']['account']}';
        artistName = '${data['user']['name']}';
        final avatarData = data['user']['profile_image_urls'] as Map?;
        if (avatarData != null && avatarData.containsKey('medium')) {
          artistAvatar = (avatarData['medium'] as String).replaceAll('_170', '');
        }
      }
    }

    if (page['profile'] is Map) {
      final profile = page['profile'] as Map;
      if (totalImages == 0) {
        if (bookmark) {
          totalImages =
              int.parse('${profile['total_illust_bookmarks_public']}');
        } else {
          totalImages = int.parse('${profile['total_illusts']}') +
              int.parse('${profile['total_manga']}');
        }
      }
      final bg = profile['background_image_url'] as String?;
      if (bg != null && bg.startsWith('http')) {
        artistBackground = bg;
      }
    }
  }

  void parseInfoFromImage(Map<String, dynamic> page) {
    artistId = (page['userId'] is String)
        ? int.parse(page['userId'] as String)
        : (page['userId'] as num).toInt();
    artistAvatar =
        (page['image'] as String).replaceAll('_50.', '.').replaceAll('_170.', '.');
    artistName = '${page['name']}';

    final bg = page['background'];
    if (bg is Map && bg['url'] != null) {
      artistBackground = '${bg['url']}';
    }

    final illusts = page['illust'] as Map? ?? const {};
    for (final il in illusts.values) {
      if (il is Map && il['userAccount'] != null) {
        artistToken = '${il['userAccount']}';
        break;
      }
    }
  }

  void parseBackground(Map<String, dynamic> payload) {
    if (payload['body'] is! Map) return;
    final root = payload['body'] as Map;
    artistId = (root['userId'] as num).toInt();
    artistName = '${root['name']}';
    if (root['imageBig'] != null) {
      artistAvatar =
          (root['imageBig'] as String).replaceAll('_50.', '.').replaceAll('_170.', '.');
    } else if (root['image'] != null) {
      artistAvatar =
          (root['image'] as String).replaceAll('_50.', '.').replaceAll('_170.', '.');
    }
    if (root['background'] is Map && root['background']['url'] != null) {
      artistBackground = '${root['background']['url']}';
    }
  }

  /// Parse the list of images from an /ajax/ response payload.
  void parseImages(Map<String, dynamic> payload) {
    imageList.clear();
    if (payload['works'] is List) {
      for (final image in payload['works'] as List) {
        imageList.add(int.parse('${image['id']}'));
      }
      totalImages = int.parse('${payload['total']}');
      haveImages = imageList.isNotEmpty;
      assert(offset >= 0);
      isLastPage = imageList.length + offset == totalImages;
      return;
    }

    void absorb(dynamic group) {
      if (group is List) {
        for (final image in group) {
          imageList.add(int.parse('$image'));
        }
      } else if (group is Map) {
        // /ajax/user/<id>/profile/all returns a Map<imageId, null>.
        for (final id in group.keys) {
          imageList.add(int.parse('$id'));
        }
      }
    }

    absorb(payload['illusts']);
    absorb(payload['manga']);
    imageList.sort((a, b) => b.compareTo(a));
    totalImages = imageList.length;
    assert(offset >= 0);
    assert(limit >= 0);
    isLastPage = offset + limit >= totalImages;
    haveImages = imageList.isNotEmpty;
  }

  void printInfo() {
    print('Artist Info');
    print('id    : $artistId');
    print('name  : $artistName');
    print('avatar: $artistAvatar');
    print('token : $artistToken');
    print('urls  : ${imageList.length}');
    for (final item in imageList) {
      print('\t$item');
    }
    print('total : $totalImages');
    print('last? : $isLastPage');
  }
}

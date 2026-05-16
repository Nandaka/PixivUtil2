import 'dart:convert';

import 'package:pixiv_util2/model/pixiv_artist.dart';
import 'package:pixiv_util2/model/pixiv_image.dart';
import 'package:pixiv_util2/model/pixiv_list_item.dart';
import 'package:test/test.dart';

void main() {
  group('PixivArtist', () {
    test('default constructor', () {
      final a = PixivArtist();
      expect(a.artistId, 0);
      expect(a.imageList, isEmpty);
    });

    test('parses ajax /profile/all response', () {
      // /ajax/user/<id>/profile/all returns illusts as {imageId: null}.
      final json = jsonEncode({
        'error': false,
        'message': '',
        'body': {
          'illusts': {'12345': null, '12346': null},
          'manga': const <String, dynamic>{},
          'mangaSeries': const <Map<String, dynamic>>[],
          'novelSeries': const <Map<String, dynamic>>[],
        }
      });
      final a = PixivArtist(
        artistId: 1,
        page: json,
        offset: 0,
        limit: 60,
      );
      expect(a.imageList.length, 2);
      expect(a.haveImages, true);
    });
  });

  group('PixivTagData', () {
    test('falls back to lowercase tag for romaji', () {
      final t = PixivTagData('Hello', null);
      expect(t.romaji, 'hello');
    });

    test('translation lookup', () {
      final t = PixivTagData('オリジナル', {
        'romaji': 'original',
        'translation': {'en': 'original'}
      });
      expect(t.getTranslation('en'), 'original');
      expect(t.getTranslation('xx'), 'オリジナル');
    });
  });

  group('PixivListItem', () {
    test('parses memberId and path', () {
      final item = PixivListItem(123, 'foo/bar');
      expect(item.memberId, 123);
      expect(item.path, 'foo/bar');
    });
    test('treats N\\A as empty', () {
      final item = PixivListItem(123, r'N\A');
      expect(item.path, '');
    });
  });
}

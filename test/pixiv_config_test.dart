import 'dart:io';

import 'package:pixiv_util2/common/pixiv_config.dart';
import 'package:test/test.dart';

void main() {
  group('PixivConfig defaults', () {
    test('save artwork files into image-id folder without text info', () {
      final config = PixivConfig();
      final artworkFolder = '%image_id%${Platform.pathSeparator}';

      expect(config.writeImageInfo, isFalse);
      expect(config.filenameFormat, contains(artworkFolder));
      expect(config.filenameMangaFormat, contains(artworkFolder));
      expect(config.filenameInfoFormat, endsWith('${artworkFolder}info'));
      expect(config.filenameMangaInfoFormat, endsWith('${artworkFolder}info'));
    });
  });
}

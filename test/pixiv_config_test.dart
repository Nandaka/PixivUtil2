import 'dart:io';

import 'package:pixiv_util2/common/pixiv_config.dart';
import 'package:test/test.dart';

void main() {
  group('PixivConfig defaults', () {
    test('save artwork files and info into one folder per artwork', () {
      final config = PixivConfig();
      final artworkFolder = '%image_id% - %title%${Platform.pathSeparator}';

      expect(config.writeImageInfo, isTrue);
      expect(config.filenameFormat, contains(artworkFolder));
      expect(config.filenameMangaFormat, contains(artworkFolder));
      expect(config.filenameInfoFormat, endsWith('${artworkFolder}info'));
      expect(config.filenameMangaInfoFormat, endsWith('${artworkFolder}info'));
    });
  });
}

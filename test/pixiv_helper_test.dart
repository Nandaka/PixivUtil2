import 'package:pixiv_util2/common/pixiv_helper.dart' as pixiv_helper;
import 'package:test/test.dart';

void main() {
  group('sanitizeFilename', () {
    test('replaces bad characters on windows-style paths', () {
      // On non-Windows systems this returns the input mostly intact.
      final result = pixiv_helper.sanitizeFilename('hello world.png');
      expect(result, contains('hello world'));
    });

    test('html entities are unescaped', () {
      final result = pixiv_helper.sanitizeFilename("it&#039;s fine.png");
      expect(result, contains("it's fine"));
    });
  });

  group('replacePathSeparator', () {
    test('replaces both / and \\\\', () {
      expect(pixiv_helper.replacePathSeparator('a/b\\c'), 'a_b_c');
    });
  });

  group('calculateGroup', () {
    test('returns expected group for 100, 250, 500, 1000', () {
      expect(pixiv_helper.calculateGroup(50), '');
      expect(pixiv_helper.calculateGroup(100), '100');
      expect(pixiv_helper.calculateGroup(250), '250');
      expect(pixiv_helper.calculateGroup(500), '500');
      expect(pixiv_helper.calculateGroup(1000), '1000');
      expect(pixiv_helper.calculateGroup(5000), '5000');
      expect(pixiv_helper.calculateGroup(99999), '10000');
    });
  });

  group('sizeInStr', () {
    test('formats bytes', () {
      expect(pixiv_helper.sizeInStr(500), '500 B');
      expect(pixiv_helper.sizeInStr(2048), '2.00 KiB');
      expect(pixiv_helper.sizeInStr(1024 * 1024 * 5), '5.00 MiB');
    });
  });

  group('strftime', () {
    test('formats date', () {
      final dt = DateTime(2024, 6, 15, 10, 30, 45);
      expect(pixiv_helper.strftime('%Y-%m-%d', dt), '2024-06-15');
      expect(pixiv_helper.strftime('%Y%m%d', dt), '20240615');
    });
  });
}

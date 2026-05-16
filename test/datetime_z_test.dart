import 'package:pixiv_util2/common/datetime_z.dart' as datetime_z;
import 'package:test/test.dart';

void main() {
  group('parseDate', () {
    test('parses YYYY-MM-DD', () {
      final dt = datetime_z.parseDate('2025-01-31');
      expect(dt, isNotNull);
      expect(dt!.year, 2025);
      expect(dt.month, 1);
      expect(dt.day, 31);
    });
    test('returns null for invalid input', () {
      expect(datetime_z.parseDate('not a date'), isNull);
    });
  });

  group('parseDatetime', () {
    test('parses ISO timestamp with Z', () {
      final dt = datetime_z.parseDatetime('2018-06-08T15:00:04Z');
      expect(dt, isNotNull);
      expect(dt!.isUtc, true);
      expect(dt.year, 2018);
      expect(dt.hour, 15);
    });
    test('parses ISO with timezone offset', () {
      final dt = datetime_z.parseDatetime('2018-06-08T15:00:04+09:00');
      expect(dt, isNotNull);
      expect(dt!.isUtc, true);
      // 15:00 +09:00 == 06:00 UTC
      expect(dt.hour, 6);
    });
  });

  group('parseDuration', () {
    test('parses standard format', () {
      final d = datetime_z.parseDuration('1 days, 02:30:15');
      expect(d, isNotNull);
      expect(d!.inHours, 26);
      expect(d.inMinutes, 26 * 60 + 30);
    });
    test('parses ISO 8601', () {
      final d = datetime_z.parseDuration('PT1H30M');
      expect(d, isNotNull);
      expect(d!.inMinutes, 90);
    });
  });
}

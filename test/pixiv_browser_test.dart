import 'package:pixiv_util2/common/pixiv_browser.dart';
import 'package:test/test.dart';

void main() {
  group('PixivBrowser cookie parsing', () {
    test('accepts browser Cookie header format', () {
      expect(
        PixivBrowser.parseCookieHeader('Cookie: PHPSESSID=abc; user=123'),
        {'PHPSESSID': 'abc', 'user': '123'},
      );
    });

    test('ignores Set-Cookie attributes when pasted into config', () {
      expect(
        PixivBrowser.parseCookieHeader(
          'PHPSESSID=abc; Path=/; Domain=.pixiv.net; Secure; HttpOnly',
        ),
        {'PHPSESSID': 'abc'},
      );
    });
  });
}

import 'dart:io';

import 'package:path/path.dart' as p;
import 'package:pixiv_util2/pixiv_db_manager.dart';
import 'package:test/test.dart';

void main() {
  group('PixivDBManager download metadata', () {
    test('stores requested artwork fields and limits tags to ten', () {
      final tempDir = Directory.systemTemp.createTempSync('pixiv-db-test-');
      try {
        final db = PixivDBManager(
          rootDirectory: tempDir.path,
          target: p.join(tempDir.path, 'db.sqlite'),
        );
        db.createDatabase();

        db.insertDownloadMetadata(
          imageId: 130952072,
          title: 'title',
          caption: 'caption',
          tags: List.generate(12, (i) => 'tag$i'),
          pages: 2,
          worksDate: '2025-05-29',
          totalViews: 35675,
          totalRating: 2963,
          bookmarkCount: 1234,
        );

        final row = db.selectDownloadMetadata(130952072)!;
        expect(row['image_id'], 130952072);
        expect(row['title'], 'title');
        expect(row['caption'], 'caption');
        expect(row['tags'],
            'tag0, tag1, tag2, tag3, tag4, tag5, tag6, tag7, tag8, tag9');
        expect(row['pages'], 2);
        expect(row['works_date'], '2025-05-29');
        expect(row['total_views'], 35675);
        expect(row['total_rating'], 2963);
        expect(row['bookmark_count'], 1234);

        db.close();
      } finally {
        tempDir.deleteSync(recursive: true);
      }
    });
  });
}

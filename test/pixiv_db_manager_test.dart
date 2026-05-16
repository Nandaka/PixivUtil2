import 'dart:io';

import 'package:path/path.dart' as p;
import 'package:pixiv_util2/pixiv_db_manager.dart';
import 'package:sqlite3/sqlite3.dart';
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

  group('PixivDBManager PixivUtil2 metadata import', () {
    test('imports upstream DB rows without replacing existing metadata', () {
      final tempDir = Directory.systemTemp.createTempSync('pixiv-db-import-');
      Database? source;
      PixivDBManager? target;
      try {
        final sourcePath = p.join(tempDir.path, 'old-pixivutil2.sqlite');
        source = sqlite3.open(sourcePath);
        source.execute('''
          CREATE TABLE pixiv_master_member (
            member_id INTEGER PRIMARY KEY ON CONFLICT IGNORE,
            name TEXT,
            save_folder TEXT,
            created_date DATE,
            last_update_date DATE,
            last_image INTEGER,
            is_deleted INTEGER DEFAULT 0,
            member_token TEXT
          )
        ''');
        source.execute('''
          CREATE TABLE pixiv_master_image (
            image_id INTEGER PRIMARY KEY,
            member_id INTEGER,
            title TEXT,
            save_name TEXT,
            created_date DATE,
            last_update_date DATE,
            is_manga TEXT,
            caption TEXT
          )
        ''');
        source.execute('''
          CREATE TABLE pixiv_master_tag (
            tag_id VARCHAR(255) PRIMARY KEY,
            created_date DATE,
            last_update_date DATE
          )
        ''');
        source.execute('''
          CREATE TABLE pixiv_image_to_tag (
            image_id INTEGER,
            tag_id VARCHAR(255),
            created_date DATE,
            last_update_date DATE,
            PRIMARY KEY (image_id, tag_id)
          )
        ''');
        source.execute('''
          CREATE TABLE novel_detail (
            post_id INTEGER,
            user_id INTEGER,
            save_name TEXT,
            created_date DATE,
            last_update_date DATE,
            is_original INTEGER,
            is_bungei INTEGER,
            language TEXT,
            x_restrict INTEGER,
            series_id INTEGER,
            series_order INTEGER,
            PRIMARY KEY (post_id, user_id)
          )
        ''');
        source.execute(
          'INSERT INTO pixiv_master_member VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
          [
            123,
            'Old Artist',
            'old-folder',
            '2024-01-01',
            '2024-01-02',
            456,
            0,
            'oldtoken'
          ],
        );
        source.execute(
          'INSERT INTO pixiv_master_image VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
          [
            456,
            123,
            'Old Title',
            'old-file.jpg',
            '2024-01-01',
            '2024-01-02',
            'N',
            'Old caption'
          ],
        );
        source.execute(
          'INSERT INTO pixiv_master_tag VALUES (?, ?, ?)',
          ['tag-a', '2024-01-01', '2024-01-02'],
        );
        source.execute(
          'INSERT INTO pixiv_image_to_tag VALUES (?, ?, ?, ?)',
          [456, 'tag-a', '2024-01-01', '2024-01-02'],
        );
        source.execute(
          'INSERT INTO novel_detail VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
          [
            789,
            123,
            'novel.html',
            '2024-01-01',
            '2024-01-02',
            1,
            0,
            'ja',
            0,
            42,
            1
          ],
        );
        source.dispose();
        source = null;

        target = PixivDBManager(
          rootDirectory: tempDir.path,
          target: p.join(tempDir.path, 'target.sqlite'),
        );
        target.createDatabase();
        target.insertImage(
          456,
          999,
          title: 'Keep Current Title',
          saveName: 'current.jpg',
          caption: '',
        );

        final stats = target.importMetadataFromPixivUtilDb(sourcePath);

        expect(stats.importedByTable['pixiv_master_member'], 1);
        expect(stats.importedByTable['pixiv_master_image'], 1);
        expect(stats.importedByTable['pixiv_master_tag'], 1);
        expect(stats.importedByTable['pixiv_image_to_tag'], 1);
        expect(stats.importedByTable['novel_detail'], 1);
        expect(stats.skippedTables['pixiv_download_metadata'],
            'missing in source');

        final member = target.selectMemberByMemberId(123)!;
        expect(member.name, 'Old Artist');
        expect(member.memberToken, 'oldtoken');

        final image = target.selectImageByImageId(456)!;
        expect(image['title'], 'Keep Current Title');
        expect(image['member_id'], 999);
        expect(image['caption'], 'Old caption');

        final novelRows =
            target.raw.select('SELECT * FROM novel_detail WHERE post_id = 789');
        expect(novelRows, hasLength(1));
        expect(novelRows.first['language'], 'ja');
      } finally {
        source?.dispose();
        target?.close();
        tempDir.deleteSync(recursive: true);
      }
    });
  });
}

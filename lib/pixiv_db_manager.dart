/// PixivUtil database manager (SQLite-backed).
library;

import 'dart:io';

import 'package:path/path.dart' as p;
import 'package:sqlite3/sqlite3.dart';

import 'common/pixiv_helper.dart' as pixiv_helper;
import 'model/pixiv_list_item.dart';

class PixivMemberRow {
  final int memberId;
  String name;
  String saveFolder;
  DateTime? createdDate;
  DateTime? lastUpdateDate;
  int lastImage;
  int isDeleted;
  String memberToken;

  PixivMemberRow({
    required this.memberId,
    this.name = '',
    this.saveFolder = '',
    this.createdDate,
    this.lastUpdateDate,
    this.lastImage = 0,
    this.isDeleted = 0,
    this.memberToken = '',
  });

  factory PixivMemberRow.fromRow(Row r) => PixivMemberRow(
        memberId: r['member_id'] as int,
        name: r['name']?.toString() ?? '',
        saveFolder: r['save_folder']?.toString() ?? '',
        createdDate: _parseDate(r['created_date']),
        lastUpdateDate: _parseDate(r['last_update_date']),
        lastImage: (r['last_image'] as int?) ?? 0,
        isDeleted: (r['is_deleted'] as int?) ?? 0,
        memberToken: r['member_token']?.toString() ?? '',
      );
}

class PixivDbImportStats {
  final Map<String, int> importedByTable = {};
  final Map<String, String> skippedTables = {};

  int get totalImported =>
      importedByTable.values.fold(0, (sum, count) => sum + count);

  @override
  String toString() {
    final parts = <String>['Imported $totalImported metadata rows.'];
    for (final entry in importedByTable.entries) {
      parts.add('  ${entry.key}: ${entry.value}');
    }
    if (skippedTables.isNotEmpty) {
      parts.add('Skipped tables:');
      for (final entry in skippedTables.entries) {
        parts.add('  ${entry.key}: ${entry.value}');
      }
    }
    return parts.join('\n');
  }
}

class PixivDbRepairReport {
  final bool integrityOk;
  final List<String> integrityMessages;
  final int imageRows;
  final int missingMetadataRows;
  final int incompleteMetadataRows;
  final int orphanMetadataRows;
  final String checkpointResult;

  PixivDbRepairReport({
    required this.integrityOk,
    required this.integrityMessages,
    required this.imageRows,
    required this.missingMetadataRows,
    required this.incompleteMetadataRows,
    required this.orphanMetadataRows,
    required this.checkpointResult,
  });

  @override
  String toString() {
    return [
      'Database integrity: ${integrityOk ? 'ok' : 'problem found'}',
      if (integrityMessages.isNotEmpty)
        'Integrity detail: ${integrityMessages.join('; ')}',
      'WAL checkpoint: $checkpointResult',
      'Artwork rows: $imageRows',
      'Missing metadata rows: $missingMetadataRows',
      'Incomplete metadata rows: $incompleteMetadataRows',
      'Orphan metadata rows: $orphanMetadataRows',
    ].join('\n');
  }
}

DateTime? _parseDate(dynamic v) {
  if (v == null) return null;
  if (v is DateTime) return v;
  return DateTime.tryParse('$v');
}

class PixivDBManager {
  String rootDirectory;
  late final Database _db;

  PixivDBManager({
    required this.rootDirectory,
    String? target,
    int timeoutSeconds = 5 * 60,
  }) {
    String dbPath = target ?? '';
    if (dbPath.isEmpty) {
      dbPath = p.join(pixiv_helper.modulePath(), 'db.sqlite');
      pixiv_helper.printAndLog('info', 'Using default DB Path: $dbPath');
    } else {
      pixiv_helper.printAndLog('info', 'Using custom DB Path: $dbPath');
    }
    _db = sqlite3.open(dbPath);
    _db.execute('PRAGMA busy_timeout = ${timeoutSeconds * 1000}');
  }

  void close() => _db.dispose();

  /// I. Create Database
  void createDatabase() {
    stdout.write('Creating database... ');
    _db.execute('''
      CREATE TABLE IF NOT EXISTS pixiv_master_member (
        member_id INTEGER PRIMARY KEY ON CONFLICT IGNORE,
        name TEXT,
        save_folder TEXT,
        created_date DATE,
        last_update_date DATE,
        last_image INTEGER
      )
    ''');
    _tryExec(
        'ALTER TABLE pixiv_master_member ADD COLUMN is_deleted INTEGER DEFAULT 0');
    _tryExec('ALTER TABLE pixiv_master_member ADD COLUMN member_token TEXT');

    _db.execute('''
      CREATE TABLE IF NOT EXISTS pixiv_master_image (
        image_id INTEGER PRIMARY KEY,
        member_id INTEGER,
        title TEXT,
        save_name TEXT,
        created_date DATE,
        last_update_date DATE
      )
    ''');
    _tryExec('ALTER TABLE pixiv_master_image ADD COLUMN is_manga TEXT');
    _tryExec('ALTER TABLE pixiv_master_image ADD COLUMN caption TEXT');

    _db.execute('''
      CREATE TABLE IF NOT EXISTS pixiv_manga_image (
        image_id INTEGER,
        page INTEGER,
        save_name TEXT,
        created_date DATE,
        last_update_date DATE,
        PRIMARY KEY (image_id, page)
      )
    ''');
    _db.execute('''
      CREATE TABLE IF NOT EXISTS pixiv_master_tag (
        tag_id VARCHAR(255) PRIMARY KEY,
        created_date DATE,
        last_update_date DATE
      )
    ''');
    _db.execute('''
      CREATE TABLE IF NOT EXISTS pixiv_tag_translation (
        tag_id VARCHAR(255) REFERENCES pixiv_master_tag(tag_id),
        translation_type VARCHAR(255),
        translation VARCHAR(255),
        created_date DATE,
        last_update_date DATE,
        PRIMARY KEY (tag_id, translation_type)
      )
    ''');
    _db.execute('''
      CREATE TABLE IF NOT EXISTS pixiv_image_to_tag (
        image_id INTEGER REFERENCES pixiv_master_image(image_id),
        tag_id VARCHAR(255) REFERENCES pixiv_master_tag(tag_id),
        created_date DATE,
        last_update_date DATE,
        PRIMARY KEY (image_id, tag_id)
      )
    ''');
    _db.execute('''
      CREATE TABLE IF NOT EXISTS pixiv_ai_info (
        image_id INTEGER PRIMARY KEY,
        ai_type INTEGER,
        created_date DATE,
        last_update_date DATE
      )
    ''');
    _db.execute('''
      CREATE TABLE IF NOT EXISTS pixiv_download_metadata (
        image_id INTEGER PRIMARY KEY,
        title TEXT,
        caption TEXT,
        tags TEXT,
        pages INTEGER,
        works_date DATE,
        total_views INTEGER,
        total_rating INTEGER,
        bookmark_count INTEGER,
        created_date DATE,
        last_update_date DATE
      )
    ''');
    _db.execute('''
      CREATE TABLE IF NOT EXISTS pixiv_master_series (
        series_id VARCHAR(255) PRIMARY KEY,
        series_title VARCHAR(255),
        series_type VARCHAR(255),
        series_description TEXT,
        created_date DATE,
        last_update_date DATE
      )
    ''');
    _db.execute('''
      CREATE TABLE IF NOT EXISTS pixiv_image_to_series (
        series_id VARCHAR(255) REFERENCES pixiv_master_series(series_id),
        series_order INTEGER,
        image_id INTEGER REFERENCES pixiv_master_image(image_id),
        created_date DATE,
        last_update_date DATE,
        PRIMARY KEY (series_id, series_order),
        UNIQUE (image_id)
      )
    ''');
    _db.execute('''
      CREATE TABLE IF NOT EXISTS fanbox_master_post (
        member_id INTEGER,
        post_id INTEGER PRIMARY KEY ON CONFLICT IGNORE,
        title TEXT,
        fee_required INTEGER,
        published_date DATE,
        updated_date DATE,
        post_type TEXT,
        last_update_date DATE
      )
    ''');
    _db.execute('''
      CREATE TABLE IF NOT EXISTS fanbox_post_image (
        post_id INTEGER,
        page INTEGER,
        save_name TEXT,
        created_date DATE,
        last_update_date DATE,
        PRIMARY KEY (post_id, page)
      )
    ''');
    _db.execute('''
      CREATE TABLE IF NOT EXISTS sketch_master_post (
        member_id INTEGER,
        post_id INTEGER PRIMARY KEY ON CONFLICT IGNORE,
        title TEXT,
        published_date DATE,
        updated_date DATE,
        post_type TEXT,
        last_update_date DATE
      )
    ''');
    _db.execute('''
      CREATE TABLE IF NOT EXISTS sketch_post_image (
        post_id INTEGER,
        page INTEGER,
        save_name TEXT,
        created_date DATE,
        last_update_date DATE,
        PRIMARY KEY (post_id, page)
      )
    ''');
    _db.execute('''
      CREATE TABLE IF NOT EXISTS novel_detail (
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
    stdout.writeln('done.');
  }

  void _tryExec(String sql) {
    try {
      _db.execute(sql);
    } catch (_) {
      // alter table will fail when column already exists
    }
  }

  void dropDatabase() {
    for (final t in const [
      'pixiv_master_member',
      'pixiv_master_image',
      'pixiv_manga_image',
      'pixiv_master_tag',
      'pixiv_tag_translation',
      'pixiv_image_to_tag',
      'pixiv_ai_info',
      'pixiv_download_metadata',
      'pixiv_master_series',
      'pixiv_image_to_series',
      'fanbox_master_post',
      'fanbox_post_image',
      'sketch_master_post',
      'sketch_post_image',
      'novel_detail',
    ]) {
      _tryExec('DROP TABLE IF EXISTS $t');
    }
  }

  /// II. Member CRUD
  void insertNewMember(int memberId) {
    _db.execute('''
      INSERT OR IGNORE INTO pixiv_master_member
        (member_id, name, save_folder, created_date, last_update_date, last_image)
      VALUES(?, ?, ?, ?, ?, ?)
    ''', [memberId, '', '', _now(), _now(), 0]);
  }

  void importList(List<PixivListItem> items) {
    for (final item in items) {
      insertNewMember(item.memberId);
      _db.execute(
          'UPDATE pixiv_master_member SET save_folder = ? WHERE member_id = ?',
          [item.path, item.memberId]);
    }
  }

  PixivMemberRow? selectMemberByMemberId(int memberId) {
    final r = _db.select(
        'SELECT * FROM pixiv_master_member WHERE member_id = ?', [memberId]);
    if (r.isEmpty) return null;
    return PixivMemberRow.fromRow(r.first);
  }

  PixivMemberRow selectMemberByMemberId2(int memberId) {
    final existing = selectMemberByMemberId(memberId);
    if (existing != null) return existing;
    insertNewMember(memberId);
    return PixivMemberRow(memberId: memberId);
  }

  List<PixivMemberRow> selectAllMember() {
    final rows = _db.select(
        'SELECT * FROM pixiv_master_member WHERE COALESCE(is_deleted, 0) = 0');
    return rows.map(PixivMemberRow.fromRow).toList();
  }

  List<PixivMemberRow> selectMembersByLastDownloadDate(int days) {
    final rows = _db.select('''
        SELECT * FROM pixiv_master_member
        WHERE COALESCE(is_deleted, 0) = 0
          AND (last_update_date IS NULL OR DATE(last_update_date) <= DATE('now', '-${days} days'))
        ''');
    return rows.map(PixivMemberRow.fromRow).toList();
  }

  void updateLastDownloadedImage(int memberId, int lastImage) {
    _db.execute('''
      UPDATE pixiv_master_member
        SET last_image = ?, last_update_date = ?
      WHERE member_id = ?
    ''', [lastImage, _now(), memberId]);
  }

  void updateMemberName(int memberId, String name) {
    _db.execute('UPDATE pixiv_master_member SET name = ? WHERE member_id = ?',
        [name, memberId]);
  }

  void updateMemberToken(int memberId, String token) {
    _db.execute(
        'UPDATE pixiv_master_member SET member_token = ? WHERE member_id = ?',
        [token, memberId]);
  }

  void setIsDeleted(int memberId, bool isDeleted) {
    _db.execute(
        'UPDATE pixiv_master_member SET is_deleted = ? WHERE member_id = ?',
        [isDeleted ? 1 : 0, memberId]);
  }

  /// III. Image CRUD
  void insertImage(int imageId, int memberId,
      {String title = '',
      String saveName = '',
      String isManga = 'N',
      String caption = ''}) {
    _db.execute('''
      INSERT OR REPLACE INTO pixiv_master_image
        (image_id, member_id, title, save_name, created_date,
         last_update_date, is_manga, caption)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''',
        [imageId, memberId, title, saveName, _now(), _now(), isManga, caption]);
  }

  void insertMangaImages(int imageId, List<String> saveNames) {
    for (var i = 0; i < saveNames.length; i++) {
      _db.execute('''
        INSERT OR REPLACE INTO pixiv_manga_image
          (image_id, page, save_name, created_date, last_update_date)
        VALUES (?, ?, ?, ?, ?)
      ''', [imageId, i, saveNames[i], _now(), _now()]);
    }
  }

  Map<String, dynamic>? selectImageByImageId(int imageId) {
    final r = _db.select(
        'SELECT * FROM pixiv_master_image WHERE image_id = ?', [imageId]);
    if (r.isEmpty) return null;
    return Map<String, dynamic>.fromEntries(
        r.first.keys.map((k) => MapEntry('$k', r.first[k])));
  }

  void deleteImage(int imageId) {
    _db.execute('DELETE FROM pixiv_master_image WHERE image_id = ?', [imageId]);
    _db.execute('DELETE FROM pixiv_manga_image WHERE image_id = ?', [imageId]);
    _db.execute('DELETE FROM pixiv_image_to_tag WHERE image_id = ?', [imageId]);
    _db.execute(
        'DELETE FROM pixiv_image_to_series WHERE image_id = ?', [imageId]);
    _db.execute('DELETE FROM pixiv_ai_info WHERE image_id = ?', [imageId]);
  }

  /// IV. Tag CRUD
  void insertTag(String tagId) {
    _db.execute('''
      INSERT OR IGNORE INTO pixiv_master_tag
        (tag_id, created_date, last_update_date) VALUES (?, ?, ?)
    ''', [tagId, _now(), _now()]);
  }

  void updateTag(String tagId) {
    _db.execute('''
      UPDATE pixiv_master_tag
      SET last_update_date = ?
      WHERE tag_id = ?
    ''', [_now(), tagId]);
  }

  void insertImageTag(int imageId, String tagId) {
    insertTag(tagId);
    _db.execute('''
      INSERT OR IGNORE INTO pixiv_image_to_tag
        (image_id, tag_id, created_date, last_update_date)
      VALUES (?, ?, ?, ?)
    ''', [imageId, tagId, _now(), _now()]);
  }

  void insertTagTranslation(String tagId, String type, String translation) {
    insertTag(tagId);
    _db.execute('''
      INSERT OR REPLACE INTO pixiv_tag_translation
        (tag_id, translation_type, translation, created_date, last_update_date)
      VALUES (?, ?, ?, ?, ?)
    ''', [tagId, type, translation, _now(), _now()]);
  }

  /// V. AI info CRUD
  void insertAiInfo(int imageId, int aiType) {
    _db.execute('''
      INSERT OR REPLACE INTO pixiv_ai_info
        (image_id, ai_type, created_date, last_update_date)
      VALUES (?, ?, ?, ?)
    ''', [imageId, aiType, _now(), _now()]);
  }

  int? getAiType(int imageId) {
    final r = _db.select(
        'SELECT ai_type FROM pixiv_ai_info WHERE image_id = ?', [imageId]);
    if (r.isEmpty) return null;
    return r.first['ai_type'] as int?;
  }

  /// VI. Download metadata
  void insertDownloadMetadata({
    required int imageId,
    required String title,
    required String caption,
    required List<String> tags,
    required int pages,
    required String worksDate,
    required int totalViews,
    required int totalRating,
    required int bookmarkCount,
  }) {
    _db.execute('''
      INSERT OR REPLACE INTO pixiv_download_metadata
        (image_id, title, caption, tags, pages, works_date, total_views,
         total_rating, bookmark_count, created_date, last_update_date)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', [
      imageId,
      title,
      caption,
      tags.take(10).join(', '),
      pages,
      worksDate,
      totalViews,
      totalRating,
      bookmarkCount,
      _now(),
      _now(),
    ]);
  }

  Map<String, dynamic>? selectDownloadMetadata(int imageId) {
    final r = _db.select(
        'SELECT * FROM pixiv_download_metadata WHERE image_id = ?', [imageId]);
    if (r.isEmpty) return null;
    return Map<String, dynamic>.fromEntries(
        r.first.keys.map((k) => MapEntry('$k', r.first[k])));
  }

  /// VII. Series CRUD
  void insertSeries(String seriesId, String title,
      {String? type, String? description}) {
    _db.execute('''
      INSERT OR REPLACE INTO pixiv_master_series
        (series_id, series_title, series_type, series_description, created_date, last_update_date)
      VALUES (?, ?, ?, ?, ?, ?)
    ''', [seriesId, title, type ?? '', description ?? '', _now(), _now()]);
  }

  void insertImageToSeries(String seriesId, int order, int imageId) {
    _db.execute('''
      INSERT OR REPLACE INTO pixiv_image_to_series
        (series_id, series_order, image_id, created_date, last_update_date)
      VALUES (?, ?, ?, ?, ?)
    ''', [seriesId, order, imageId, _now(), _now()]);
  }

  /// VIII. Fanbox/Sketch
  void insertFanboxPost({
    required int memberId,
    required int postId,
    required String title,
    required int feeRequired,
    required String publishedDate,
    required String updatedDate,
    required String postType,
  }) {
    _db.execute('''
      INSERT OR REPLACE INTO fanbox_master_post
        (member_id, post_id, title, fee_required,
         published_date, updated_date, post_type, last_update_date)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', [
      memberId,
      postId,
      title,
      feeRequired,
      publishedDate,
      updatedDate,
      postType,
      _now()
    ]);
  }

  Map<String, dynamic>? selectFanboxPost(int postId) {
    final r = _db
        .select('SELECT * FROM fanbox_master_post WHERE post_id = ?', [postId]);
    if (r.isEmpty) return null;
    return Map<String, dynamic>.fromEntries(
        r.first.keys.map((k) => MapEntry('$k', r.first[k])));
  }

  void insertSketchPost({
    required int memberId,
    required int postId,
    required String title,
    required String publishedDate,
    required String updatedDate,
    required String postType,
  }) {
    _db.execute('''
      INSERT OR REPLACE INTO sketch_master_post
        (member_id, post_id, title, published_date, updated_date, post_type, last_update_date)
      VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', [
      memberId,
      postId,
      title,
      publishedDate,
      updatedDate,
      postType,
      _now()
    ]);
  }

  /// IX. Maintenance
  void vacuum() => _db.execute('VACUUM');

  void replaceRootPath(String oldRoot, String newRoot) {
    _db.execute('''
      UPDATE pixiv_master_image
      SET save_name = REPLACE(save_name, ?, ?)
      WHERE save_name LIKE ?
    ''', [oldRoot, newRoot, '$oldRoot%']);
    _db.execute('''
      UPDATE pixiv_manga_image
      SET save_name = REPLACE(save_name, ?, ?)
      WHERE save_name LIKE ?
    ''', [oldRoot, newRoot, '$oldRoot%']);
  }

  PixivDbRepairReport repairAfterInterruptedRun() {
    final integrityRows = _db.select('PRAGMA integrity_check');
    final integrityMessages =
        integrityRows.map((row) => '${row.values.first}').toList();
    final integrityOk =
        integrityMessages.length == 1 && integrityMessages.first == 'ok';

    var checkpointResult = 'not needed';
    try {
      final checkpointRows = _db.select('PRAGMA wal_checkpoint(TRUNCATE)');
      checkpointResult =
          checkpointRows.map((row) => row.values.join(',')).join('; ');
    } catch (e) {
      checkpointResult = 'skipped: $e';
    }

    return PixivDbRepairReport(
      integrityOk: integrityOk,
      integrityMessages: integrityMessages,
      checkpointResult: checkpointResult,
      imageRows: _count('SELECT COUNT(*) AS c FROM pixiv_master_image'),
      missingMetadataRows: _count('''
        SELECT COUNT(*) AS c
        FROM pixiv_master_image i
        LEFT JOIN pixiv_download_metadata m ON m.image_id = i.image_id
        WHERE m.image_id IS NULL
      '''),
      incompleteMetadataRows: _count('''
        SELECT COUNT(*) AS c
        FROM pixiv_download_metadata
        WHERE COALESCE(title, '') = ''
           OR COALESCE(caption, '') = ''
           OR COALESCE(tags, '') = ''
      '''),
      orphanMetadataRows: _count('''
        SELECT COUNT(*) AS c
        FROM pixiv_download_metadata m
        LEFT JOIN pixiv_master_image i ON i.image_id = m.image_id
        WHERE i.image_id IS NULL
      '''),
    );
  }

  PixivDbImportStats importMetadataFromPixivUtilDb(
    String sourceDbPath, {
    bool replaceExisting = false,
  }) {
    final sourceFile = File(sourceDbPath);
    if (!sourceFile.existsSync()) {
      throw ArgumentError('Source database does not exist: $sourceDbPath');
    }

    final stats = PixivDbImportStats();
    final source = sqlite3.open(sourceDbPath, mode: OpenMode.readOnly);
    try {
      _db.execute('BEGIN IMMEDIATE');
      try {
        for (final table in _metadataTables) {
          if (!_hasTable(source, table)) {
            stats.skippedTables[table] = 'missing in source';
            continue;
          }
          if (!_hasTable(_db, table)) {
            stats.skippedTables[table] = 'missing in target';
            continue;
          }

          final sourceColumns = _tableColumns(source, table);
          final targetColumns = _tableColumns(_db, table);
          final columns =
              sourceColumns.where((c) => targetColumns.contains(c)).toList();
          if (columns.isEmpty) {
            stats.skippedTables[table] = 'no matching columns';
            continue;
          }

          final quotedTable = _quoteIdentifier(table);
          final rows = source.select(
            'SELECT ${columns.map(_quoteIdentifier).join(', ')} FROM $quotedTable',
          );
          if (rows.isEmpty) {
            stats.importedByTable[table] = 0;
            continue;
          }

          final insertMode = replaceExisting ? 'REPLACE' : 'IGNORE';
          final insertStatement = _db.prepare('''
            INSERT OR $insertMode INTO $quotedTable
              (${columns.map(_quoteIdentifier).join(', ')})
            VALUES (${List.filled(columns.length, '?').join(', ')})
          ''');
          final pkColumns = _primaryKeyColumns(source, table)
              .where((c) => columns.contains(c))
              .toList();
          final fillColumns = replaceExisting || pkColumns.isEmpty
              ? <String>[]
              : columns.where((c) => !pkColumns.contains(c)).toList();
          PreparedStatement? fillStatement;
          if (fillColumns.isNotEmpty) {
            fillStatement = _db.prepare('''
              UPDATE $quotedTable
              SET ${fillColumns.map((column) {
              final quoted = _quoteIdentifier(column);
              return "$quoted = CASE WHEN $quoted IS NULL OR $quoted = '' THEN ? ELSE $quoted END";
            }).join(', ')}
              WHERE ${pkColumns.map((column) => '${_quoteIdentifier(column)} = ?').join(' AND ')}
            ''');
          }

          var changed = 0;
          try {
            for (final row in rows) {
              insertStatement
                  .execute(columns.map((column) => row[column]).toList());
              final inserted = _db.updatedRows;
              changed += inserted;
              if (inserted == 0 && fillStatement != null) {
                fillStatement.execute([
                  ...fillColumns.map((column) => row[column]),
                  ...pkColumns.map((column) => row[column]),
                ]);
                changed += _db.updatedRows;
              }
            }
          } finally {
            insertStatement.dispose();
            fillStatement?.dispose();
          }
          stats.importedByTable[table] = changed;
        }
        _db.execute('COMMIT');
      } catch (_) {
        _db.execute('ROLLBACK');
        rethrow;
      }
    } finally {
      source.dispose();
    }
    return stats;
  }

  /// Returns a raw db handle for advanced usage.
  Database get raw => _db;

  String _now() => DateTime.now().toIso8601String();

  int _count(String sql) {
    final rows = _db.select(sql);
    if (rows.isEmpty) return 0;
    return (rows.first['c'] as int?) ?? int.parse('${rows.first.values.first}');
  }

  static const List<String> _metadataTables = [
    'pixiv_master_member',
    'pixiv_master_image',
    'pixiv_manga_image',
    'pixiv_master_tag',
    'pixiv_tag_translation',
    'pixiv_image_to_tag',
    'pixiv_ai_info',
    'pixiv_download_metadata',
    'pixiv_master_series',
    'pixiv_image_to_series',
    'fanbox_master_post',
    'fanbox_post_image',
    'sketch_master_post',
    'sketch_post_image',
    'novel_detail',
  ];

  static bool _hasTable(Database db, String table) {
    final rows = db.select(
      "SELECT name FROM sqlite_master WHERE type = 'table' AND name = ?",
      [table],
    );
    return rows.isNotEmpty;
  }

  static List<String> _tableColumns(Database db, String table) {
    final rows = db.select('PRAGMA table_info(${_quoteIdentifier(table)})');
    return rows.map((row) => '${row['name']}').toList();
  }

  static List<String> _primaryKeyColumns(Database db, String table) {
    final rows = db.select('PRAGMA table_info(${_quoteIdentifier(table)})');
    final pkRows = rows.where((row) => (row['pk'] as int? ?? 0) > 0).toList()
      ..sort((a, b) => (a['pk'] as int).compareTo(b['pk'] as int));
    return pkRows.map((row) => '${row['name']}').toList();
  }

  static String _quoteIdentifier(String value) {
    return '"${value.replaceAll('"', '""')}"';
  }
}

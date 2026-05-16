/// CLI entry point for PixivUtil2 (Dart port).
///
/// This replaces `PixivUtil2.py`'s `main()` function. It provides an
/// interactive menu and an `args`-based CLI.
library;

import 'dart:io';

import 'package:args/args.dart';

import 'package:pixiv_util2/common/pixiv_browser.dart';
import 'package:pixiv_util2/common/pixiv_config.dart';
import 'package:pixiv_util2/common/pixiv_helper.dart' as pixiv_helper;
import 'package:pixiv_util2/handler/pixiv_artist_handler.dart'
    as artist_handler;
import 'package:pixiv_util2/handler/pixiv_batch_handler.dart' as batch_handler;
import 'package:pixiv_util2/handler/pixiv_bookmark_handler.dart'
    as bookmark_handler;
import 'package:pixiv_util2/handler/pixiv_fanbox_handler.dart'
    as fanbox_handler;
import 'package:pixiv_util2/handler/pixiv_image_handler.dart' as image_handler;
import 'package:pixiv_util2/handler/pixiv_list_handler.dart' as list_handler;
import 'package:pixiv_util2/handler/pixiv_novel_handler.dart' as novel_handler;
import 'package:pixiv_util2/handler/pixiv_ranking_handler.dart'
    as ranking_handler;
import 'package:pixiv_util2/handler/pixiv_sketch_handler.dart'
    as sketch_handler;
import 'package:pixiv_util2/handler/pixiv_tags_handler.dart' as tags_handler;
import 'package:pixiv_util2/pixiv_db_manager.dart';

/// The main caller object passed to handlers; mirrors the Python module's
/// global state.
class PixivCaller {
  PixivConfig config;
  PixivBrowser br;
  PixivDBManager dbManager;
  int errorCode = 0;
  bool DEBUG_SKIP_PROCESS_IMAGE = false;
  bool DEBUG_SKIP_DOWNLOAD_IMAGE = false;
  List<dynamic> errorList = [];

  PixivCaller({
    required this.config,
    required this.br,
    required this.dbManager,
  });
}

ArgParser _buildParser() {
  return ArgParser()
    ..addOption('config', abbr: 'c', defaultsTo: 'config.ini')
    ..addOption('option',
        abbr: 'o', help: 'Run a specific menu option non-interactively')
    ..addOption('member-id', help: 'Member ID for options 1/9/10')
    ..addOption('image-id', help: 'Image ID for option 2')
    ..addOption('post-id', help: 'FANBOX/Sketch post ID')
    ..addOption('tag', help: 'Tag for option 3')
    ..addOption('novel-id', help: 'Novel ID')
    ..addOption('series-id', help: 'Series ID')
    ..addOption('list-file', defaultsTo: 'list.txt')
    ..addOption('mode', defaultsTo: 'daily', help: 'Ranking mode')
    ..addOption('start-page', defaultsTo: '1')
    ..addOption('end-page', defaultsTo: '0')
    ..addFlag('process-from-db', help: 'Use the DB instead of list.txt')
    ..addFlag('verbose', abbr: 'v', help: 'Verbose output')
    ..addFlag('help', abbr: 'h', negatable: false);
}

Future<void> main(List<String> arguments) async {
  pixiv_helper.printOriginalHeader();

  final parser = _buildParser();
  final ArgResults args;
  try {
    args = parser.parse(arguments);
  } on FormatException catch (e) {
    stderr.writeln('Argument error: ${e.message}');
    stderr.writeln(parser.usage);
    exit(2);
  }
  if (args['help'] as bool) {
    print(parser.usage);
    return;
  }

  final config = PixivConfig();
  await config.loadConfig(args['config'] as String?);
  pixiv_helper.setConfig(config);
  if (args['verbose'] as bool) {
    config.printConfig();
  }

  final browser = createBrowser(config: config);
  final db = PixivDBManager(
    rootDirectory: config.rootDirectory,
    target: config.dbPath,
  );
  db.createDatabase();

  final caller = PixivCaller(config: config, br: browser, dbManager: db);

  try {
    _printStartupNotes(config);
    await _loginWithCookie(browser, config);
    if (args['option'] != null) {
      await _runOption(caller, args, args['option'] as String);
    } else {
      await _menuLoop(caller);
    }
  } catch (e, st) {
    pixiv_helper.printAndLog('error', 'Fatal error: $e\n$st');
  } finally {
    db.close();
    browser.close();
  }

  exit(caller.errorCode);
}

void _printStartupNotes(PixivConfig config) {
  if (config.dayLastUpdated != 0 && config.processFromDb) {
    pixiv_helper.printAndLog('info',
        'Only process members where the last update is >= ${config.dayLastUpdated} days ago');
  }
  print('Username login is broken, use Cookies to log in.');
  print(
      'See Q3. at https://github.com/Nandaka/PixivUtil2?tab=readme-ov-file#a-usage');
  if (config.username.isEmpty || config.password.isEmpty) {
    print('No username and/or password found in config.ini');
    print(
        'See https://github.com/Nandaka/PixivUtil2?tab=readme-ov-file#authentication');
  }
}

Future<void> _loginWithCookie(PixivBrowser browser, PixivConfig config) async {
  if (config.cookie.isEmpty) return;
  final result = await browser.loginUsingCookie();
  if (result) {
    if (browser.myId > 0) {
      pixiv_helper.printAndLog('info', 'My User Id: ${browser.myId}.');
    }
    pixiv_helper.printAndLog('info', 'Premium User: ${browser.isPremium}.');
  }
}

String _requireArg(ArgResults args, String key, String option) {
  final value = args[key] as String?;
  if (value == null || value.trim().isEmpty) {
    throw FormatException('Missing --$key for option $option');
  }
  return value.trim();
}

int _requireIntArg(ArgResults args, String key, String option) {
  final raw = _requireArg(args, key, option);
  final parsed = int.tryParse(raw);
  if (parsed == null) {
    throw FormatException('Invalid integer for --$key: $raw');
  }
  return parsed;
}

Future<void> _runOption(
    PixivCaller caller, ArgResults args, String option) async {
  final config = caller.config;
  switch (option) {
    case '1': // download by member id
      final id = _requireIntArg(args, 'member-id', option);
      await artist_handler.processMember(
        caller: caller,
        config: config,
        memberId: id,
      );
      break;
    case '2': // download by image id
      final id = _requireIntArg(args, 'image-id', option);
      await image_handler.processImage(
        caller: caller,
        config: config,
        imageId: id,
      );
      break;
    case '3': // download by tag
      await tags_handler.processTags(
        caller: caller,
        config: config,
        tags: _requireArg(args, 'tag', option),
        page: _requireIntArg(args, 'start-page', option),
        endPage: _requireIntArg(args, 'end-page', option),
      );
      break;
    case '4': // download by list
      await list_handler.processList(
        caller: caller,
        config: config,
        listFileName: args['list-file'] as String?,
      );
      break;
    case '5':
      _notImplemented('Download from followed artists');
      break;
    case '6':
      final memberId = caller.br.myId;
      if (memberId <= 0) {
        _notImplemented(
            'Download from bookmarked images requires login user id');
        break;
      }
      await bookmark_handler.processImageBookmark(
        caller: caller,
        config: config,
        memberId: memberId,
        startPage: _requireIntArg(args, 'start-page', option),
        endPage: _requireIntArg(args, 'end-page', option),
      );
      break;
    case '7':
      await list_handler.processTagsList(
        caller: caller,
        config: config,
        filename: args['list-file'] as String? ?? 'list.txt',
      );
      break;
    case '8':
      await bookmark_handler.processBookmark(
        caller: caller,
        config: config,
        startPage: _requireIntArg(args, 'start-page', option),
        endPage: _requireIntArg(args, 'end-page', option),
      );
      break;
    case '9':
      await tags_handler.processTags(
        caller: caller,
        config: config,
        tags: _requireArg(args, 'tag', option),
        page: _requireIntArg(args, 'start-page', option),
        endPage: _requireIntArg(args, 'end-page', option),
        titleCaption: true,
      );
      break;
    case '10':
      await tags_handler.processTags(
        caller: caller,
        config: config,
        tags: _requireArg(args, 'tag', option),
        page: _requireIntArg(args, 'start-page', option),
        endPage: _requireIntArg(args, 'end-page', option),
        memberId: _requireIntArg(args, 'member-id', option),
      );
      break;
    case '11':
      await bookmark_handler.processImageBookmark(
        caller: caller,
        config: config,
        memberId: _requireIntArg(args, 'member-id', option),
        startPage: _requireIntArg(args, 'start-page', option),
        endPage: _requireIntArg(args, 'end-page', option),
      );
      break;
    case '13':
      await image_handler.processMangaSeries(
        caller: caller,
        config: config,
        mangaSeriesId: _requireIntArg(args, 'series-id', option),
        startPage: _requireIntArg(args, 'start-page', option),
        endPage: _requireIntArg(args, 'end-page', option),
      );
      break;
    case '14': // novel
      await novel_handler.processNovel(
        caller: caller,
        config: config,
        novelId: _requireIntArg(args, 'novel-id', option),
      );
      break;
    case '15': // novel series
      await novel_handler.processNovelSeries(
        caller: caller,
        config: config,
        seriesId: _requireIntArg(args, 'series-id', option),
      );
      break;
    case '16': // ranking
      await ranking_handler.processRanking(
        caller: caller,
        config: config,
        mode: _requireArg(args, 'mode', option),
        content: '',
        startPage: _requireIntArg(args, 'start-page', option),
        endPage: _requireIntArg(args, 'end-page', option),
      );
      break;
    case '18': // new illusts
      await ranking_handler.processNewIllusts(
        caller: caller,
        config: config,
        maxPage: _requireIntArg(args, 'end-page', option),
      );
      break;
    case '19':
      await image_handler.processUnlistedImage(
        caller: caller,
        config: config,
        unlistedId: _requireArg(args, 'image-id', option),
      );
      break;
    case 'm1':
      await artist_handler.processMemberMetadata(
        caller: caller,
        config: config,
        memberId: _requireIntArg(args, 'member-id', option),
      );
      break;
    case 'm2':
      await image_handler.processImageMetadata(
        caller: caller,
        config: config,
        imageId: _requireIntArg(args, 'image-id', option),
      );
      break;
    case 'm3':
      await image_handler.processMangaSeriesMetadata(
        caller: caller,
        config: config,
        mangaSeriesId: _requireIntArg(args, 'series-id', option),
      );
      break;
    case 'm4':
      await tags_handler.processTagMetadata(
        caller: caller,
        config: config,
        tags: _requireArg(args, 'tag', option),
      );
      break;
    case 's1': // sketch
      await sketch_handler.processSketchArtists(
        caller: caller,
        config: config,
        artistToken: _requireArg(args, 'member-id', option),
      );
      break;
    case 's2':
      await sketch_handler.processSketchPost(
        caller: caller,
        config: config,
        postId: int.parse(
          (args['post-id'] as String?) ?? _requireArg(args, 'image-id', option),
        ),
      );
      break;
    case 'f2': // fanbox
      await fanbox_handler.processFanboxArtist(
        caller: caller,
        config: config,
        artistId: _requireIntArg(args, 'member-id', option),
      );
      break;
    case 'f3': // fanbox post
      await fanbox_handler.processFanboxPost(
        caller: caller,
        config: config,
        postId: int.parse(
          (args['post-id'] as String?) ?? _requireArg(args, 'image-id', option),
        ),
      );
      break;
    case 'b': // batch job
      await batch_handler.processBatchJob(
        caller: caller,
        config: config,
        jobFile: _requireArg(args, 'list-file', option),
      );
      break;
    default:
      pixiv_helper.printAndLog('error', 'Unknown option: $option');
  }
}

Future<void> _menuLoop(PixivCaller caller) async {
  while (true) {
    pixiv_helper.printOriginalHeader();
    _printMenu();
    final input = stdin.readLineSync()?.trim() ?? '';
    if (input == 'x' || input == '99' || input == 'q' || input.isEmpty) break;
    try {
      switch (input) {
        case '1':
          stdout.write('Member ID: ');
          final id = int.parse(stdin.readLineSync()!.trim());
          await artist_handler.processMember(
            caller: caller,
            config: caller.config,
            memberId: id,
          );
          break;
        case '2':
          stdout.write('Image ID: ');
          final id = int.parse(stdin.readLineSync()!.trim());
          await image_handler.processImage(
            caller: caller,
            config: caller.config,
            imageId: id,
          );
          break;
        case '3':
          stdout.write('Tag: ');
          final tag = stdin.readLineSync()!.trim();
          await tags_handler.processTags(
            caller: caller,
            config: caller.config,
            tags: tag,
          );
          break;
        case '4':
          await list_handler.processList(
            caller: caller,
            config: caller.config,
          );
          break;
        case '5':
          _notImplemented('Download from followed artists');
          break;
        case '6':
          if (caller.br.myId <= 0) {
            _notImplemented(
                'Download from bookmarked images requires login user id');
            break;
          }
          await bookmark_handler.processImageBookmark(
            caller: caller,
            config: caller.config,
            memberId: caller.br.myId,
          );
          break;
        case '7':
          stdout.write('Tags list filename [tags.txt]: ');
          final f = stdin.readLineSync()!.trim();
          await list_handler.processTagsList(
            caller: caller,
            config: caller.config,
            filename: f.isEmpty ? 'tags.txt' : f,
          );
          break;
        case '8':
          await bookmark_handler.processBookmark(
            caller: caller,
            config: caller.config,
          );
          break;
        case '9':
          stdout.write('Title/Caption keyword: ');
          final keyword = stdin.readLineSync()!.trim();
          await tags_handler.processTags(
            caller: caller,
            config: caller.config,
            tags: keyword,
            titleCaption: true,
          );
          break;
        case '10':
          stdout.write('Member ID: ');
          final memberId = int.parse(stdin.readLineSync()!.trim());
          stdout.write('Tag: ');
          final tag = stdin.readLineSync()!.trim();
          await tags_handler.processTags(
            caller: caller,
            config: caller.config,
            tags: tag,
            memberId: memberId,
          );
          break;
        case '11':
          stdout.write('Member ID: ');
          final id = int.parse(stdin.readLineSync()!.trim());
          await bookmark_handler.processImageBookmark(
            caller: caller,
            config: caller.config,
            memberId: id,
          );
          break;
        case '12':
          _notImplemented('Download by Group Id');
          break;
        case '13':
          stdout.write('Manga Series ID: ');
          final id = int.parse(stdin.readLineSync()!.trim());
          await image_handler.processMangaSeries(
            caller: caller,
            config: caller.config,
            mangaSeriesId: id,
          );
          break;
        case '14':
          stdout.write('Novel ID: ');
          final id = int.parse(stdin.readLineSync()!.trim());
          await novel_handler.processNovel(
            caller: caller,
            config: caller.config,
            novelId: id,
          );
          break;
        case '15':
          stdout.write('Series ID: ');
          final id = int.parse(stdin.readLineSync()!.trim());
          await novel_handler.processNovelSeries(
            caller: caller,
            config: caller.config,
            seriesId: id,
          );
          break;
        case '16':
          stdout.write('Mode (daily/weekly/monthly/...): ');
          final mode = stdin.readLineSync()!.trim();
          await ranking_handler.processRanking(
            caller: caller,
            config: caller.config,
            mode: mode,
            content: '',
          );
          break;
        case '17':
          await ranking_handler.processRanking(
            caller: caller,
            config: caller.config,
            mode: 'daily_r18',
            content: '',
          );
          break;
        case '18':
          await ranking_handler.processNewIllusts(
            caller: caller,
            config: caller.config,
          );
          break;
        case '19':
          stdout.write('Unlisted image ID/token: ');
          final id = stdin.readLineSync()!.trim();
          await image_handler.processUnlistedImage(
            caller: caller,
            config: caller.config,
            unlistedId: id,
          );
          break;
        case 'm1':
          stdout.write('Member ID: ');
          final id = int.parse(stdin.readLineSync()!.trim());
          await artist_handler.processMemberMetadata(
            caller: caller,
            config: caller.config,
            memberId: id,
          );
          break;
        case 'm2':
          stdout.write('Image ID: ');
          final id = int.parse(stdin.readLineSync()!.trim());
          await image_handler.processImageMetadata(
            caller: caller,
            config: caller.config,
            imageId: id,
          );
          break;
        case 'm3':
          stdout.write('Manga Series ID: ');
          final id = int.parse(stdin.readLineSync()!.trim());
          await image_handler.processMangaSeriesMetadata(
            caller: caller,
            config: caller.config,
            mangaSeriesId: id,
          );
          break;
        case 'm4':
          stdout.write('Tag(s), comma-separated: ');
          final tag = stdin.readLineSync()!.trim();
          await tags_handler.processTagMetadata(
            caller: caller,
            config: caller.config,
            tags: tag,
          );
          break;
        case 'f1':
          _notImplemented('Download from supporting list (FANBOX)');
          break;
        case 'f2':
          stdout.write('Fanbox artist ID: ');
          final id = int.parse(stdin.readLineSync()!.trim());
          await fanbox_handler.processFanboxArtist(
            caller: caller,
            config: caller.config,
            artistId: id,
          );
          break;
        case 'f3':
          stdout.write('Fanbox post ID: ');
          final id = int.parse(stdin.readLineSync()!.trim());
          await fanbox_handler.processFanboxPost(
            caller: caller,
            config: caller.config,
            postId: id,
          );
          break;
        case 'f4':
          _notImplemented('Download from following list (FANBOX)');
          break;
        case 'f5':
          _notImplemented('Download from custom list (FANBOX)');
          break;
        case 'f6':
          _notImplemented('Download Pixiv by FANBOX Artist ID');
          break;
        case 's1':
          stdout.write('Artist Token: ');
          final token = stdin.readLineSync()!.trim();
          await sketch_handler.processSketchArtists(
            caller: caller,
            config: caller.config,
            artistToken: token,
          );
          break;
        case 's2':
          stdout.write('Sketch post ID: ');
          final id = int.parse(stdin.readLineSync()!.trim());
          await sketch_handler.processSketchPost(
            caller: caller,
            config: caller.config,
            postId: id,
          );
          break;
        case 'b':
          stdout.write('Batch file [batch_job.json]: ');
          final f = stdin.readLineSync()!.trim();
          await batch_handler.processBatchJob(
            caller: caller,
            config: caller.config,
            jobFile: f.isEmpty ? 'batch_job.json' : f,
          );
          break;
        case 'd':
          _notImplemented('Manage database');
          break;
        case 'l':
          _notImplemented('Export local database');
          break;
        case 'e':
          _notImplemented('Export online followed artist');
          break;
        case 'm':
          _notImplemented("Export online other's followed artist");
          break;
        case 'p':
          _notImplemented('Export online image bookmarks');
          break;
        case 'i':
          stdout.write('List filename [list.txt]: ');
          final f = stdin.readLineSync()!.trim();
          await list_handler.importList(
            caller: caller,
            config: caller.config,
            listName: f.isEmpty ? 'list.txt' : f,
          );
          break;
        case 'u':
          _notImplemented('Ugoira re-encode');
          break;
        case 'r':
          await caller.config.loadConfig();
          pixiv_helper.setConfig(caller.config);
          break;
        case 'c':
          caller.config.printConfig();
          break;
        default:
          print('Unknown option.');
      }
    } catch (e) {
      pixiv_helper.printAndLog('error', 'Error: $e');
    }
  }
  print('Saving config and exiting...');
  await caller.config.writeConfig();
}

void _printMenu() {
  print('── Pixiv ───────────────────────────────────────────────────');
  print(' 1.  Download by member_id');
  print(' 2.  Download by image_id');
  print(' 3.  Download by tags');
  print(' 4.  Download from list');
  print(' 5.  Download from followed artists (/bookmark.php?type=user)');
  print(' 6.  Download from bookmarked images (/bookmark.php)');
  print(' 7.  Download from tags list');
  print(
      ' 8.  Download new illust from bookmarked members (/bookmark_new_illust.php)');
  print(' 9.  Download by Title/Caption');
  print(' 10. Download by Tag and Member Id');
  print(' 11. Download Member Bookmark (/bookmark.php?id=)');
  print(' 12. Download by Group Id');
  print(' 13. Download by Manga Series Id');
  print(' 14. Download by Novel Id');
  print(' 15. Download by Novel Series Id');
  print(' 16. Download by Rank');
  print(' 17. Download by Rank R-18');
  print(' 18. Download by New Illusts');
  print(' 19. Download by Unlisted image_id');
  print(' m1. Metadata by member_id');
  print(' m2. Metadata by image_id');
  print(' m3. Metadata by manga series id');
  print(' m4. Metadata by tag');
  print('── FANBOX ──────────────────────────────────────────────────');
  print(' f1. Download from supporting list (FANBOX)');
  print(' f2. Download by artist/creator id (FANBOX)');
  print(' f3. Download by post id (FANBOX)');
  print(' f4. Download from following list (FANBOX)');
  print(' f5. Download from custom list (FANBOX)');
  print(' f6. Download Pixiv by FANBOX Artist ID');
  print('── Sketch ──────────────────────────────────────────────────');
  print(' s1. Download by creator id (Sketch)');
  print(' s2. Download by post id (Sketch)');
  print('── Batch Download ──────────────────────────────────────────');
  print(' b. Batch Download from batch_job.json (experimental)');
  print('── Others ──────────────────────────────────────────────────');
  print(' d. Manage database');
  print(' l. Export local database.');
  print(' e. Export online followed artist.');
  print(" m. Export online other's followed artist.");
  print(' p. Export online image bookmarks.');
  print(' i. Import list file');
  print(' u. Ugoira re-encode');
  print(' r. Reload config.ini');
  print(' c. Print config.ini');
  print(' x. Exit');
  stdout.write('Input: ');
}

void _notImplemented(String label) {
  pixiv_helper.printAndLog(
      'warn', '$label is not implemented in the Dart port yet.');
}

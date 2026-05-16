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
import 'package:pixiv_util2/handler/pixiv_artist_handler.dart' as artist_handler;
import 'package:pixiv_util2/handler/pixiv_batch_handler.dart' as batch_handler;
import 'package:pixiv_util2/handler/pixiv_bookmark_handler.dart' as bookmark_handler;
import 'package:pixiv_util2/handler/pixiv_fanbox_handler.dart' as fanbox_handler;
import 'package:pixiv_util2/handler/pixiv_image_handler.dart' as image_handler;
import 'package:pixiv_util2/handler/pixiv_list_handler.dart' as list_handler;
import 'package:pixiv_util2/handler/pixiv_novel_handler.dart' as novel_handler;
import 'package:pixiv_util2/handler/pixiv_ranking_handler.dart' as ranking_handler;
import 'package:pixiv_util2/handler/pixiv_sketch_handler.dart' as sketch_handler;
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
    ..addOption('option', abbr: 'o', help: 'Run a specific menu option non-interactively')
    ..addOption('member-id', help: 'Member ID for options 1/9/10')
    ..addOption('image-id', help: 'Image ID for option 2')
    ..addOption('tag', help: 'Tag for option 3')
    ..addOption('novel-id', help: 'Novel ID')
    ..addOption('series-id', help: 'Series ID')
    ..addOption('list-file', defaultsTo: 'list.txt')
    ..addOption('mode', defaultsTo: 'daily', help: 'Ranking mode')
    ..addOption('start-page', defaultsTo: '1')
    ..addOption('end-page', defaultsTo: '0')
    ..addFlag('process-from-db',
        help: 'Use the DB instead of list.txt')
    ..addFlag('verbose', abbr: 'v', help: 'Verbose output')
    ..addFlag('help', abbr: 'h', negatable: false);
}

Future<void> main(List<String> arguments) async {
  pixiv_helper.printHeader();

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
  config.printConfig();

  final browser = createBrowser(config: config);
  final db = PixivDBManager(
    rootDirectory: config.rootDirectory,
    target: config.dbPath,
  );
  db.createDatabase();

  final caller = PixivCaller(config: config, br: browser, dbManager: db);

  try {
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
    case '5': // bookmarks
      await bookmark_handler.processBookmark(
        caller: caller,
        config: config,
        startPage: _requireIntArg(args, 'start-page', option),
        endPage: _requireIntArg(args, 'end-page', option),
      );
      break;
    case '6': // ranking
      await ranking_handler.processRanking(
        caller: caller,
        config: config,
        mode: _requireArg(args, 'mode', option),
        content: '',
        startPage: _requireIntArg(args, 'start-page', option),
        endPage: _requireIntArg(args, 'end-page', option),
      );
      break;
    case '7': // novel
      await novel_handler.processNovel(
        caller: caller,
        config: config,
        novelId: _requireIntArg(args, 'novel-id', option),
      );
      break;
    case '8': // novel series
      await novel_handler.processNovelSeries(
        caller: caller,
        config: config,
        seriesId: _requireIntArg(args, 'series-id', option),
      );
      break;
    case '9': // sketch
      await sketch_handler.processSketchArtists(
        caller: caller,
        config: config,
        artistToken: _requireArg(args, 'member-id', option),
      );
      break;
    case '10': // fanbox
      await fanbox_handler.processFanboxArtist(
        caller: caller,
        config: config,
        artistId: _requireIntArg(args, 'member-id', option),
      );
      break;
    case '11': // batch job
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
    print('');
    print('===== MENU =====');
    print(' 1. Download by Member ID');
    print(' 2. Download by Image ID');
    print(' 3. Download by Tag');
    print(' 4. Download from list.txt');
    print(' 5. Download bookmarks');
    print(' 6. Download Pixiv Ranking');
    print(' 7. Download Novel');
    print(' 8. Download Novel Series');
    print(' 9. Download Pixiv Sketch');
    print('10. Download FANBOX');
    print('11. Run batch_job.json');
    print('99. Save and exit');
    stdout.write('Choose an option: ');
    final input = stdin.readLineSync()?.trim() ?? '';
    if (input == '99' || input == 'q' || input.isEmpty) break;
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
          await bookmark_handler.processBookmark(
            caller: caller,
            config: caller.config,
          );
          break;
        case '6':
          stdout.write('Mode (daily/weekly/monthly/...): ');
          final mode = stdin.readLineSync()!.trim();
          await ranking_handler.processRanking(
            caller: caller,
            config: caller.config,
            mode: mode,
            content: '',
          );
          break;
        case '7':
          stdout.write('Novel ID: ');
          final id = int.parse(stdin.readLineSync()!.trim());
          await novel_handler.processNovel(
            caller: caller,
            config: caller.config,
            novelId: id,
          );
          break;
        case '8':
          stdout.write('Series ID: ');
          final id = int.parse(stdin.readLineSync()!.trim());
          await novel_handler.processNovelSeries(
            caller: caller,
            config: caller.config,
            seriesId: id,
          );
          break;
        case '9':
          stdout.write('Artist Token: ');
          final token = stdin.readLineSync()!.trim();
          await sketch_handler.processSketchArtists(
            caller: caller,
            config: caller.config,
            artistToken: token,
          );
          break;
        case '10':
          stdout.write('Fanbox artist ID: ');
          final id = int.parse(stdin.readLineSync()!.trim());
          await fanbox_handler.processFanboxArtist(
            caller: caller,
            config: caller.config,
            artistId: id,
          );
          break;
        case '11':
          stdout.write('Batch file [batch_job.json]: ');
          final f = stdin.readLineSync()!.trim();
          await batch_handler.processBatchJob(
            caller: caller,
            config: caller.config,
            jobFile: f.isEmpty ? 'batch_job.json' : f,
          );
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

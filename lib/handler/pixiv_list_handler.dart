/// List-file handler: process from `list.txt` or DB.
library;

import 'dart:io';

import '../common/pixiv_config.dart';
import '../common/pixiv_helper.dart' as pixiv_helper;
import '../model/pixiv_list_item.dart';
import '../model/pixiv_tags.dart';
import 'pixiv_artist_handler.dart' as artist_handler;
import 'pixiv_sketch_handler.dart' as sketch_handler;
import 'pixiv_tags_handler.dart' as tags_handler;

Future<void> processList({
  required dynamic caller,
  required PixivConfig config,
  String? listFileName,
  String? tags,
  bool includeSketch = false,
}) async {
  final db = caller.dbManager;
  final br = caller.br;

  List<dynamic> result;
  if (config.processFromDb) {
    pixiv_helper.printAndLog('info', 'Processing from database.');
    if (config.dayLastUpdated == 0) {
      result = db.selectAllMember();
    } else {
      print('Select only last ${config.dayLastUpdated} days.');
      result = db.selectMembersByLastDownloadDate(config.dayLastUpdated);
    }
  } else {
    pixiv_helper.printAndLog(
        'info', 'Processing from list file: $listFileName');
    result = await PixivListItem.parseList(
        listFileName ?? 'list.txt', config.rootDirectory);
  }

  if (await File('ignore_list.txt').exists()) {
    pixiv_helper.printAndLog(
        'info', 'Processing ignore list for member: ignore_list.txt');
    final ignore =
        await PixivListItem.parseList('ignore_list.txt', config.rootDirectory);
    result.removeWhere((item) =>
        ignore.any((ig) => (item as dynamic).memberId == ig.memberId));
  }

  pixiv_helper.printAndLog('info', 'Found ${result.length} items.');
  var current = 1;
  for (final item in result) {
    var retryCount = 0;
    while (true) {
      try {
        final prefix = '[$current of ${result.length}] ';
        await artist_handler.processMember(
          caller: caller,
          config: config,
          memberId: (item as dynamic).memberId as int,
          userDir: (item as dynamic).path as String,
          tags: tags,
          titlePrefix: prefix,
        );
        break;
      } catch (e) {
        if (retryCount > config.retry) {
          pixiv_helper.printAndLog(
              'error', 'Giving up member_id: ${(item as dynamic).memberId} ==> $e');
          break;
        }
        retryCount++;
        print('Retrying after 2s ($retryCount): $e');
        await pixiv_helper.printDelay(2);
      }
    }

    if (includeSketch) {
      var retryCountSketch = 0;
      while (true) {
        try {
          final (artistModel, _) = await br.getMemberPage(
              (item as dynamic).memberId as int);
          final prefix =
              '[$current (${(item as dynamic).memberId} - ${artistModel.artistToken}) of ${result.length}] ';
          await sketch_handler.processSketchArtists(
            caller: caller,
            config: config,
            artistToken: artistModel.artistToken,
            titlePrefix: prefix,
          );
          break;
        } catch (e) {
          if (retryCountSketch > config.retry) {
            pixiv_helper.printAndLog('error',
                'Giving up sketch for member_id: ${(item as dynamic).memberId} ==> $e');
            break;
          }
          retryCountSketch++;
          print('Retrying sketch after 2s ($retryCountSketch): $e');
          await pixiv_helper.printDelay(2);
        }
      }
    }

    current++;
    br.clearHistory();
    print('done for member id = ${(item as dynamic).memberId}.\n');
  }
}

Future<void> processTagsList({
  required dynamic caller,
  required PixivConfig config,
  required String filename,
  int page = 1,
  int endPage = 0,
  bool wildCard = true,
  String sortOrder = 'date_d',
  int? bookmarkCount,
  String? startDate,
  String? endDate,
}) async {
  print('Reading: $filename');
  final tags = await PixivTags.parseTagsList(filename);
  for (final tag in tags) {
    await tags_handler.processTags(
      caller: caller,
      config: config,
      tags: tag,
      page: page,
      endPage: endPage,
      wildCard: wildCard,
      startDate: startDate,
      endDate: endDate,
      useTagsAsDir: config.useTagsAsDir,
      bookmarkCount: bookmarkCount,
      sortOrder: sortOrder,
    );
    await pixiv_helper.wait(null, config);
  }
}

Future<void> importList({
  required dynamic caller,
  required PixivConfig config,
  String listName = 'list.txt',
}) async {
  final listPath = '${config.downloadListDirectory}${Platform.pathSeparator}$listName';
  if (await File(listPath).exists()) {
    final list = await PixivListItem.parseList(listPath, config.rootDirectory);
    caller.dbManager.importList(list);
    print('Updated ${list.length} items.');
  } else {
    pixiv_helper.printAndLog('warn', 'List file not found: $listPath');
  }
}

/// Batch-job handler: dispatches a `batch_job.json` to the right handler.
library;

import 'dart:convert';
import 'dart:io';

import '../common/pixiv_config.dart';
import '../common/pixiv_helper.dart' as pixiv_helper;
import 'pixiv_artist_handler.dart' as artist_handler;
import 'pixiv_bookmark_handler.dart' as bookmark_handler;
import 'pixiv_fanbox_handler.dart' as fanbox_handler;
import 'pixiv_list_handler.dart' as list_handler;
import 'pixiv_novel_handler.dart' as novel_handler;
import 'pixiv_ranking_handler.dart' as ranking_handler;
import 'pixiv_tags_handler.dart' as tags_handler;

Future<void> processBatchJob({
  required dynamic caller,
  required PixivConfig config,
  required String jobFile,
}) async {
  final f = File(jobFile);
  if (!await f.exists()) {
    pixiv_helper.printAndLog('error', 'Batch job file not found: $jobFile');
    return;
  }
  final data = jsonDecode(await f.readAsString()) as Map<String, dynamic>;
  for (final entry in data['jobs'] as List? ?? const []) {
    final job = entry as Map<String, dynamic>;
    await dispatchJob(caller: caller, config: config, job: job);
  }
}

Future<void> dispatchJob({
  required dynamic caller,
  required PixivConfig config,
  required Map<String, dynamic> job,
}) async {
  final type = job['type'] as String;
  switch (type) {
    case 'artist':
      await artist_handler.processMember(
        caller: caller,
        config: config,
        memberId: job['member_id'] as int,
        tags: job['tags'] as String?,
      );
      break;
    case 'tags':
      await tags_handler.processTags(
        caller: caller,
        config: config,
        tags: job['tags'] as String,
      );
      break;
    case 'list':
      await list_handler.processList(
        caller: caller,
        config: config,
        listFileName: job['file'] as String?,
      );
      break;
    case 'bookmark':
      await bookmark_handler.processBookmark(
        caller: caller,
        config: config,
      );
      break;
    case 'ranking':
      await ranking_handler.processRanking(
        caller: caller,
        config: config,
        mode: job['mode'] as String,
        content: job['content'] as String? ?? '',
      );
      break;
    case 'novel':
      await novel_handler.processNovel(
        caller: caller,
        config: config,
        novelId: job['novel_id'] as int,
      );
      break;
    case 'fanbox':
      await fanbox_handler.processFanboxArtist(
        caller: caller,
        config: config,
        artistId: job['artist_id'] as int,
        creatorId: job['creator_id'] as String?,
      );
      break;
    default:
      pixiv_helper.printAndLog('warn', 'Unknown batch job type: $type');
  }
}

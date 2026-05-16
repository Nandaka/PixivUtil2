/// Novel handler.
library;

import 'dart:io';

import '../common/pixiv_browser.dart';
import '../common/pixiv_config.dart';
import '../common/pixiv_helper.dart' as pixiv_helper;
import '../model/pixiv_novel.dart' as pixiv_novel;

Future<void> processNovel({
  required dynamic caller,
  required PixivConfig config,
  required int novelId,
  void Function({String? title, String? message, dynamic type})? notifier,
}) async {
  notifier ??= pixiv_helper.dummyNotifier;
  pixiv_helper.printAndLog('info', 'Processing Novel details: $novelId');

  final br = caller.br as PixivBrowser;
  final novel = await br.getNovelPage(novelId);
  pixiv_helper.printAndLog(null, 'Title : ${novel.imageTitle}');
  pixiv_helper.printAndLog(null, 'Tags  : ${novel.imageTags?.join(', ')}');
  pixiv_helper.printAndLog(null, 'Date  : ${novel.worksDateDateTime}');
  pixiv_helper.printAndLog(
      null, 'Bookmark Count : ${novel.bookmark_count}');

  final fileUrl = 'https://www.pixiv.net/ajax/novel/$novelId.html';
  var filename = pixiv_helper.makeFilename(
    config.filenameFormatNovel,
    novel,
    artistInfo: novel.artist,
    tagsSeparator: config.tagsSeparator,
    tagsLimit: config.tagsLimit,
    fileUrl: fileUrl,
    useTranslatedTag: config.useTranslatedTag,
    tagTranslationLocale: config.tagTranslationLocale,
  );
  filename = pixiv_helper.sanitizeFilename(filename, config.rootDirectory);
  pixiv_helper.printAndLog(null, 'Filename : $filename');
  await novel.writeContent(filename);

  if (config.setLastModified) {
    try {
      File(filename).setLastModifiedSync(novel.worksDateDateTime);
    } catch (_) {}
  }
}

Future<void> processNovelSeries({
  required dynamic caller,
  required PixivConfig config,
  required int seriesId,
  int startPage = 1,
  int endPage = 0,
  void Function({String? title, String? message, dynamic type})? notifier,
}) async {
  notifier ??= pixiv_helper.dummyNotifier;
  pixiv_helper.printAndLog('info', 'Processing Novel Series: $seriesId');

  final br = caller.br as PixivBrowser;
  final series = await br.getNovelSeries(seriesId);
  pixiv_helper.printAndLog(null, 'Series Name : ${series.seriesName}');
  pixiv_helper.printAndLog(null, 'Total Novel : ${series.total}');

  var page = startPage;
  while (true) {
    pixiv_helper.printAndLog(null, 'Getting page = $page');
    final body = await br.getContent(
        'https://www.pixiv.net/ajax/novel/series_content/$seriesId?limit=${pixiv_novel.MAX_LIMIT}&last_order=${(page - 1) * pixiv_novel.MAX_LIMIT}');
    series.parseSeriesContent(body, page);
    if (endPage > 0 && page > endPage) {
      pixiv_helper.printAndLog(null, 'Page limit reached = $endPage');
      break;
    }
    if (page * pixiv_novel.MAX_LIMIT >= series.total) {
      pixiv_helper.printAndLog(null, 'No more novel.');
      break;
    }
    page++;
  }

  for (final novel in series.seriesList) {
    await processNovel(
      caller: caller,
      config: config,
      novelId: int.parse('${(novel as Map)['id']}'),
      notifier: notifier,
    );
  }
}

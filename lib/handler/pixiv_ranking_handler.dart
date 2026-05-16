/// Ranking handler.
library;

import '../common/pixiv_browser.dart';
import '../common/pixiv_config.dart';
import '../common/pixiv_constant.dart' as pixiv_constant;
import '../common/pixiv_exception.dart';
import '../common/pixiv_helper.dart' as pixiv_helper;
import 'pixiv_image_handler.dart' as image_handler;

const int rankingOk = pixiv_constant.PIXIVUTIL_OK;

Future<void> processRanking({
  required dynamic caller,
  required PixivConfig config,
  required String mode,
  required String content,
  int startPage = 1,
  int endPage = 0,
  String date = '',
  List<String>? filter,
  void Function({String? title, String? message, dynamic type})? notifier,
}) async {
  notifier ??= pixiv_helper.dummyNotifier;
  pixiv_helper.printAndLog(
      'info', 'Processing Pixiv Ranking: $mode.');
  final br = caller.br as PixivBrowser;

  var currPage = startPage;
  while (true) {
    final titlePrefix =
        'Pixiv Ranking: $mode page $currPage and date $date';
    pixiv_helper.printAndLog(null, titlePrefix);
    final ranks =
        await br.getPixivRanking(mode, currPage, date, content, filter);
    pixiv_helper.printAndLog(null, 'Mode      : ${ranks.mode}');
    pixiv_helper.printAndLog(null, 'Total     : ${ranks.rankTotal}');
    pixiv_helper.printAndLog(null, 'Next Page : ${ranks.nextPage}');

    for (final post in ranks.contents) {
      try {
        final result = await image_handler.processImage(
          caller: caller,
          config: config,
          imageId: (post['illust_id'] as num).toInt(),
          userDir: config.rootDirectory,
          titlePrefix: titlePrefix,
          imageResponseCount: (post['rating_count'] as num? ?? 0).toInt(),
          notifier: notifier,
        );
        await pixiv_helper.wait(result, config);
      } on PixivException catch (e) {
        pixiv_helper.printAndLog(
            'error', 'Failed ranking image ${post['illust_id']}: $e');
      }
    }
    currPage++;
    if (endPage > 0 && currPage > endPage) break;
    if (ranks.nextPage is! int) break;
  }
}

Future<void> processNewIllusts({
  required dynamic caller,
  required PixivConfig config,
  String typeMode = 'illust',
  int maxPage = 0,
  void Function({String? title, String? message, dynamic type})? notifier,
}) async {
  notifier ??= pixiv_helper.dummyNotifier;
  final br = caller.br as PixivBrowser;
  var lastId = 0;
  var currentPage = 1;
  var i = 1;
  while (true) {
    final result = await br.getNewIllust(lastId,
        typeMode: typeMode, r18: config.r18mode);
    pixiv_helper.printAndLog(null,
        'Pixiv New Illusts: R-18=${config.r18mode} - page $currentPage');
    for (final image in result.images ?? const []) {
      final imageId = (image['id'] as num).toInt();
      pixiv_helper.printAndLog(null, '#$i - $imageId');
      try {
        final dl = await image_handler.processImage(
          caller: caller,
          config: config,
          imageId: imageId,
          userDir: config.rootDirectory,
          titlePrefix:
              'Pixiv New Illusts: R-18=${config.r18mode} - page $currentPage',
          notifier: notifier,
        );
        await pixiv_helper.wait(dl, config);
      } on PixivException catch (e) {
        pixiv_helper.printAndLog(
            'error', 'Failed new illusts image $imageId: $e');
      }
      i++;
    }
    lastId = result.lastId;
    currentPage++;
    if (maxPage != 0 && currentPage > maxPage) break;
    if (lastId == 0 || (result.images?.isEmpty ?? true)) break;
  }
}


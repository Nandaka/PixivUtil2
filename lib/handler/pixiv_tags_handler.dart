/// Tag-search handler.
library;

import '../common/pixiv_browser.dart';
import '../common/pixiv_config.dart';
import '../common/pixiv_helper.dart' as pixiv_helper;
import 'pixiv_image_handler.dart' as image_handler;

Future<void> processTags({
  required dynamic caller,
  required PixivConfig config,
  required String tags,
  int page = 1,
  int endPage = 0,
  bool wildCard = true,
  String? startDate,
  String? endDate,
  bool useTagsAsDir = false,
  int? bookmarkCount,
  String sortOrder = 'date_d',
  void Function({String? title, String? message, dynamic type})? notifier,
}) async {
  notifier ??= pixiv_helper.dummyNotifier;
  pixiv_helper.printAndLog(
      'info', 'Processing Tags: $tags (sort=$sortOrder)');
  final br = caller.br as PixivBrowser;
  var currentPage = page;
  while (true) {
    pixiv_helper.printAndLog(
        null, 'Search Page $currentPage for $tags');
    final result = await br.getSearchTagPage(
      tags,
      currentPage: currentPage,
      sortOrder: sortOrder,
      startDate: startDate,
      endDate: endDate,
      bookmarkCount: bookmarkCount,
    );
    result.printInfo();

    if (result.itemList == null || result.itemList!.isEmpty) break;
    var i = 1;
    for (final item in result.itemList!) {
      pixiv_helper.printAndLog(
          null, '#$i / ${result.itemList!.length} - ${item.imageId}');
      try {
        final dl = await image_handler.processImage(
          caller: caller,
          config: config,
          imageId: item.imageId,
          searchTags: tags,
          notifier: notifier,
        );
        await pixiv_helper.wait(dl, config);
      } catch (e) {
        pixiv_helper.printAndLog(
            'error', 'Failed tag image ${item.imageId}: $e');
      }
      i++;
    }

    if (result.isLastPage == true) break;
    currentPage++;
    if (endPage > 0 && currentPage > endPage) break;
  }
}

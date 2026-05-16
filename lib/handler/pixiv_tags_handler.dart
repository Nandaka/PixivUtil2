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
  bool titleCaption = false,
  String? startDate,
  String? endDate,
  bool useTagsAsDir = false,
  int? memberId,
  int? bookmarkCount,
  String sortOrder = 'date_d',
  void Function({String? title, String? message, dynamic type})? notifier,
}) async {
  notifier ??= pixiv_helper.dummyNotifier;
  pixiv_helper.printAndLog('info', 'Processing Tags: $tags (sort=$sortOrder)');
  final br = caller.br as PixivBrowser;
  var currentPage = page;
  while (true) {
    pixiv_helper.printAndLog(null, 'Search Page $currentPage for $tags');
    final result = await br.getSearchTagPage(
      tags,
      currentPage: currentPage,
      wildCardSearch: wildCard,
      titleCaption: titleCaption,
      sortOrder: sortOrder,
      startDate: startDate,
      endDate: endDate,
      memberId: memberId,
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

Future<void> processTagMetadata({
  required dynamic caller,
  required PixivConfig config,
  required String tags,
  String filterMode = 'none',
  void Function({String? title, String? message, dynamic type})? notifier,
}) async {
  notifier ??= pixiv_helper.dummyNotifier;
  final br = caller.br as PixivBrowser;
  final tagsList = tags
      .split(',')
      .map((tag) => tag.trim())
      .where((tag) => tag.isNotEmpty)
      .toList();

  for (final tag in tagsList) {
    final msg = 'Processing Tag Metadata: $tag';
    pixiv_helper.printAndLog('info', msg);
    notifier(type: 'TAG', message: msg);
    try {
      final tagInfo =
          await br.getTagInfo(tag, lang: config.tagTranslationLocale);
      final tagId = tagInfo.tag.isNotEmpty
          ? tagInfo.tag
          : (tagInfo.word.isNotEmpty ? tagInfo.word : tag);
      final hasPixpedia =
          tagInfo.pixpedia != null && tagInfo.pixpedia!.tag.isNotEmpty;
      final hasTranslation = tagInfo.tagTranslation.isNotEmpty;
      if (filterMode == 'pixpedia' && !hasPixpedia) continue;
      if (filterMode == 'translation' && !hasTranslation) continue;
      if (filterMode == 'pixpedia_or_translation' &&
          !(hasPixpedia || hasTranslation)) {
        continue;
      }

      caller.dbManager.insertTag(tagId);
      caller.dbManager.updateTag(tagId);
      for (final entry in tagInfo.tagTranslation.entries) {
        final sourceTag = entry.key;
        if (sourceTag.isEmpty) continue;
        caller.dbManager.insertTag(sourceTag);
        caller.dbManager.updateTag(sourceTag);
        final translations = entry.value;
        if (translations is Map) {
          for (final translation in translations.entries) {
            final locale = '${translation.key}';
            final value = '${translation.value}';
            if (value.isNotEmpty) {
              caller.dbManager.insertTagTranslation(sourceTag, locale, value);
            }
          }
        }
      }
    } catch (e) {
      pixiv_helper.printAndLog(
          'error', 'Error at process_tag_metadata(): $tag');
      pixiv_helper.printAndLog('error', 'Exception: $e');
    }
  }
}

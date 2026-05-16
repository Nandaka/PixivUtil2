/// Fanbox handler.
library;

import '../common/pixiv_browser.dart';
import '../common/pixiv_config.dart';
import '../common/pixiv_helper.dart' as pixiv_helper;
import 'pixiv_download_handler.dart' as download_handler;

Future<void> processFanboxArtist({
  required dynamic caller,
  required PixivConfig config,
  required int artistId,
  String? creatorId,
  int endPage = 0,
  void Function({String? title, String? message, dynamic type})? notifier,
}) async {
  notifier ??= pixiv_helper.dummyNotifier;
  pixiv_helper.printAndLog(
      'info', 'Processing Fanbox artist: $artistId ($creatorId)');
  final br = caller.br as PixivBrowser;
  final artist = await br.getFanboxArtist(artistId, creatorId: creatorId);
  pixiv_helper.printAndLog(null, 'Artist : $artist');
  final posts = await br.getFanboxPosts(artist);

  var i = 1;
  for (final post in posts) {
    pixiv_helper.printAndLog(null, '#$i / ${posts.length} - $post');
    for (var j = 0; j < post.images.length; j++) {
      final url = post.images[j];
      final filename = pixiv_helper.makeFilename(
        config.filenameFormatFanboxContent,
        post,
        artistInfo: artist,
        tagsSeparator: config.tagsSeparator,
        tagsLimit: config.tagsLimit,
        fileUrl: url,
      );
      final fullPath =
          pixiv_helper.sanitizeFilename(filename, config.rootDirectory);
      pixiv_helper.printAndLog(null, '  -> $fullPath');
      await download_handler.downloadImage(
        caller: caller,
        config: config,
        url: url,
        filename: fullPath,
        referer: 'https://www.fanbox.cc/',
      );
    }
    i++;
  }
}

Future<void> processFanboxFollowList({
  required dynamic caller,
  required PixivConfig config,
}) async {
  pixiv_helper.printAndLog(
      'info', 'Processing Fanbox follow list (not yet implemented).');
}

Future<void> processFanboxPost({
  required dynamic caller,
  required PixivConfig config,
  required int postId,
}) async {
  pixiv_helper.printAndLog('info', 'Processing Fanbox post: $postId');
  final br = caller.br as PixivBrowser;
  final body = await br.getContent(
      'https://api.fanbox.cc/post.info?postId=$postId',
      headers: {
        'Origin': 'https://www.fanbox.cc',
        'Referer': 'https://www.fanbox.cc/',
      });
  pixiv_helper.printAndLog(null, body.length > 200 ? '${body.substring(0, 200)}...' : body);
}

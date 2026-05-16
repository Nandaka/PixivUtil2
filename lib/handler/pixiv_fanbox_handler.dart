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
  final post = await br.getFanboxPostById(postId);
  final artist = post.parent;
  pixiv_helper.printAndLog(null, 'Post : $post');

  if (artist != null) {
    caller.dbManager.insertFanboxPost(
      memberId: artist.artistId,
      postId: post.imageId,
      title: post.imageTitle,
      feeRequired: post.feeRequired,
      publishedDate: post.worksDate,
      updatedDate: post.updatedDate,
      postType: post.type,
    );
  }

  if (post.coverImageUrl.isNotEmpty) {
    final fakeUrl = post.coverImageUrl.replaceAll(
      '${post.imageId}/cover/',
      '${post.imageId}_',
    );
    final filename = pixiv_helper.makeFilename(
      config.filenameFormatFanboxCover,
      post,
      artistInfo: artist,
      tagsSeparator: config.tagsSeparator,
      tagsLimit: config.tagsLimit,
      fileUrl: fakeUrl,
    );
    final fullPath = pixiv_helper.sanitizeFilename(
      filename,
      config.rootDirectory,
    );
    pixiv_helper.printAndLog(null, 'Cover -> $fullPath');
    await download_handler.downloadImage(
      caller: caller,
      config: config,
      url: post.coverImageUrl,
      filename: fullPath,
      referer: 'https://www.fanbox.cc/posts/${post.imageId}',
    );
  }

  if (post.isRestricted) {
    pixiv_helper.printAndLog(
        'info', 'Skipping post ${post.imageId} due to restricted post.');
    return;
  }

  pixiv_helper.printAndLog(null, 'Image Count = ${post.images.length}');
  for (var i = 0; i < post.images.length; i++) {
    final url = post.images[i];
    final fakeUrl =
        url.replaceAll('${post.imageId}/', '${post.imageId}_p${i}_');
    final filename = pixiv_helper.makeFilename(
      config.filenameFormatFanboxContent,
      post,
      artistInfo: artist,
      tagsSeparator: config.tagsSeparator,
      tagsLimit: config.tagsLimit,
      fileUrl: fakeUrl,
    );
    final fullPath =
        pixiv_helper.sanitizeFilename(filename, config.rootDirectory);
    post.linkToFile?[url] = fullPath;
    pixiv_helper.printAndLog(null, 'Downloading image $i from $url');
    pixiv_helper.printAndLog(null, 'Saved to $fullPath');
    await download_handler.downloadImage(
      caller: caller,
      config: config,
      url: url,
      filename: fullPath,
      referer: 'https://www.fanbox.cc/posts/${post.imageId}',
    );
  }

  if (config.writeImageInfo) {
    final filename = pixiv_helper.makeFilename(
      config.filenameFormatFanboxInfo,
      post,
      artistInfo: artist,
      tagsSeparator: config.tagsSeparator,
      tagsLimit: config.tagsLimit,
      fileUrl: '${post.imageId}',
      appendExtension: false,
    );
    final fullPath =
        pixiv_helper.sanitizeFilename('$filename.txt', config.rootDirectory);
    await post.writeInfo(fullPath);
  }
}

/// Pixiv Sketch handler.
library;

import '../common/pixiv_browser.dart';
import '../common/pixiv_config.dart';
import '../common/pixiv_helper.dart' as pixiv_helper;
import 'pixiv_download_handler.dart' as download_handler;

Future<void> processSketchArtists({
  required dynamic caller,
  required PixivConfig config,
  required String artistToken,
  String titlePrefix = '',
  int endPage = 0,
}) async {
  pixiv_helper.printAndLog(
      'info', '${titlePrefix}Processing Sketch artist: $artistToken');
  final br = caller.br as PixivBrowser;
  final artist = await br.getSketchArtist(artistToken);
  pixiv_helper.printAndLog(null, 'Artist : $artist');
  await br.getSketchPosts(artist);

  for (final post in artist.posts) {
    pixiv_helper.printAndLog(null, 'Post: $post');
    for (var i = 0; i < post.imageUrls.length; i++) {
      final url = post.imageUrls[i];
      final filename = pixiv_helper.makeFilename(
        config.filenameFormatSketch,
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
        referer: 'https://sketch.pixiv.net/',
      );
    }
  }
}

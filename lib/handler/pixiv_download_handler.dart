/// Image-download handler: downloads files with retry, size checks, and
/// last-modified preservation.
library;

import 'dart:async';
import 'dart:io';

import '../common/pixiv_browser.dart';
import '../common/pixiv_config.dart';
import '../common/pixiv_constant.dart' as pixiv_constant;
import '../common/pixiv_exception.dart';
import '../common/pixiv_helper.dart' as pixiv_helper;

/// Downloads an image at [url] to [filename]. Returns one of the
/// `PIXIVUTIL_*` constants from [pixiv_constant].
Future<int> downloadImage({
  required dynamic caller,
  required PixivConfig config,
  required String url,
  required String filename,
  String referer = 'https://www.pixiv.net',
  int retry = 0,
}) async {
  retry = retry == 0 ? config.retry : retry;
  final br = caller.br as PixivBrowser;

  final f = File(filename);
  if (await f.exists() &&
      !config.overwrite &&
      !config.alwaysCheckFileSize) {
    pixiv_helper.printAndLog(
        'warn', 'File already exists: $filename - skipped.');
    return pixiv_constant.PIXIVUTIL_SKIP_DUPLICATE;
  }

  await pixiv_helper.makeSubdirs(filename);

  for (var attempt = 0; attempt < retry; attempt++) {
    try {
      final start = DateTime.now();
      final bytes = await br.downloadFile(url, filename, headers: {
        'Referer': referer,
      });
      final elapsed = DateTime.now().difference(start).inMilliseconds / 1000.0;
      pixiv_helper.printAndLog(
          'info',
          'Downloaded ${pixiv_helper.sizeInStr(bytes)} '
          'in ${elapsed.toStringAsFixed(2)}s '
          '(${pixiv_helper.speedInStr(bytes, elapsed)}) -> $filename');

      if (config.minFileSize > 0 && bytes < config.minFileSize) {
        pixiv_helper.printAndLog(
            'warn', 'File smaller than min ($bytes < ${config.minFileSize})');
        await f.delete();
        return pixiv_constant.PIXIVUTIL_SIZE_LIMIT_SMALLER;
      }
      if (config.maxFileSize > 0 && bytes > config.maxFileSize) {
        pixiv_helper.printAndLog(
            'warn', 'File larger than max ($bytes > ${config.maxFileSize})');
        await f.delete();
        return pixiv_constant.PIXIVUTIL_SIZE_LIMIT_LARGER;
      }
      return pixiv_constant.PIXIVUTIL_OK;
    } on PixivException catch (e) {
      pixiv_helper.printAndLog('warn',
          'Download attempt ${attempt + 1}/$retry failed for $url: $e');
      if (attempt + 1 >= retry) {
        return pixiv_constant.PIXIVUTIL_NOT_OK;
      }
      await Future<void>.delayed(Duration(seconds: config.retryWait));
    } on TimeoutException {
      pixiv_helper.printAndLog('warn',
          'Timeout on attempt ${attempt + 1}/$retry: $url');
      await Future<void>.delayed(Duration(seconds: config.retryWait));
    } on SocketException catch (e) {
      pixiv_helper.printAndLog('warn',
          'Network error on attempt ${attempt + 1}/$retry: ${e.message}');
      await Future<void>.delayed(Duration(seconds: config.retryWait));
    }
  }
  return pixiv_constant.PIXIVUTIL_NOT_OK;
}

/// Verifies an image: stub that just checks the file exists and is non-empty.
Future<bool> verifyImage(String filename) async {
  final f = File(filename);
  if (!await f.exists()) return false;
  final size = await f.length();
  return size > 0;
}

/// Process a post-download callback.
Future<void> postProcess(PixivConfig config, String filename) async {
  if (!config.enablePostProcessing || config.postProcessingCmd.isEmpty) return;
  final cmd = config.postProcessingCmd
      .replaceAll('%filename%', filename)
      .split(' ');
  await Process.run(cmd.first, cmd.skip(1).toList());
}

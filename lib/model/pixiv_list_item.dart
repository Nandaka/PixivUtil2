/// PixivListItem: items within a `list.txt` file.
library;

import 'dart:io';

import 'package:path/path.dart' as p;

import '../common/pixiv_exception.dart';
import '../common/pixiv_helper.dart' as pixiv_helper;

class PixivListItem {
  final int memberId;
  String path;

  PixivListItem(int memberId, String pathInput)
      : memberId = memberId,
        path = pathInput.trim() == r'N\A' ? '' : pathInput.trim();

  @override
  String toString() => "(id:$memberId, path:'$path')";

  /// Parse a `list.txt` file into PixivListItem objects.
  static Future<List<PixivListItem>> parseList(
    String filename, [
    String? rootDir,
  ]) async {
    final members = <PixivListItem>[];
    if (!await File(filename).exists()) {
      throw PixivException(
        "File doesn't exists or no permission to read: $filename",
        errorCode: PixivException.FILE_NOT_EXISTS_OR_NO_WRITE_PERMISSION,
      );
    }
    final lines = await pixiv_helper.openTextFileLines(filename);
    var lineNo = 1;
    var originalLine = '';
    try {
      for (var line in lines) {
        originalLine = line;
        if (line.startsWith('#') || line.isEmpty) continue;
        if (line.trim().isEmpty) continue;
        line = line.trim();
        final items = line.split(RegExp(r'\s+'));
        int memberId;

        if (items[0].startsWith('http')) {
          final parsed = Uri.parse(items[0]);
          if (parsed.path == '/member.php' ||
              parsed.path == '/member_illust.php') {
            final id = parsed.queryParameters['id'];
            if (id != null) {
              memberId = int.parse(id);
            } else {
              pixiv_helper.printAndLog(
                  'error', 'Cannot detect member id from url: ${items[0]}');
              continue;
            }
          } else {
            pixiv_helper.printAndLog(
                'error', 'Unsupported url detected: ${items[0]}');
            continue;
          }
        } else {
          memberId = int.parse(items[0]);
        }

        var path = '';
        if (items.length > 1) {
          path = items.sublist(1).join(' ').trim();
          path = path.replaceAll('"', '');
          if (rootDir != null) {
            path = path.replaceAll('%root%', rootDir);
          } else {
            path = path.replaceAll('%root%', '');
          }
          path = p.absolute(path);
          path = pixiv_helper.sanitizeFilename(path, rootDir);
          path = path.replaceAll(r'\\', r'\');
          path = path.replaceAll(r'\', Platform.pathSeparator);
        }
        members.add(PixivListItem(memberId, path));
        lineNo++;
        originalLine = '';
      }
    } catch (e) {
      pixiv_helper.printAndLog('error',
          'Invalid value: $originalLine at line $lineNo: $e');
    }
    return members;
  }
}

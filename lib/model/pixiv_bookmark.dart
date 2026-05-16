/// PixivBookmark: parsing favorites/bookmarks.
library;

import 'dart:convert';
import 'dart:io';

import 'package:html/parser.dart' as html_parser;

import '../common/pixiv_exception.dart';

class PixivBookmark {
  /// Parse a "favorites" page (list of artists). [parseUtilities.selectMember]
  /// is used to look each member up in the database; we keep the same flow
  /// here using the provided db instance.
  static Future<List<dynamic>> parseBookmark(
    String page, {
    required String rootDirectory,
    required String dbPath,
    String locale = '',
    bool isJson = false,
    Future<dynamic> Function(String memberId)? selectMember,
  }) async {
    final result2 = <String>[];

    if (isJson) {
      final parsed = jsonDecode(page) as Map<String, dynamic>;
      for (final member in parsed['body']['users'] as List) {
        if (member is Map && member['isAdContainer'] == true) continue;
        result2.add('${member['userId']}');
      }
    } else {
      final parsePage = html_parser.parse(page);
      final memberRe = RegExp('$locale/users/(\\d*)');
      final memberList = parsePage.querySelector('.members');
      if (memberList != null) {
        final anchors = memberList.querySelectorAll('a');
        final seen = <String, String>{};
        for (final a in anchors) {
          final href = a.attributes['href'] ?? '';
          final m = memberRe.firstMatch(href);
          if (m != null) {
            seen[m.group(1)!] = m.group(1)!;
          }
        }
        result2.addAll(seen.keys);
      }
    }

    final bookmarks = <dynamic>[];
    for (final r in result2) {
      if (selectMember != null) {
        bookmarks.add(await selectMember(r));
      } else {
        bookmarks.add(r);
      }
    }
    return bookmarks;
  }

  /// Parse the JSON bookmarks page, returning [imageIds, totalImages].
  static (List<int>, int) parseImageBookmark(String page,
      {String? imageTagsFilter}) {
    final imageList = <int>[];
    final imageBookmark = jsonDecode(page) as Map<String, dynamic>;
    final total = (imageBookmark['body']['total'] as num).toInt();
    for (final work in imageBookmark['body']['works'] as List) {
      if (work is Map && work['isAdContainer'] == true) continue;

      var skip = true;
      if (imageTagsFilter != null) {
        final tags = work['tags'] as List? ?? const [];
        for (final tag in tags) {
          if (tag == imageTagsFilter) {
            skip = false;
            break;
          }
        }
        if (skip) continue;
      }
      if (work['illustId'] != null) {
        imageList.add(int.parse('${work['illustId']}'));
      } else if (work['id'] != null) {
        imageList.add(int.parse('${work['id']}'));
      }
    }
    return (imageList, total);
  }

  static Future<void> exportList(
      List<dynamic> lst, String filename) async {
    var path = filename;
    if (!path.endsWith('.txt')) path = '$path.txt';
    final f = File(path).openWrite(encoding: utf8);
    f.writeln('###Export members date: ${DateTime.now()} ###');
    for (final item in lst) {
      var data = '${item.memberId}';
      if ((item.path as String).isNotEmpty) {
        data = '$data ${item.path}';
      }
      f.writeln(data);
    }
    f.write('###END-OF-FILE###');
    await f.close();
  }

  static Future<void> exportImageList(List lst, String filename) async {
    var path = filename;
    if (!path.endsWith('.txt')) path = '$path.txt';
    final f = File(path).openWrite(encoding: utf8);
    f.writeln('###Export images date: ${DateTime.now()} ###');
    for (final item in lst) {
      f.writeln('$item');
    }
    f.write('###END-OF-FILE###');
    await f.close();
  }
}

class PixivNewIllustBookmark {
  List<int> imageList = [];
  bool? isLastPage;
  bool haveImages = false;

  PixivNewIllustBookmark(String page) {
    _parse(page);
    haveImages = imageList.isNotEmpty;
  }

  void _parse(String page) {
    final pageJson = jsonDecode(page) as Map<String, dynamic>;
    if (pageJson['error'] == true) {
      throw PixivException(
        '${pageJson['message']}',
        errorCode: PixivException.OTHER_ERROR,
      );
    }
    for (final id in pageJson['body']['page']['ids'] as List) {
      imageList.add(int.parse('$id'));
    }
  }
}

/// PixivRanking + PixivNewIllust models.
library;

import 'dart:convert';

import '../common/pixiv_exception.dart';

class PixivRanking {
  String mode = '';
  int currPage = 0;
  dynamic nextPage;
  dynamic prevPage;
  String currDate = '';
  dynamic nextDate;
  dynamic prevDate;
  int rankTotal = 0;
  List<dynamic> contents = [];
  List<String>? filters;

  PixivRanking(String jsStr, this.filters) {
    final data = jsonDecode(jsStr) as Map<String, dynamic>;
    mode = data['mode'] as String;
    currDate = data['date'] as String;
    nextDate = data['next_date'];
    prevDate = data['prev_date'];
    currPage = (data['page'] as num).toInt();
    nextPage = data['next'];
    prevPage = data['prev'];
    rankTotal = (data['rank_total'] as num).toInt();
    contents = data['contents'] as List;

    if (filters != null) filterContents();
  }

  void filterContents() {
    contents.removeWhere((content) {
      for (final f in filters!) {
        if ((content['illust_content_type'] as Map)[f] == true) {
          return true;
        }
      }
      return false;
    });
  }
}

class PixivNewIllust {
  int lastId = 0;
  List<dynamic>? images;
  String? typeMode;

  PixivNewIllust(String jsStr, String typeMode) {
    this.typeMode = typeMode;
    final data = jsonDecode(jsStr) as Map<String, dynamic>;
    if (data['error'] == true) {
      throw PixivException(
        '${data['message']}',
        errorCode: PixivException.OTHER_ERROR,
      );
    }
    lastId = (data['body']['lastId'] as num).toInt();
    images = data['body']['illusts'] as List;
  }
}

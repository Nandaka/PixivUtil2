/// Custom exception used by PixivUtil2.
class PixivException implements Exception {
  // Error Codes
  static const int NOT_LOGGED_IN = 100;
  static const int CANNOT_LOGIN = 1005;
  static const int USER_ID_NOT_EXISTS = 1001;
  static const int USER_ID_SUSPENDED = 1002;
  static const int OTHER_MEMBER_ERROR = 1003;
  static const int NO_IMAGES = 1004;

  static const int PARSE_TOKEN_DIFFERENT_IMAGE_STRUCTURE = 1005;
  static const int PARSE_TOKEN_NO_IMAGES = 1006;
  static const int NO_PAGE_GIVEN = 1007;

  static const int OAUTH_LOGIN_ISSUE = 1508;

  static const int FILE_NOT_EXISTS_OR_NO_WRITE_PERMISSION = 4002;
  static const int FILE_NOT_EXISTS_OR_NO_PERMISSION = 4001;

  static const int OTHER_IMAGE_ERROR = 2001;
  static const int NOT_IN_MYPICK = 2002;
  static const int NO_APPROPRIATE_LEVEL = 2003;
  static const int IMAGE_DELETED = 2004;
  static const int R_18_DISABLED = 2005;
  static const int UNKNOWN_IMAGE_ERROR = 2006;
  static const int UGOIRA_CONVERSION_ERROR = 2007;

  static const int DOWNLOAD_FAILED_OTHER = 9000;
  static const int DOWNLOAD_FAILED_IO = 9001;
  static const int DOWNLOAD_FAILED_NETWORK = 9002;
  static const int SERVER_ERROR = 9005;

  static const int MISSING_CONFIG = 9901;
  static const int OTHER_ERROR = 9999;

  final String message;
  final int errorCode;
  final dynamic htmlPage;

  PixivException(this.message, {this.errorCode = 0, this.htmlPage});

  @override
  String toString() {
    final hasPage = (htmlPage != null && htmlPage.toString().isNotEmpty)
        ? 'Y'
        : 'N';
    return 'PixivException($errorCode $message, hasDumpPage=$hasPage)';
  }
}

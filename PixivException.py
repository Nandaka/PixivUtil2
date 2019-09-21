# -*- coding: utf-8 -*-


class PixivException(Exception):
    # Error Codes
    NOT_LOGGED_IN      = 100
    CANNOT_LOGIN       = 1005
    USER_ID_NOT_EXISTS = 1001
    USER_ID_SUSPENDED  = 1002
    OTHER_MEMBER_ERROR = 1003
    NO_IMAGES          = 1004

    PARSE_TOKEN_DIFFERENT_IMAGE_STRUCTURE = 1005
    PARSE_TOKEN_NO_IMAGES                 = 1006
    NO_PAGE_GIVEN                         = 1007

    OAUTH_LOGIN_ISSUE  = 1508

    FILE_NOT_EXISTS_OR_NO_WRITE_PERMISSION = 4002
    FILE_NOT_EXISTS_OR_NO_READ_PERMISSION  = 4001

    OTHER_IMAGE_ERROR    = 2001
    NOT_IN_MYPICK        = 2002
    NO_APPROPRIATE_LEVEL = 2003
    IMAGE_DELETED        = 2004
    R_18_DISABLED        = 2005
    UNKNOWN_IMAGE_ERROR  = 2006

    DOWNLOAD_FAILED_OTHER = 9000
    DOWNLOAD_FAILED_IO = 9001
    DOWNLOAD_FAILED_NETWORK = 9002
    SERVER_ERROR  = 9005

    MISSING_CONFIG = 9901
    OTHER_ERROR = 9999

    errorCode = -1
    htmlPage = None

    def __init__(self, message, errorCode=0, htmlPage=None):
        super(PixivException, self).__init__(message)
        self.value = message
        self.message = message
        self.errorCode = errorCode
        self.htmlPage = htmlPage

    def __str__(self):
        import PixivHelper
        # return str(self.errorCode) + " " + repr(self.value)
        has_page = "Y" if self.htmlPage is not None and len(self.htmlPage) > 0 else "N"
        return PixivHelper.toUnicode("{0} {1}, hasDumpPage={2}".format(self.errorCode, self.value, has_page))

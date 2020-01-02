# -*- coding: utf-8 -*-
# pylint: disable=I0011, C, C0302

import os
import re
from urllib import parse

import PixivHelper
from PixivException import PixivException


class PixivListItem(object):
    '''Class for item in list.txt'''
    memberId = ""
    path = ""

    def __init__(self, memberId, path):
        self.memberId = int(memberId)
        self.path = path.strip()
        if self.path == r"N\A":
            self.path = ""

    def __repr__(self):
        return "(id:{0}, path:'{1}')".format(self.memberId, self.path)

    @staticmethod
    def parseList(filename, rootDir=None):
        '''read list.txt and return the list of PixivListItem'''
        members = list()

        if not os.path.exists(filename):
            raise PixivException("File doesn't exists or no permission to read: " + filename,
                                 errorCode=PixivException.FILE_NOT_EXISTS_OR_NO_WRITE_PERMISSION)

        reader = PixivHelper.open_text_file(filename)
        line_no = 1
        try:
            for line in reader:
                original_line = line
                # PixivHelper.safePrint("Processing: " + line)
                if line.startswith('#') or len(line) < 1:
                    continue
                if len(line.strip()) == 0:
                    continue
                # line = PixivHelper.toUnicode(line)
                line = line.strip()
                items = line.split(None, 1)

                if items[0].startswith("http"):
                    # handle urls:
                    # http://www.pixiv.net/member_illust.php?id=<member_id>
                    # http://www.pixiv.net/member.php?id=<member_id>
                    parsed = parse.urlparse(items[0])
                    if parsed.path == "/member.php" or parsed.path == "/member_illust.php":
                        query_str = parse.parse_qs(parsed.query)
                        if 'id' in query_str:
                            member_id = int(query_str["id"][0])
                        else:
                            PixivHelper.print_and_log(
                                'error', "Cannot detect member id from url: " + items[0])
                            continue
                    else:
                        PixivHelper.print_and_log(
                            'error', "Unsupported url detected: " + items[0])
                        continue

                else:
                    # handle member id directly
                    member_id = int(items[0])

                path = ""
                if len(items) > 1:
                    path = items[1].strip()

                    path = path.replace('\"', '')
                    if rootDir is not None:
                        path = path.replace('%root%', rootDir)
                    else:
                        path = path.replace('%root%', '')

                    path = os.path.abspath(path)
                    # have drive letter
                    if re.match(r'[a-zA-Z]:', path):
                        dirpath = path.split(os.sep, 1)
                        dirpath[1] = PixivHelper.sanitize_filename(
                            dirpath[1], None)
                        path = os.sep.join(dirpath)
                    else:
                        path = PixivHelper.sanitize_filename(path, rootDir)

                    path = path.replace('\\\\', '\\')
                    path = path.replace('\\', os.sep)

                list_item = PixivListItem(member_id, path)
                # PixivHelper.safePrint(u"- {0} ==> {1} ".format(member_id, path))
                members.append(list_item)
                line_no = line_no + 1
                original_line = ""
        except UnicodeDecodeError:
            PixivHelper.get_logger().exception("PixivListItem.parseList(): Invalid value when parsing list")
            PixivHelper.print_and_log('error', 'Invalid value: {0} at line {1}, try to save the list.txt in UTF-8.'.format(
                                      original_line, line_no))
        except BaseException:
            PixivHelper.get_logger().exception("PixivListItem.parseList(): Invalid value when parsing list")
            PixivHelper.print_and_log('error', 'Invalid value: {0} at line {1}'.format(original_line, line_no))

        reader.close()
        return members

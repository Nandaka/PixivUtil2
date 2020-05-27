# -*- coding: utf-8 -*-

import os

import demjson

import PixivArtistHandler
import PixivHelper
import PixivImageHandler
import PixivTagsHandler
import PixivUtil2

_default_batch_filename = "./batch_job.json"


class JobOption(object):
    filenameFormat = ""
    filenameMangaFormat = ""
    filenameInfoFormat = ""
    filenameMangaInfoFormat = ""
    avatarNameFormat = ""
    rootDirectory = ""
    useTagsAsDir = False
    r18mode = False

    def __init__(self, job, _config):
        if _config is None:
            raise Exception("Cannot get default configuration, aborting...")
        # set default option from config
        self.filenameFormat = _config.filenameFormat
        self.filenameMangaFormat = _config.filenameMangaFormat
        self.filenameInfoFormat = _config.filenameInfoFormat
        self.filenameMangaInfoFormat = _config.filenameMangaInfoFormat
        self.avatarNameFormat = _config.avatarNameFormat
        self.rootDirectory = _config.rootDirectory
        self.useTagsAsDir = _config.useTagsAsDir
        self.r18mode = _config.r18mode

        if "option" in job and job["option"] is not None:
            # need to check if the job option exists for each option
            option_data = job["option"]
            if "filenameFormat" in option_data:
                self.filenameFormat = option_data["filenameFormat"]
            if "filenameMangaFormat" in option_data:
                self.filenameMangaFormat = option_data["filenameMangaFormat"]
            if "filenameInfoFormat" in option_data:
                self.filenameInfoFormat = option_data["filenameInfoFormat"]
            if "filenameMangaInfoFormat" in option_data:
                self.filenameMangaInfoFormat = option_data["filenameMangaInfoFormat"]
            if "avatarNameFormat" in option_data:
                self.avatarNameFormat = option_data["avatarNameFormat"]
            if "rootDirectory" in option_data:
                self.rootDirectory = option_data["rootDirectory"]
            if "useTagsAsDir" in option_data:
                self.useTagsAsDir = option_data["useTagsAsDir"]
            if "r18mode" in option_data:
                self.r18mode = option_data["r18mode"]


def handle_members(caller, job, job_name, job_option):
    member_ids = list()
    if "member_ids" in job:
        print("Multi Member IDs")
        member_ids = job["member_ids"]
    elif "member_id" in job:
        member_id = job["member_id"]
        member_ids.append(member_id)
    else:
        print(f"No member_id or member_ids found in {job_name}!")
        return

    start_page = 1
    if "start_page" in job:
        start_page = int(job["start_page"])
    end_page = 0
    if "end_page" in job:
        end_page = int(job["end_page"])
    from_bookmark = False
    if "from_bookmark" in job:
        from_bookmark = bool(job["from_bookmark"])
    tags = None
    if "tags" in job and len(job["tags"]) > 0:
        tags = job["tags"]

    for member_id in member_ids:
        PixivArtistHandler.process_member(caller,
                                          member_id=member_id,
                                          user_dir=job_option.rootDirectory,
                                          page=start_page,
                                          end_page=end_page,
                                          bookmark=from_bookmark,
                                          tags=tags,
                                          title_prefix=job_name,
                                          job_option=job_option)


def handle_images(caller: PixivUtil2, job, job_name, job_option):
    image_ids = list()
    if "image_ids" in job:
        image_ids = job["image_ids"]
        print(f"Found multiple images: {len(image_ids)}")
    elif "image_id" in job:
        image_id = job["image_id"]
        image_ids.append(image_id)
    else:
        print(f"No image_id or image_ids found in {job_name}!")
        return

    for image_id in image_ids:
        PixivImageHandler.process_image(caller,
                                        image_id=image_id,
                                        user_dir=job_option.rootDirectory,
                                        title_prefix=job_name,
                                        job_option=job_option)
    print("done.")


def handle_tags(caller, job, job_name, job_option):
    if "tags" in job and len(job["tags"]) > 0:
        tags = job["tags"]
    else:
        print(f"No tags found or empty tags in {job_name}!")

    start_page = 1
    if "start_page" in job:
        start_page = int(job["start_page"])
    end_page = 0
    if "end_page" in job:
        end_page = int(job["end_page"])
    wild_card = True
    if "wild_card" in job:
        wild_card = bool(job["wild_card"])
    title_caption = False
    if "title_caption" in job:
        title_caption = bool(job["title_caption"])
    start_date = None
    if "start_date" in job and len(job["start_date"]) == 10:
        try:
            start_date = PixivHelper.check_date_time(job["start_date"])
        except BaseException:
            raise Exception(f"Invalid start_date: {job['start_date']} in {job_name}.")
    end_date = None
    if "end_date" in job and len(job["end_date"]) == 10:
        try:
            end_date = PixivHelper.check_date_time(job["end_date"])
        except BaseException:
            raise Exception(f"Invalid end_date: {job['end_date']} in {job_name}.")
    member_id = None
    if "member_id" in job:
        member_id = bool(job["member_id"])
    bookmark_count = None
    if "bookmark_count" in job:
        bookmark_count = int(job["bookmark_count"])
    oldest_first = False
    if "oldest_first" in job:
        oldest_first = bool(job["oldest_first"])
    type_mode = "a"
    if "type_mode" in job:
        if job["type_mode"] in {'a', 'i', 'm'}:
            type_mode = job["type_mode"]
        else:
            raise Exception(f"Invalid type_mode: {job['type_mode']} in {job_name}.")

    PixivTagsHandler.process_tags(caller,
                                  tags,
                                  page=start_page,
                                  end_page=end_page,
                                  wild_card=wild_card,
                                  title_caption=title_caption,
                                  start_date=start_date,
                                  end_date=end_date,
                                  use_tags_as_dir=job_option.useTagsAsDir,
                                  member_id=member_id,
                                  bookmark_count=bookmark_count,
                                  oldest_first=oldest_first,
                                  type_mode=type_mode,
                                  job_option=job_option)


def process_batch_job(caller: PixivUtil2):
    caller.set_console_title("Batch Menu")
    if os.path.exists(_default_batch_filename):
        jobs_file = open(_default_batch_filename, encoding="utf-8")
        jobs = demjson.decode(jobs_file.read())
        for job_name in jobs["jobs"]:
            print(f"Processing {job_name}")
            curr_job = jobs["jobs"][job_name]

            if "enabled" not in curr_job or not bool(curr_job["enabled"]):
                print(f"Skipping {job_name} because not enabled.")
                continue

            if "job_type" not in curr_job:
                print(f"Cannot find job_type in {job_name}")
                continue

            job_option = JobOption(curr_job, caller.__config__)
            if curr_job["job_type"] == '1':
                handle_members(caller, curr_job, job_name, job_option)
            elif curr_job["job_type"] == '2':
                handle_images(caller, curr_job, job_name, job_option)
            elif curr_job["job_type"] == '3':
                handle_tags(caller, curr_job, job_name, job_option)
            else:
                print(f"Unsupported job_type {curr_job['job_type']} in {job_name}")
    else:
        print(f"Cannot found {_default_batch_filename} in the application folder, see https://github.com/Nandaka/PixivUtil2/wiki/Using-Batch-Job-(Experimental) for example. ")

    # restore original method
    # PixivHelper.print_and_log = temp_printer


def notifier(level, msg, exception=None, newline=True, end=None):
    if level is None:
        level = ""
    if level == "debug":
        return
    msg = msg.replace("\n", "")
    msg = "{0:5} - {1}".format(level, msg)
    msg = msg.ljust(150)
    print(msg, end='\r')


if __name__ == '__main__':
    import PixivUtil2
    process_batch_job(PixivUtil2)

# -*- coding: utf-8 -*-

import json
import os
from copy import deepcopy

import PixivArtistHandler
import PixivBrowserFactory
import PixivConfig
import PixivHelper
import PixivImageHandler
import PixivSketchHandler
import PixivTagsHandler
import PixivUtil2

_default_batch_filename = "./batch_job.json"


class JobOption(object):
    config = PixivConfig.ConfigItem

    def loadConfig(self, path=None):
        # dummy method for compatibility
        PixivHelper.print_and_log("debug", "Called from JobOption, will not reloading the config...")
        pass

    def __init__(self, job, _config):
        if _config is None:
            raise Exception("Cannot get default configuration, aborting...")

        # set default option from config
        self.config = deepcopy(_config)
        self.config.loadConfig = self.loadConfig

        if "option" in job and job["option"] is not None:
            option_data = job["option"]
            for option in option_data:
                self.config.__setattr__(option, option_data[option])


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
    include_sketch = False
    if "include_sketch" in job and len(job["include_sketch"]) > 0:
        include_sketch = bool(job["include_sketch"])

    for member_id in member_ids:
        PixivArtistHandler.process_member(caller,
                                          job_option.config,
                                          member_id=member_id,
                                          user_dir=job_option.config.rootDirectory,
                                          page=start_page,
                                          end_page=end_page,
                                          bookmark=from_bookmark,
                                          tags=tags,
                                          title_prefix=f"{job_name} ")
        if include_sketch:
            # fetching artist token...
            (artist_model, _) = PixivBrowserFactory.getBrowser().getMemberPage(member_id)
            PixivSketchHandler.process_sketch_artists(caller,
                                                      job_option.config,
                                                      artist_model.artistToken,
                                                      start_page=start_page,
                                                      end_page=end_page,
                                                      title_prefix=f"{job_name} ")


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
                                        job_option.config,
                                        image_id=image_id,
                                        user_dir=job_option.config.rootDirectory,
                                        title_prefix=f"{job_name} ")
    print("done.")


def handle_tags(caller: PixivUtil2, job, job_name, job_option):
    tags = None
    if "tags" in job and len(job["tags"]) > 0:
        tags = job["tags"]
    else:
        print(f"No tags found or empty tags in {job_name}!")
        return

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
        member_id = job["member_id"]
    bookmark_count = None
    if "bookmark_count" in job:
        bookmark_count = int(job["bookmark_count"])

    sort_order = 'date_d'  # default is newest work first.
    if "oldest_first" in job:
        sort_order = 'date' if bool(job["oldest_first"]) else 'date_d'

    if "sort_order" in job and caller.__br__._isPremium:
        if job["sort_order"] in ('date_d', 'date', 'popular_d', 'popular_male_d', 'popular_female_d'):
            sort_order = job["sort_order"]
        else:
            raise Exception(f"Invalid sort_order: {job['sort_order']} in {job_name}.")

    type_mode = "a"
    if "type_mode" in job:
        if job["type_mode"] in {'a', 'i', 'm'}:
            type_mode = job["type_mode"]
        else:
            raise Exception(f"Invalid type_mode: {job['type_mode']} in {job_name}.")

    PixivTagsHandler.process_tags(caller,
                                  job_option.config,
                                  tags,
                                  page=start_page,
                                  end_page=end_page,
                                  wild_card=wild_card,
                                  title_caption=title_caption,
                                  start_date=start_date,
                                  end_date=end_date,
                                  use_tags_as_dir=job_option.config.useTagsAsDir,
                                  member_id=member_id,
                                  bookmark_count=bookmark_count,
                                  sort_order=sort_order,
                                  type_mode=type_mode)


def process_batch_job(caller: PixivUtil2, batch_file=None):
    PixivHelper.get_logger().info('Batch Mode from json (b).')
    caller.set_console_title("Batch Menu")

    if batch_file is None:
        batch_file = _default_batch_filename

    batch_file = os.path.abspath(batch_file)

    if os.path.exists(batch_file):
        jobs_file = open(batch_file, encoding="utf-8")
        jobs = json.load(jobs_file)

        total_job = len(jobs["jobs"])
        active_job = len([y for y in jobs["jobs"] if jobs["jobs"][y]["enabled"]])
        PixivHelper.print_and_log("info", f"Found {active_job} active job(s) of {total_job} jobs from {batch_file}.")

        for job_name in jobs["jobs"]:
            PixivHelper.print_and_log("info", f"Processing {job_name}")
            curr_job = jobs["jobs"][job_name]

            if "enabled" not in curr_job or not bool(curr_job["enabled"]):
                PixivHelper.print_and_log("warn", f"Skipping {job_name} because not enabled.")
                continue

            if "job_type" not in curr_job:
                PixivHelper.print_and_log("error", f"Cannot find job_type in {job_name}")
                continue

            job_option = JobOption(curr_job, caller.__config__)
            if curr_job["job_type"] == '1':
                handle_members(caller, curr_job, job_name, job_option)
            elif curr_job["job_type"] == '2':
                handle_images(caller, curr_job, job_name, job_option)
            elif curr_job["job_type"] == '3':
                handle_tags(caller, curr_job, job_name, job_option)
            else:
                PixivHelper.print_and_log("error", f"Unsupported job_type {curr_job['job_type']} in {job_name}")
    else:
        PixivHelper.print_and_log("error", f"Cannot found {batch_file}, see https://github.com/Nandaka/PixivUtil2/wiki/Using-Batch-Job-(Experimental) for example. ")

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

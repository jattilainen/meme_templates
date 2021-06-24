from django.core.management.base import BaseCommand

from django.conf import settings
from memeapp.recommend_engine.recommend_client import process_new_meme
from memeapp.creators import set_start_meme
from memeapp.origin_manager import get_group_origin
import os
from pathlib import Path


class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('--path', action='store',
                            dest='source_path',
                            help='Set path to recommendation engine configurations')

    def handle(self, *args, **options):
        if options['source_path']:
            source_path = options['source_path']
        else:
            print("Please specify a path to folder with start memes from group using --path option")
            exit(0)

        print("Folder contains {} memes".format(len(os.listdir(source_path))))
        answer = input("Continue?")
        if answer.lower() in ["y","yes"]:
            print("Starting upload...")
        else:
            print("Aborting.")
            exit(0)

        cnt = 0
        for i, entry in enumerate(os.scandir(source_path)):
            if (entry.path.endswith(".jpeg") or entry.path.endswith(".jpg") or entry.path.endswith(".png")) and entry.is_file():
                meme_id = set_start_meme(entry.path, start=cnt)
                if (meme_id > 0):
                    cnt += 1
                else:
                    print(entry.path, "upload failed with code", meme_id)

        print("Total of {} memes uploaded".format(cnt))

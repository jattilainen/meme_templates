from django.core.management.base import BaseCommand

from django.conf import settings
from memeapp.recommend_engine.recommend_client import process_new_meme
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
            print("Please specify a path to folder with memes from group using --path option")
            exit(0)

        path = Path(source_path)
        group_type = os.path.basename(path.parent)
        group_name = os.path.basename(source_path)
        origin = get_group_origin(group_type, group_name)
        print("GROUP_TYPE: {}\nGROUP_NAME: {}\nORIGIN: {}".format(group_type, group_name, origin))
        answer = input("Continue?")
        if answer.lower() in ["y","yes"]:
            print("Starting upload...")
        else:
            print("Aborting.")
            exit(0)

        cnt = 0
        for i, entry in enumerate(os.scandir(source_path)):
            if (entry.path.endswith(".jpeg") or entry.path.endswith(".jpg") or entry.path.endswith(".png")) and entry.is_file():
                code = process_new_meme(entry.path, origin=origin)
                if (code > 0):
                    cnt += 1
                else:
                    print(entry.path, "upload failed with code", code)

        print("Total of {} memes uploaded".format(cnt)) 

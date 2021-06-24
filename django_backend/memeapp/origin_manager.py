from django.conf import settings
import json

def is_meme_from_user(origin):
    return origin.startswith("u")
def is_meme_from_group(origin):
    return origin.startswith("g")
def get_group_origin(group_type, group_name):
    with open(settings.ORIGINS_PATH) as origins:
        origins_list = json.load(origins)
    return "g" + str(origins_list[group_type][group_name])
def get_user_origin(user_id):
    return "u" + str(user_id)
def get_id_by_origin(origin):
    return int(origin[1:])

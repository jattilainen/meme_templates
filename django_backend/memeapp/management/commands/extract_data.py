import os
from django.core.management.base import BaseCommand
import time
from django.conf import settings

from memeapp.models import ProfileMeme, Profile, Meme


class Command(BaseCommand):
    def handle(self, *args, **options):
        cur_date = time.strftime("%Y%m%d-%H%M%S")
        location_subdir = settings.DATA_DUMP_DIR + '/' + cur_date + '/'
        if not os.path.exists(location_subdir):
            os.mkdir(location_subdir)
        reactions_location= location_subdir + 'reactions'
        users_rec_embeddings_location = location_subdir + 'users_rec_embeddings'
        memes_rec_embeddings_location = location_subdir + 'memes_rec_embeddings'
        memes_visual_embeddings_location = location_subdir + 'memes_visual_embeddings'
        memes_text_embeddings_location = location_subdir + 'memes_text_embeddings'
        memes_text_location = location_subdir + 'memes_text'

        # dump reactions
        file = open(reactions_location, "w")
        interactions = ProfileMeme.objects.all()
        for interaction in interactions:
            data = f'{interaction.user_id} {interaction.meme_id} {interaction.score} {interaction.interacted_on}\n'
            file.write(data)
        file.close()

        # dump users recommendation embeddings
        file = open(users_rec_embeddings_location, "w")
        users = Profile.objects.all()
        for user in users:
            data = f'{user.pk} {user.embedding}\n'
            file.write(data)
        file.close()

        # dump memes recommendation embeddings
        file = open(memes_rec_embeddings_location, "w")
        memes = Meme.objects.all()
        for meme in memes:
            data = f'{meme.pk} {meme.embedding}\n'
            file.write(data)
        file.close()

        # dump memes visual embeddings
        file = open(memes_visual_embeddings_location, "w")
        memes = Meme.objects.all()
        for meme in memes:
            data = f'{meme.pk} {meme.visual_embedding}\n'
            file.write(data)
        file.close()

        # dump memes text embeddings
        file = open(memes_text_embeddings_location, "w")
        memes = Meme.objects.all()
        for meme in memes:
            data = f'{meme.pk} {meme.text_embedding} {meme.lang}\n'
            file.write(data)
        file.close()

        # dump memes text
        file = open(memes_text_location, "w")
        memes = Meme.objects.all()
        for meme in memes:
            data = f'{meme.pk} {meme.text} {meme.lang}\n'
            file.write(data)
        file.close()

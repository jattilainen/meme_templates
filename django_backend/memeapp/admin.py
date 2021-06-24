from django.contrib import admin
from .models import Profile, Meme, ProfileMeme
from django.utils.html import format_html
from memeapp.choices import APPROVED, REJECTED

# Register your models here.
admin.site.register(Profile)
admin.site.register(ProfileMeme)


def approve_memes(modeladmin, request, queryset):
    # this is a function which lets admin make bulk updates on objects
    # (bulk checks on memes in this case)
    queryset.update(checked=APPROVED)

def reject_memes(modeladmin, request, queryset):
    # this is a function which lets admin make bulk updates on objects
    # (bulk checks on memes in this case)
    queryset.update(checked=REJECTED)

approve_memes.short_description = 'Approve selected memes'
reject_memes.short_description = 'Reject selected memes'

MAX_HEIGHT = 256  # max height of an image displayed on admin site
MAX_WIDTH = 1024

@admin.register(Meme)
class MemeAdmin(admin.ModelAdmin):


    # function to make an image tag from an object
    def image_tag(self, obj):
        height = obj.image.height
        width = obj.image.width

        if height > MAX_HEIGHT:
            # if height of original image is too big,
            # compress it
            factor = MAX_HEIGHT / height
            height *= factor
            width *= factor

        if width > MAX_WIDTH:
            factor = MAX_WIDTH / width
            width *= factor
            height *= factor

        return format_html('<img src="{}" width={} height={}/>'.format(obj.image.url, width, height))

    image_tag.short_description = 'Meme image'

    list_display = ['image_tag', ]  # field that displays when viewing memes as a list
    readonly_fields = ['image_tag', ]  # field that displays when viewing meme in detail
    list_filter = ['checked', ]  # fields on which filtering can be done when viewing as a list

    actions = [approve_memes, reject_memes]  # list of actions that can be done on multiple memes

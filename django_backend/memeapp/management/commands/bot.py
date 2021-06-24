from django.core.management.base import BaseCommand
from telegram import Bot, ParseMode
from telegram import InlineQueryResultCachedPhoto
from telegram.ext import Filters, MessageHandler, Updater, CommandHandler, CallbackQueryHandler, InlineQueryHandler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.utils.request import Request
from telegram.error import BadRequest, Unauthorized

from django.conf import settings
from django.db.models import F
from django.db import IntegrityError
from django.utils import timezone
from django.core.files import File

from memeapp.models import Template

import logging
import sys
import os
import json
import datetime
import Levenshtein
import traceback
import time
import html
import uuid
import schedule
import re
from threading import Thread
from time import sleep
import math
import numpy as np


class Command(BaseCommand):

    def start(self, update, context):
        chat_id = update.message.chat.id
        invite_info = update.message.text.split(' ')

        logger.info("start {}".format(chat_id))

        profile, new_created = Profile.objects.get_or_create(
            telegram_id=chat_id,
        )

        # cant add it to creation, because duplicate created with the same telegram_id
        if new_created:
            profile.start = 0
            profile.save()

        if new_created:
            if len(invite_info) > 1:
                invite_link = invite_info[1]
                if len(invite_link) <= 10 and invite_link.isalnum():
                    invite = Invite.objects.create(
                        link=invite_info[1],
                        user_id = profile.pk,
                    )
                else:
                    logger.warning("hack_attempt {} {}".format(profile.pk, chat_id))
            else:
                invite = Invite.objects.create(
                    link="no_link",
                    user_id = profile.pk,
                )


        button_list = [[
            InlineKeyboardButton(self.start_text, callback_data="reaction 0 -1 -1"),
        ]]
        reply_markup = InlineKeyboardMarkup(button_list)
        if not new_created:
            message = self.intro_message
        else:
            message = self.first_time_message
        context.bot.send_message(
            chat_id=update.message.chat_id,
            text=message,
            reply_markup=reply_markup,
        )
        logger.info("intro_sent {} {} {}".format(profile.pk, chat_id, new_created))

    def help(self, update, context):
        context.bot.send_message(
            chat_id=update.message.chat_id,
            text=self.help_message,
        )

    def handle(self, *args, **options):
        request = Request(
            connect_timeout=0.5,
            read_timeout=1.0,
        )

        self.bot = Bot(
            request=request,
            token=settings.TG_TOKEN,
        )

        updater = Updater(
            bot=self.bot,
            use_context=True,
        )

        dispatcher = updater.dispatcher
        dispatcher.add_handler(InlineQueryHandler(self.inline_query, run_async=True))
        dispatcher.add_handler(CommandHandler('start', self.start, run_async=True, filters=Filters.chat_type.private))
        dispatcher.add_handler(CommandHandler('help', self.help, run_async=True, filters=Filters.chat_type.private))

        dispatcher.add_error_handler(self.error_handler)

        Thread(target=self.schedule_checker).start()

        mode = settings.BOT_MODE
        if mode == "debug":
            updater.start_polling()
        elif mode == "prod":
            PORT = int(os.environ.get("PORT", "8443"))
            HOSTNAME = os.environ.get("CURRENT_HOST")
            updater.start_webhook(listen="0.0.0.0",
                                  port=PORT,
                                  url_path=settings.TG_TOKEN,
                                  key=os.environ.get("SSL_KEY"),
                                  cert=os.environ.get("SSL_CERT"),
                                  webhook_url="https://{}:{}/{}".format(HOSTNAME, PORT, settings.TG_TOKEN)
                                  )
        else:
            logger.error("No MODE specified!")
            sys.exit(1)


    def error_handler(self, update, context) -> None:
        """Log the error and send a telegram message to notify the developer."""

        # traceback.format_exception returns the usual python message about an exception, but as a
        # list of strings rather than a single string, so we have to join them together.
        tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
        tb_string = ''.join(tb_list)

        # Build the message with some markup and additional information about what happened.
        # You might need to add some logic to deal with messages longer than the 4096 character limit.
        message = (
            f'An exception was raised while handling an update\n'
            f'<pre>update = {html.escape(json.dumps(update.to_dict(), indent=2, ensure_ascii=False))}'
            '</pre>\n\n'
            f'<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n'
            f'<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n'
            f'<pre>{html.escape(tb_string)}</pre>'
        )

        # Finally, send the message
        context.bot.send_message(chat_id=settings.DEVELOPER_CHAT_ID, text=message, parse_mode=ParseMode.HTML)

    def inline_query(self, update, context):
        start = time.time()
        query = update.inline_query.query
        def substr_match(str1, str2):
            str1 = str1.lower()
            str2 = str2.lower()
            if len(str1) >= len(str2):
                return Levenshtein.distance(str1, str2)
            else:
                best_match = len(str1)
                for i in range(0, len(str2) - len(str1) + 1):
                    best_match = min(best_match, Levenshtein.distance(str1, str2[i:i+len(str1)]))
                return best_match
        templates = np.array(Template.objects.all())
        text_matches = []
        for template in templates:
            text_matches.append(substr_match(query, template.text))
        sorted_templates = templates[np.argsort(text_matches)]
        result = []
        for i in range(min(50, len(sorted_templates))):
            result.append(InlineQueryResultCachedPhoto(id=uuid.uuid4(), photo_file_id=sorted_templates[i].telegram_id))
        logger.info("inline_query_result")
        update.inline_query.answer(results=result, switch_pm_text='More memes for you',
                               switch_pm_parameter='inline-help', cache_time=0)
        end = time.time()
        response_time = int(1000 * (end - start))
        if len(query) >= 3:
            user_id = update.inline_query.from_user.id
            template_id = sorted_templates[0].pk
            LogInline.objects.create(
                user_id=user_id,
                template_id=template_id,
                response_time=response_time,
            )



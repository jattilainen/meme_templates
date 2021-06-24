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

from memeapp.models import Profile, Meme, LogReaction, Invite, Template, LogInline
from memeapp.recommend_engine.recommend_engine import RecommendEngine
from memeapp.recommend_engine.recommend_client import get_next_meme, submit_reaction, process_new_meme, reaction_to_rating, approved_processing
from memeapp.recommend_engine.daily_recalculation import daily_recalculation
from memeapp.choices import APPROVED, REJECTED, ON_REVIEW, MEME_OF_THE_DAY
from memeapp.getters import get_oldest_on_review, get_on_review_count, get_origin_on_review_count, get_users_count, get_memes_count, get_total_views, get_total_likes, get_user_views, get_user_likes, get_uploaded_count, get_uploaded_likes, get_uploaded_views, get_uploaded_max_liked, get_all_users, get_meme_of_the_day, has_user_seen_meme, does_nickname_exist, get_origin_nth_meme, get_n_uploads_a_day, get_origin_range_memes_stats
from memeapp.setters import set_moderation_result
from memeapp.origin_manager import get_id_by_origin, is_meme_from_user, get_user_origin
from memeapp.management.commands.bot_utils import get_right_time_word, get_time_ago_words

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


logger = logging.getLogger("memerecommend")


class Command(BaseCommand):
    # intro_message = 'This is the meme recommendation bot. Welcome!'
    # start_text = 'Lets go!'
    # continue_text = 'Back  to memes'
    # good_reaction_emoji = "😀"
    # bad_reaction_emoji = "😟"
    # no_memes_left_message = "You deserve a break. Please come back in a few hours"
    # imback_text = "I'm back"
    # successful_upload_message = "Your meme is uploaded, you can always check how it's doing with '/meme {}' command"
    # unknown_error_message = "Strange things happened. Please try to restart bot with /start command. Don't worry, your data will NOT be lost"
    # wide_image_message = "Your image is too wide, image proportion must be between 1:{} and {}:1".format(settings.MAX_HEIGHT_PROPORTION, settings.MAX_WIDTH_PROPORTION)
    # high_image_message = "Your image is too high, image proportion must be between 1:{} and {}:1".format(settings.MAX_HEIGHT_PROPORTION, settings.MAX_WIDTH_PROPORTION)
    # large_image_message = "Your image is too large, image size must be less then {} MB".format(settings.MAX_IMAGE_SIZE / 1024 / 1024)
    # upload_message = "Attach a meme you want to upload as a single image (not file)"
    # forwarded_photo_message = "If you are attempting to upload a meme please send it as a single photo, not as a forwarded message"
    # document_message = "If you are attempting to upload a meme please attach a photo, not a document, video or audio"
    # photo_with_caption_message = "If you are attempting to upload a meme please send it as a photo without caption"
    # meme_help_message = "You should use this command like this '/meme 2020'"
    # on_review_message = "This meme is on review"
    # rejected_message = "This meme was rejected"
    # approved_message = "This meme is live.\n Views: {}\n Likes: {}"
    # meme_does_not_exist_message = "No memes with that number found"
    intro_message = 'Чтобы перейти к просмотру мемов, нажмите на кнопку ниже. То, как загрузить свои мемы, участвовать в Меме Дня и другие полезные команды Вы всегда можете найти по команде /help. Добро пожаловать!'
    first_time_message = intro_message + "\n\n" + "В начале мы покажем Вам около 20-30 мемов разного типа (Вы не заметите, как пролетит время), чтобы получше понять Ваши вкусы и предпочтения"
    start_text = 'Поехали!'
    continue_text = 'Снова к мемам'
    good_reaction_emoji = "👍"
    bad_reaction_emoji = "💩"
    good_moderation_emoji = "✅"
    bad_moderation_emoji = "⛔️"
    on_review_emoji = "🕔"
    views_emoji = "👁"
    next_page_emoji = "▶️"
    previous_page_emoji = "◀️"
    no_memes_left_message = "Вы точно заслужили перерыв! Приходите через пару часиков"
    imback_text = "Я вернулся"
    successful_upload_message = "Ваш мем загружен, Вы всегда можете посмотреть, как он поживает, с помощью команды /m{}"
    unknown_error_message = "Что-то странное... Пожалуйста, сделайте рестарт бота с помощью команды /start . Не беспокойтесь, Ваши данные утеряны НЕ будут"
    wide_image_message = "Ваше изображение слишком широкое, пропорции изображения должны быть между 1:{} и {}:1".format(settings.MAX_HEIGHT_PROPORTION, settings.MAX_WIDTH_PROPORTION)
    high_image_message = "Ваше изображение слишком длинное в высоту, пропорции изображения должны быть между 1:{} и {}:1".format(settings.MAX_HEIGHT_PROPORTION, settings.MAX_WIDTH_PROPORTION)
    large_image_message = "Ваше изображение слишком тяжелое, вес изображения должен быть меньше {} MB".format(settings.MAX_IMAGE_SIZE / 1024 / 1024)
    origin_meme_repeated_message = "Вы уже загружали этот мем, вот он /m{}. Если вы считаете, что его необходимо загрузить еще раз, обратитесь в @memebrandt_support"
    upload_message = "Приложите мем, который хотите загрузить, в качестве 'фото' в одном экземпляре (НЕ 'файл'). Ваши фото не должны содержать порнографический контент и нарушать законодательство РФ. Вы можете не вызывать эту команду, а просто прикладывать фото"
    forwarded_photo_message = "Если вы пытаетесь приложить мем, пожалуйста, загрузите его как фото в одном экземпляре, а не как пересланное сообщение"
    document_message = "Если вы пытаетесь приложить мем, пожалуйста, загрузите его как фото в одном экземпляре, а не как документ, видео или аудио"
    photo_with_caption_message = "Если вы пытаетесь приложить мем, пожалуйста, загрузите его как фото в одном экземпляре без капчи"
    on_review_author_message = "Ваш мем находится на рассмотрении. Это не займет много времени"
    on_review_other_message = "Этот мем пока что находится на рассмотрении, поэтому на всякий случай мы Вам его не покажем"
    rejected_author_message = "Ваш мем был отклонен"
    rejected_other_message = "Этот мем был отклонен, поэтому мы Вам его не покажем"
    approved_message = "Опубликован {} \n👁 {}\n👍 {}"
    meme_does_not_exist_message = "Нет мема с данным номером"
    permission_denied_message = "Эта операция доступна только администраторам."
    no_memes_for_review_message = "Нет мемов на модерации"
    too_many_rejected_message = "Вы больше не можете загружать мемы, так как слишком много Ваших мемов было отклонено. Если Вы считаете, что это произошло по ошибке, напишите @memebrandt_support"
    too_many_onreview_message = "Для защиты от спама, число мемов, которое может находиться на модерации от одного пользователя одновременно, ограничено. Пожалуйста, дождитесь, пока проверят Ваши предыдущие мемы"
    help_message = "Это бот с рекомендательной системой, который предлагает мемы, подобранные специально для Вас. Вы можете загрузить свои мемы и посмотреть оценки других пользователей, которым мы его гарантированно покажем. \n\nТакже каждый день, анализируя многие факторы, мы определяем Мем Дня среди загруженных пользователями. Добавляя свой мем, Вы автоматически анонимно принимаете в нем участие, но если хотите, можете сделать себе никнейм, который мы покажем в случае Вашей победы. \n\n Полезные команды: \n /upload - загрузить свой мем. На всякий случай, все мемы проходят модерацию, однако это не займет много времени \n /changename - сделать впервые или сменить имя пользователя (по умолчанию анонимно) \n /gallery - посмотреть лайки и просмотры каждого Вашего мема \n /feed - вернуться к рекомендациям в любой момент \n /stats - получить общую статистику как бота, так и Вашу собственную"
    meme_of_the_day_congrats = "А вот и сегодняшний #мемдня! Поздравляем запостившего его пользователя - {}! \n\n👁 {}\n👍 {} \nВсего мемов-участников: {}\n======\n" \
                               "Наша курсовая закончилась. Сервер довольно дорогой, поэтому мы не можем просто оставить его крутиться."\
                               " Вы можете лайкать мемы до завтрашнего утра по Москве, но потом бот превратится в тыкву. Мы планируем оставить возможность присылать"\
                               " друг другу шаблоны в чатах - для этого в любом чате напишите @memebrandt_bot и начните набирать текст шаблона. "\
                               " Возможно это будет недоступно пару дней, пока мы переезжаем на маленький и дешевый сервер."\
                               " По ссылочке https://bitbucket.org/jattilainen_dev/memerecommend/ можно найти наш код."
    meme_of_the_day_congrats_anon = "А вот и сегодняшний #мемдня! Запостивший его пользователь решил остаться анонимом, но мы все равно его поздравляем! \n\n👁 {}\n👍 {} \nВсего участвовало мемов: {}\n======\n"\
                               "Наша курсовая закончилась. Сервер довольно дорогой, поэтому мы не можем просто оставить его крутиться.\n"\
                               " Вы можете лайкать мемы до завтрашнего утра по Москве, но потом бот превратится в тыкву. Мы планируем оставить возможность присылать"\
                               " друг другу шаблоны в чатах - для этого в любом чате напишите @memebrandt_bot и начните набирать текст шаблона. "\
                               " Возможно это будет недоступно пару дней, пока мы переезжаем на маленький и дешевый сервер.\n"\
                               " По ссылочке https://bitbucket.org/jattilainen_dev/memerecommend/ можно найти наш код."
    change_name_message = "Введите имя пользователя. Оно должно состоять только из латинских букв, подчеркиваний и цифр, длина должна быть от 5 до 20 символов. Просим воздержаться от использования нецензурной лексики, оскорблений и нарушений закондательства РФ, в противном случае Ваш аккаунт может быть немедленно заблокирован."
    wrong_name_character_message = "Имя пользователя должно состоять только из латинских букв, подчеркиваний и цифр"
    wrong_name_length_message = "Длина имени должна быть от 5 до 20 символов"
    name_is_not_unique_message = "Данное имя пользователя занято"
    name_changed_message = 'Ваше имя пользователя теперь "{}"!'
    changename_hint = "Напоминаем, что Вы можете установить имя пользователя с помощью команды /changename. Так, если Ваш мем окажется мемом дня, то он будет подписан Вашим ником."
    too_many_uploaded_message = "Для защиты от спама на данный момент наш бот поддерживает загрузку не более {} мемов в день от одного пользователя, а Вы уже достигли этого числа. Ваш последнний загруженный мем не будет добавлен в бота, но будем очень его ждать через {}! (смена дня рассчитывается по UTC)"
    no_memes_message = "Вы еще не грузили мемы. Загрузите хотя бы один, чтобы смотреть статистику по своим мемам"
    start_memes_ending = "Стартовые мемы закончились! Пожалуйста, не обижайтесь, если рекомендательная система подсунет что-то несмешное для Вас, она пока только учится. Приятного мемпросмотра!"


    def add_arguments(self, parser):
        parser.add_argument('--config', action='store',
                            dest='config_path',
                            help='Set path to recommendation engine configurations')


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

    def stats(self, update, context):
        chat_id = update.message.chat.id
        logger.info("stats_invoked {}".format(chat_id))

        # safety get, better to do it everywhere
        try:
            profile = Profile.objects.get(telegram_id=chat_id)
        except Profile.DoesNotExist:
            profile = None
        if profile is None:
            logger.warning("stats_user_doesnt_exist {}".format(chat_id))
            self.send_message(context, chat_id, self.unknown_error_message)
            return
        user_id = profile.pk

        users_cnt = get_users_count()
        memes_cnt = get_memes_count()
        total_views = get_total_views()
        total_likes = get_total_likes()
        likes_ratio = round(total_likes / total_views * 100, 1)

        user_views = get_user_views(user_id)
        user_likes = get_user_likes(user_id)
        if user_views != 0:
            user_likes_ratio = round(user_likes / user_views * 100, 1)
        else:
            user_likes_ratio = 100

        user_origin = get_user_origin(user_id)
        uploaded_cnt = get_uploaded_count(user_origin)

        info_message = "<b>Статистика бота</b> \nВсего пользователей: {:,} \nВсего мемов: {:,} \nВсего просмотров мемов: {:,} \nИз них лайков: {:,} ({} %) \n\n<b>Статистика пользователя</b> \nВы просмотрели мемов: {:,} \nИз них лайкнули: {:,} ({} %) \n\n<b>Статистика загруженных мемов</b> \nЗагружено мемов: {:,}".format(users_cnt, memes_cnt, total_views, total_likes, likes_ratio, user_views, user_likes, user_likes_ratio, uploaded_cnt)

        if uploaded_cnt > 0:
            uploaded_views = get_uploaded_views(user_origin)
            uploaded_likes = get_uploaded_likes(user_origin)
            if uploaded_views > 0:
                uploaded_likes_ratio = round(uploaded_likes / uploaded_views * 100, 1)
            else:
                uploaded_likes_ratio = 100
            info_message += "\nПолучено просмотров: {:,} \nПолучено лайков: {:,} ({} %)".format(uploaded_views, uploaded_likes, uploaded_likes_ratio)

        best_id, best_likes = get_uploaded_max_liked(user_origin)
        if (best_id != -1):
            info_message += "\nСамый популярный мем: /m{} ({} {})".format(best_id, best_likes, self.good_reaction_emoji)

        info_message += "\n\n @memebrandt_bot"

        context.bot.send_message(
            chat_id=update.message.chat_id,
            text=info_message,
            parse_mode=ParseMode.HTML,
        )
        logger.info("stats_success {} {}".format(user_id, chat_id))

    def schedule_checker(self):
        while True:
            schedule.run_pending()
            sleep(1)

    def send_top_day_meme(self):
        users_info =  get_all_users() # [(pk, tg_id)]
        top_day_meme, total_memes = get_meme_of_the_day()
        if top_day_meme == -1:
            return
        #owner_id = get_id_by_origin(top_day_meme.origin)
        #owner = Profile.objects.get(pk=owner_id)
        #congrat_phrase = self.meme_of_the_day_congrats.format(owner.nickname, top_day_meme.watched, top_day_meme.likes, total_memes)
        #if owner.nickname == '':
        congrat_phrase = self.meme_of_the_day_congrats_anon.format(top_day_meme.watched, top_day_meme.likes, total_memes)
        meme_path = top_day_meme.image.path
        meme_id = top_day_meme.pk
        for i in range(len(users_info)):
            try:
                chat_id = users_info[i][1]
                user_id = users_info[i][0]
                if has_user_seen_meme(user_id, meme_id):
                    self.bot.send_photo(chat_id,
                                        photo=open(meme_path, 'rb'),
                                        caption=congrat_phrase)
                else:
                    button_list = [[
                        InlineKeyboardButton(self.good_reaction_emoji, callback_data="reaction 1 {} {}".format(meme_id, MEME_OF_THE_DAY)),
                        InlineKeyboardButton(self.bad_reaction_emoji, callback_data="reaction -1 {} {}".format(meme_id, MEME_OF_THE_DAY)),
                    ]]
                    reply_markup = InlineKeyboardMarkup(button_list)
                    self.bot.send_photo(chat_id,
                                        photo=open(meme_path, 'rb'),
                                        caption=congrat_phrase,
                                        reply_markup=reply_markup)
            except:
                pass
            sleep(0.1)

    def handle(self, *args, **options):
        if options['config_path']:
            config_path = options['config_path']
        else:
            print("You have to specify a config using --config option")
            exit(0)


        with open(config_path) as config_file:
            config_data = json.load(config_file)
            settings.CONFIG = config_data
        settings.recommend_engine = RecommendEngine(**config_data['RecommendEngine'])
        settings.N_START_MEMES = config_data['N_START_MEMES']
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
        dispatcher.add_handler(CommandHandler('upload', self.upload, run_async=True, filters=Filters.chat_type.private))
        dispatcher.add_handler(MessageHandler(Filters.regex('^(/m[\d]+)$') & Filters.chat_type.private, self.meme, run_async=True))
        dispatcher.add_handler(MessageHandler(Filters.regex('^(/t[\d]+)$') & Filters.chat(username=settings.BOT_ADMINS), self.meme, run_async=True))
        dispatcher.add_handler(CommandHandler('feed', self.feed, run_async=True, filters=Filters.chat_type.private))
        dispatcher.add_handler(CommandHandler('help', self.help, run_async=True, filters=Filters.chat_type.private))
        dispatcher.add_handler(CommandHandler('stats', self.stats, run_async=True, filters=Filters.chat_type.private))
        dispatcher.add_handler(CommandHandler('changename', self.change_name, filters=Filters.chat_type.private))
        dispatcher.add_handler(CommandHandler('gallery', self.gallery, run_async=True, filters=Filters.chat_type.private))
        dispatcher.add_handler(CommandHandler('list', self.list, run_async=True, filters=Filters.chat_type.private))
        dispatcher.add_handler(CommandHandler('x', self.moderation, filters=Filters.chat(username=settings.BOT_ADMINS)))

        dispatcher.add_handler(CallbackQueryHandler(self.callback_handler, run_async=True))
        dispatcher.add_handler(MessageHandler(Filters.photo & ~Filters.caption & ~Filters.forwarded & Filters.chat_type.private, self.only_photo_handler, run_async=True))
        dispatcher.add_handler(MessageHandler(Filters.photo & Filters.forwarded & Filters.chat_type.private, self.forwarded_photo_handler))
        dispatcher.add_handler(MessageHandler(Filters.photo & Filters.caption & Filters.chat_type.private, self.photo_with_caption_handler))
        dispatcher.add_handler(MessageHandler((Filters.document | Filters.video | Filters.audio | Filters.voice | Filters.video_note) & Filters.chat_type.private, self.document_handler))
        dispatcher.add_handler(MessageHandler(Filters.text & Filters.chat_type.private, self.text_handler))
        dispatcher.add_error_handler(self.error_handler)
        if config_data['MemeOfTheDay']['send'] == 'yes':
            schedule.every().day.at(config_data['MemeOfTheDay']['at']).do(self.send_top_day_meme)

        if config_data['DailyRecalculation']['do'] == 'yes':
            schedule.every().day.at(config_data['DailyRecalculation']['at']).do(lambda: daily_recalculation(config_data))

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

    @staticmethod
    def send_message(context, chat_id, message, reply_markup=None, parse_mode=None):
        if reply_markup:
            context.bot.send_message(
                chat_id=chat_id,
                text=message,
                reply_markup=reply_markup,
                parse_mode=parse_mode,
            )
            return
        context.bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode=parse_mode,
        )

    def callback_handler(self, update, context):
        # Get reply
        query = update.callback_query

        # Get chat
        chat_id = query.message.chat.id
        try:
            profile = Profile.objects.get(telegram_id=chat_id)
        except Profile.DoesNotExist:
            profile = None
        if profile is None:
            logger.warning("callback_handler_user_doesnt_exist {}".format(chat_id))
            self.send_message(context, chat_id, self.unknown_error_message)
            return

        # Parse reply
        command_type = (query.data.split(' '))[0]
        if command_type == "moderation":
            user = query.from_user
            username = user['username']
            if username not in settings.BOT_ADMINS:
                self.send_message(context, chat_id, self.permission_denied_message)
                return

            _, choice, meme_id = (query.data.split(' '))
            try:
                query.edit_message_reply_markup(reply_markup=None)
            except BadRequest:
                return
            meme = Meme.objects.get(pk=meme_id)
            if meme.checked == ON_REVIEW:
                if choice == "1":
                    self.send_message(context, chat_id, self.good_moderation_emoji)
                    approved_processing(meme_id)
                    set_moderation_result(meme_id, True)
                elif choice == "-1":
                    self.send_message(context, chat_id, self.bad_moderation_emoji)
                    set_moderation_result(meme_id, False)
                    if (is_meme_from_user(meme.origin)):
                        user_id = get_id_by_origin(meme.origin)
                        author = Profile.objects.get(pk=user_id)
                        author.rejected = F('rejected') + 1
                        author.save(update_fields=['rejected'])
                        caption = "Ваш мем /m" + str(meme_id) + " был отклонен! Возможно, в нем есть запрещенный контент или это не мем, а просто картинка. Если вы считаете, что произошла ошибка, напишите @memebrandt_support"
                        context.bot.send_photo(chat_id=author.telegram_id, photo=open(meme.image.path, 'rb'), caption=caption)
            else:
                self.send_message(context, chat_id, "Не успел")

            # For moderation convinience
            on_review_count = get_on_review_count()
            self.send_message(context, chat_id, "Мемов на модерации: {}".format(on_review_count))

            meme_id = get_oldest_on_review()
            if meme_id == -1:
                self.send_message(context, chat_id, self.no_memes_for_review_message)
                return

            meme_path = Meme.objects.get(pk=meme_id).image.path  # Get path to meme
            button_list = [[
                InlineKeyboardButton(self.good_moderation_emoji, callback_data="moderation 1 {}".format(meme_id)),
                InlineKeyboardButton(self.bad_moderation_emoji, callback_data="moderation -1 {}".format(meme_id)),
            ]]
            reply_markup = InlineKeyboardMarkup(button_list)

            context.bot.send_photo(chat_id=chat_id,
                                   photo=open(meme_path, 'rb'),
                                   reply_markup=reply_markup)
            logger.info("moderation {}".format(meme_id))

        elif command_type == "reaction":
            start = time.time()

            _, choice, meme_id, recommend_details = (query.data.split(' '))
            logger.info("reaction {} {} {} {} {}".format(profile.pk, query.from_user.id, choice, meme_id, recommend_details))
            meme_id = int(meme_id)
            recommend_details = int(recommend_details)
            message_id = query.message.message_id
            try:
                query.edit_message_reply_markup(reply_markup=None)
            except BadRequest:
                return

            reaction = None
            if choice == "1":
                reaction = 'like'
                submit_reaction(profile.pk, meme_id, 'like', recommend_details)
            elif choice == "-1":
                reaction = 'dislike'
                submit_reaction(profile.pk, meme_id, 'dislike', recommend_details)
                try:
                    context.bot.delete_message(chat_id=chat_id, message_id=message_id)
                except:
                    pass
            old_meme_id = meme_id
            old_recommend_details = recommend_details
            meme_id, recommend_details, new_start = get_next_meme(profile.pk, start=profile.start)   # Get meme id from recommendation system
            if (profile.start != new_start):
                if profile.start != settings.N_START_MEMES + 1 and new_start == settings.N_START_MEMES + 1:
                    self.send_message(context, chat_id, self.start_memes_ending)
                profile.start = new_start
                profile.save()
            if (meme_id == -1):
                button_list = [[
                    InlineKeyboardButton(self.imback_text, callback_data="reaction 0 -1 -1"),
                ]]
                reply_markup = InlineKeyboardMarkup(button_list)
                self.send_message(context, query.message.chat.id, self.no_memes_left_message, reply_markup)
            else:
                meme_path = Meme.objects.get(pk=meme_id).image.path  # Get path to meme
                button_list = [[
                    InlineKeyboardButton(self.good_reaction_emoji, callback_data="reaction 1 {} {}".format(meme_id, recommend_details)),
                    InlineKeyboardButton(self.bad_reaction_emoji, callback_data="reaction -1 {} {}".format(meme_id, recommend_details)),
                ]]
                reply_markup = InlineKeyboardMarkup(button_list)
                try:
                    context.bot.send_photo(query.message.chat.id,
                                           photo=open(meme_path, 'rb'),
                                           reply_markup=reply_markup)
                except Unauthorized:
                    logger.warning("reaction after block {}".format(profile.pk))
            logger.info("recommend {} {} {} {}".format(profile.pk, query.from_user.id, meme_id, recommend_details))

            if reaction is None:
                return

            end = time.time()
            response_time = int(1000 * (end - start))
            LogReaction.objects.create(
                user_id=profile.pk,
                meme_id=old_meme_id,
                score=reaction_to_rating(reaction),
                response_time=response_time,
                reacted_recommend_detail=old_recommend_details,
                responded_recommend_detail=recommend_details
            )
        elif command_type == "gallery":
            _, user_id, new_page, last_page = (query.data.split(' '))
            new_page = int(new_page)
            last_page = int(last_page)
            try:
                query.edit_message_reply_markup(reply_markup=None)
            except BadRequest:
                return
            caption, image_path, reply_markup = self.get_gallery_page(user_id, new_page, chat_id)
            message_id = query.message.message_id
            context.bot.delete_message(chat_id=chat_id, message_id=message_id)

            if not image_path is None:
                context.bot.send_photo(chat_id,
                                       photo=open(image_path, 'rb'),
                                       caption=caption,
                                       reply_markup=reply_markup)
            else:
                self.send_message(context, chat_id, caption, reply_markup)
            logger.info("gallery_updated {} {} {}".format(chat_id, user_id, new_page))
        elif command_type == "list":
            _, user_id, new_page, last_page = (query.data.split(' '))
            new_page = int(new_page)
            last_page = int(last_page)
            try:
                query.edit_message_reply_markup(reply_markup=None)
            except BadRequest:
                return
            caption, reply_markup = self.get_list_page(user_id, new_page)
            message_id = query.message.message_id
            context.bot.delete_message(chat_id=chat_id, message_id=message_id)

            self.send_message(context, chat_id, caption, reply_markup)
            logger.info("list_updated {} {} {}".format(chat_id, user_id, new_page))



    def only_photo_handler(self, update, context):
        chat_id = update.message.chat.id

        # safety get, better to do it everywhere
        try:
            profile = Profile.objects.get(telegram_id=chat_id)
        except Profile.DoesNotExist:
            profile = None
        if profile is None:
            logger.warning("photo_handler_user_doesnt_exist {}".format(chat_id))
            self.send_message(context, chat_id, self.unknown_error_message)
            return

        logger.info("photo_handler_uploading {}".format(chat_id))

        if profile.rejected > settings.CONFIG['MAX_REJECTED']:
            self.send_message(context, chat_id, self.too_many_rejected_message)
            return

        if get_origin_on_review_count(get_user_origin(profile.pk)) > settings.CONFIG['MAX_ONREVIEW']:
            self.send_message(context, chat_id, self.too_many_onreview_message)
            return

        n_uploads, time_left, time_left_type = get_n_uploads_a_day(get_user_origin(profile.pk))
        if n_uploads >= settings.CONFIG['MAX_UPLOADS_A_DAY']:
            time_left_words = get_right_time_word(time_left, time_left_type)
            self.send_message(context, chat_id, self.too_many_uploaded_message.format(settings.CONFIG['MAX_UPLOADS_A_DAY'], time_left_words))
            return

        file_id = update.message.photo[-1].file_id
        newFile = context.bot.get_file(file_id)
        # jpg - telegram native format
        temp_meme_filename = os.path.join(settings.TEMP_PATH, uuid.uuid4().hex + ".jpg")
        newFile.download(temp_meme_filename)
        meme_id = process_new_meme(temp_meme_filename, origin=get_user_origin(profile.pk))
        os.remove(temp_meme_filename)

        if meme_id == settings.TOO_WIDE_ERROR:
            self.send_message(context, chat_id, self.wide_image_message)
            return
        elif meme_id == settings.TOO_HIGH_ERROR:
            self.send_message(context, chat_id, self.high_image_message)
            return
        elif meme_id == settings.TOO_LARGE_ERROR:
            self.send_message(context, chat_id, self.large_image_message)
            return
        elif meme_id == settings.UNKNOWN_UPLOAD_ERROR:
            self.send_message(context, chat_id, self.unknown_error_message)
            return
        elif meme_id < 0:
            self.send_message(context, chat_id, self.origin_meme_repeated_message.format(-meme_id))
            return

        button_list = [[
            InlineKeyboardButton(self.continue_text, callback_data="reaction 0 -1 -1"),
        ]]
        reply_markup = InlineKeyboardMarkup(button_list)
        message = self.successful_upload_message.format(meme_id)
        if profile.nickname == "":
            message += "\n\n" + self.changename_hint
        self.send_message(context, update.message.chat_id, message, reply_markup)
        logger.info("photo_handler_uploaded {} {} {}".format(profile.pk, chat_id, meme_id))
        total_on_review = get_on_review_count()
        if (math.log10(total_on_review)/ math.log10(4)) % 1 == 0:
            context.bot.send_message(chat_id=settings.DEVELOPER_CHAT_ID, text="Количество мемов на модерации является степенью числа 4. ({})".format(total_on_review), parse_mode=ParseMode.HTML)

    def forwarded_photo_handler(self, update, context):
        chat_id = update.message.chat.id
        logger.info("forwarded_photo_handler {}".format(chat_id))
        self.send_message(context, chat_id, self.forwarded_photo_message)

    def photo_with_caption_handler(self, update, context):
        chat_id = update.message.chat.id
        logger.info("photo_with_caption_handler {}".format(chat_id))
        user = update.message.from_user
        if (user['username'] in settings.BOT_ADMINS):
            # here we choose the largest image to show to users
            photo_id = update.message.photo[0].file_id
            caption = update.message.caption
            template = Template.objects.create(
                telegram_id=photo_id,
                text=caption,
            )

            # here we choose the smallest image to reduce memory cost
            file_id = update.message.photo[-1].file_id
            newFile = context.bot.get_file(file_id)
            # we have to use TEMP directory, instead of saving directly to TEMPLATE folder, because template.save creates copy
            temp_meme_filename = os.path.join(settings.TEMP_PATH, uuid.uuid4().hex + ".jpg")
            newFile.download(temp_meme_filename)
            template.image.save(temp_meme_filename, File(open(temp_meme_filename, "rb")))
            template.save()
            self.send_message(context, chat_id, "Шаблон {} загружен".format(template.pk))
        else:
            self.send_message(context, chat_id, self.photo_with_caption_message)


    def document_handler(self, update, context):
        chat_id = update.message.chat.id
        logger.info("document_handler {}".format(chat_id))
        self.send_message(context, chat_id, self.document_message)


    def upload(self, update, context):
        chat_id = update.message.chat.id

        logger.info("upload_invoked {}".format(chat_id))

        context.bot.send_message(
            chat_id=update.message.chat_id,
            text=self.upload_message,
        )


    def get_meme_description(self, meme, chat_id):
        is_author = False
        if is_meme_from_user(meme.origin):
            user_id = get_id_by_origin(meme.origin)
            try:
                profile = Profile.objects.get(pk=user_id)
            except Profile.DoesNotExist:
                profile = None
            if profile is None:
                logger.warning("photo_handler_user_doesnt_exist {}".format(chat_id))
            else:
                if profile.telegram_id == chat_id:
                    is_author = True
        meme_path = meme.image.path
        caption = ""
        show_meme = True
        time_ago = (timezone.now() - meme.published_on.replace())
        if meme.checked == APPROVED:
            caption = self.approved_message.format(get_time_ago_words(time_ago), meme.watched, meme.likes)
        if meme.checked == REJECTED:
            if is_author:
                caption = self.rejected_author_message
            else:
                show_meme = False
                caption = self.rejected_other_message
        if meme.checked == ON_REVIEW:
            if is_author:
                caption = self.on_review_author_message
            else:
                show_meme = False
                caption = self.on_review_other_message
        if show_meme:
            return caption, meme_path
        else:
            return caption, None
            self.send_message(context, chat_id, caption)


    def meme(self, update, context):
        chat_id = update.message.chat.id
        logger.info("meme_invoked {}".format(chat_id))
        if not isinstance(update.message.text, str):
            return

        args = update.message.text.split('m')
        is_t = False
        if len(args) != 2:
            is_t = True
            args = update.message.text.split('t')
            if len(args) != 2:
                return

        meme_str = args[1]
        try:
            meme_id = int(meme_str)
        except:
            return

        try:
            meme = Meme.objects.get(pk=meme_id)
        except Meme.DoesNotExist:
            self.send_message(context, chat_id, self.meme_does_not_exist_message)
            return

        caption, image_path = self.get_meme_description(meme, chat_id)
        if not image_path is None:
            if is_t:
                caption = meme.text
            context.bot.send_photo(chat_id,
                                   photo=open(image_path, 'rb'),
                                   caption=caption)
        else:
            self.send_message(context, chat_id, caption)

        logger.info("meme_completed {} {}".format(chat_id, meme_id))


    def get_scroll_button_pages(self, cur_page, total_pages):
        prev_page = cur_page
        if cur_page - 1 >= 0:
            prev_page = cur_page - 1

        next_page = cur_page
        if cur_page + 1 < total_pages:
            next_page = cur_page + 1

        return prev_page, next_page


    def get_gallery_page(self, user_id, page, chat_id):
        uploaded_count = get_uploaded_count(get_user_origin(user_id))
        if (uploaded_count == 0):
            return self.no_memes_message, None, None
        cur_page = page
        prev_page, next_page = self.get_scroll_button_pages(cur_page, uploaded_count)
        meme = get_origin_nth_meme(get_user_origin(user_id), cur_page)

        caption, image_path = self.get_meme_description(meme, chat_id)
        button_list = [[
             InlineKeyboardButton(self.previous_page_emoji, callback_data="gallery {} {} {}".format(user_id, prev_page, cur_page)),
             InlineKeyboardButton("{}/{}".format(cur_page + 1, uploaded_count), callback_data="gallery {} {} {}".format(user_id, cur_page, cur_page)),
            InlineKeyboardButton(self.next_page_emoji, callback_data="gallery {} {} {}".format(user_id, next_page, cur_page)),
        ]]
        reply_markup = InlineKeyboardMarkup(button_list)
        return caption, image_path, reply_markup


    def gallery(self, update, context):
        chat_id = update.message.chat.id
        logger.info("gallery_invoked {}".format(chat_id))

        # safety get, better to do it everywhere
        try:
            profile = Profile.objects.get(telegram_id=chat_id)
        except Profile.DoesNotExist:
            profile = None
        if profile is None:
            logger.warning("gallery_user_doesnt_exist {}".format(chat_id))
            self.send_message(context, chat_id, self.unknown_error_message)
            return
        user_id = profile.pk

        caption, image_path, reply_markup = self.get_gallery_page(user_id, 0, chat_id)
        if not image_path is None:
            context.bot.send_photo(chat_id,
                                   photo=open(image_path, 'rb'),
                                   caption=caption,
                                   reply_markup=reply_markup)
        else:
            self.send_message(context, chat_id, caption, reply_markup)

        logger.info("gallery_sent {} {}".format(chat_id, user_id))


    def get_list_page(self, user_id, page):
        uploaded_count = get_uploaded_count(get_user_origin(user_id))
        if (uploaded_count == 0):
            return self.no_memes_message, None
        cur_page = page
        total_pages = (uploaded_count + settings.CONFIG["N_MEMES_ON_LIST_PAGE"] - 1) // settings.CONFIG["N_MEMES_ON_LIST_PAGE"]
        prev_page, next_page = self.get_scroll_button_pages(cur_page, total_pages)
        start = cur_page * settings.CONFIG["N_MEMES_ON_LIST_PAGE"]
        end = min((cur_page + 1) * settings.CONFIG["N_MEMES_ON_LIST_PAGE"], uploaded_count)
        memes_ids, likes, views, status = get_origin_range_memes_stats(get_user_origin(user_id), start, end)
        caption = ""
        for i in range(len(memes_ids)):
            like_ratio = 0
            if views[i] != 0:
                like_ratio = int(likes[i] / views[i] * 100)
            if (status[i] == APPROVED):
                caption += "/m{}  {} {} | {} {}\n".format(memes_ids[i], self.good_reaction_emoji, likes[i], self.views_emoji, views[i])
            elif (status[i] == REJECTED):
                caption += "/m{}  {}\n".format(memes_ids[i], self.bad_moderation_emoji)
            elif (status[i] == ON_REVIEW):
                caption += "/m{}  {}\n".format(memes_ids[i], self.on_review_emoji)

        button_list = [[
             InlineKeyboardButton(self.previous_page_emoji, callback_data="list {} {} {}".format(user_id, prev_page, cur_page)),
             InlineKeyboardButton("{}-{}/{}".format(start + 1, end, uploaded_count), callback_data="list {} {} {}".format(user_id, cur_page, cur_page)),
            InlineKeyboardButton(self.next_page_emoji, callback_data="list {} {} {}".format(user_id, next_page, cur_page)),
        ]]
        reply_markup = InlineKeyboardMarkup(button_list)
        return caption, reply_markup


    def list(self, update, context):
        chat_id = update.message.chat.id
        logger.info("list_invoked {}".format(chat_id))

        # safety get, better to do it everywhere
        try:
            profile = Profile.objects.get(telegram_id=chat_id)
        except Profile.DoesNotExist:
            profile = None
        if profile is None:
            logger.warning("list_user_doesnt_exist {}".format(chat_id))
            self.send_message(context, chat_id, self.unknown_error_message)
            return
        user_id = profile.pk

        caption, reply_markup = self.get_list_page(user_id, 0)
        self.send_message(context, chat_id, caption, reply_markup=reply_markup)

        logger.info("list_sent {} {}".format(chat_id, user_id))

    def moderation(self, update, context):
        user = update.message.from_user
        username = user['username']
        if username not in settings.BOT_ADMINS:
            self.send_message(context, update.message.chat_id, self.permission_denied_message)
            return

        meme_id = get_oldest_on_review()
        if meme_id == -1:
            self.send_message(context, update.message.chat_id, self.no_memes_for_review_message)
            return

        meme_path = Meme.objects.get(pk=meme_id).image.path  # Get path to meme
        button_list = [[
            InlineKeyboardButton(self.good_moderation_emoji, callback_data="moderation 1 {}".format(meme_id)),
            InlineKeyboardButton(self.bad_moderation_emoji, callback_data="moderation -1 {}".format(meme_id)),
        ]]
        reply_markup = InlineKeyboardMarkup(button_list)

        context.bot.send_photo(update.message.chat_id,
                               photo=open(meme_path, 'rb'),
                               reply_markup=reply_markup)
        logger.info("moderation {}".format(meme_id))


    # ctrl+c - ctrl+v quick solution - to refactor
    def feed(self, update, context):
        chat_id = update.message.chat.id
        try:
            profile = Profile.objects.get(telegram_id=chat_id)
        except Profile.DoesNotExist:
            profile = None
        if profile is None:
            logger.warning("feed_user_doesnt_exist {}".format(chat_id))
            self.send_message(context, chat_id, self.unknown_error_message)
            return

        meme_id, recommend_details, new_start = get_next_meme(profile.pk, start=profile.start)   # Get meme id from recommendation system
        if profile.start != new_start:
            profile.start = new_start
            profile.save()
        if meme_id == -1:
            button_list = [[
                InlineKeyboardButton(self.imback_text, callback_data="reaction 0 -1 -1"),
            ]]
            reply_markup = InlineKeyboardMarkup(button_list)
            self.send_message(context, chat_id, self.no_memes_left_message, reply_markup)
            return
        meme_path = Meme.objects.get(pk=meme_id).image.path  # Get path to meme
        button_list = [[
            InlineKeyboardButton(self.good_reaction_emoji, callback_data="reaction 1 {} {}".format(meme_id, recommend_details)),
            InlineKeyboardButton(self.bad_reaction_emoji, callback_data="reaction -1 {} {}".format(meme_id, recommend_details)),
            ]]
        reply_markup = InlineKeyboardMarkup(button_list)

        context.bot.send_photo(chat_id,
                               photo=open(meme_path, 'rb'),
                               reply_markup=reply_markup)
        logger.info("recommend {} {} {} {}".format(profile.pk, chat_id, meme_id, recommend_details))


    def error_handler(self, update, context) -> None:
        """Log the error and send a telegram message to notify the developer."""
        # Log the error before we do anything else, so we can see it even if something breaks.-
        logger.error(msg="Exception while handling an update:", exc_info=context.error)

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


    def change_name(self, update, context):
        chat_id = update.message.chat.id
        context.chat_data['last_command'] = 'change_name'
        self.send_message(context, chat_id, self.change_name_message)

        logger.info("change_name_invoked {}".format(chat_id))


    def text_handler(self, update, context):
        text = update.effective_message.text
        chat_id = update.message.chat.id
        if 'last_command' in context.chat_data and context.chat_data['last_command'] == 'change_name':
            if not re.match("^[A-Za-z0-9_]*$", text):
                self.send_message(context, chat_id, self.wrong_name_character_message)
                return
            if len(text) < 5 or len(text) > 20:
                self.send_message(context, chat_id, self.wrong_name_length_message)
                return

            try:
                profile = Profile.objects.get(telegram_id=chat_id)
            except Profile.DoesNotExist:
                profile = None
            if profile is None:
                logger.warning("name_change_user_doesnt_exist {}".format(chat_id))
                self.send_message(context, chat_id, self.unknown_error_message)
                return

            if not does_nickname_exist(text):
                profile.nickname = text
                profile.save()
            else:
                self.send_message(context, chat_id, self.name_is_not_unique_message)
                return
            self.send_message(context, chat_id, self.name_changed_message.format(text))
            context.chat_data['last_command'] = 'name_changed'
            logger.info("change_name_success {} {} {}".format(profile.pk, chat_id, text))
            return

        context.chat_data['last_command'] = 'unknown_text'

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



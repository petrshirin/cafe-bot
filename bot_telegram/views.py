from django.shortcuts import render
from django.http import HttpResponse
from telebot import TeleBot, types
from .models import *
from .messages import *
from .menu_parser import *

# Create your views here.
bot = TeleBot('')


def get_web_hook(request, token):
    if request.match_info.get("token") == token:
        global bot
        bot.token = token
        request_body_dict = request.json()
        update = types.Update.de_json(request_body_dict)
        bot.process_new_updates([update])
        return HttpResponse('ok', status=200)
    else:
        return HttpResponse('fail', status=403)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    telegram_bot = TelegramBot.objects.filter(token=bot.token).first()
    user = TelegramUser.objects.filter(telegram_bot=telegram_bot, user_id=message.chat.id).first()
    if not user:
        user = TelegramUser(user_id=message.chat.id, telegram_bot=telegram_bot, role=TelegramUserRole.objects.get(key=1), user_name=message.from_user.first_name)
        user.save()
    message_to_send = TelegramMessage.objects.filter(tag='welcome_message').first()
    if not message_to_send:
        message_text = '''Привет, {}
Добро пожаловать в бота {}
Правила публичной оферты {} принимаются после первого платежа в системе
Давай уже закажем первый кофе!
На первый заказ через бота действует скидка 50%
'''
    else:
        message_text = message_to_send.text
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('Главное Меню'))
    bot.send_message(message.chat.id, message_text.format(user.user_name, telegram_bot.name, telegram_bot.rules), reply_markup=markup)


@bot.message_handler(content_types=['text'])
def text_messages(message):
    user = TelegramUser.objects.get(user_id=message.chat.id)
    action = BotAction(bot, message, user)
    if message.text.lower() == 'главное меню':
        user.status = action.main_menu()
    elif message.text.lower() == 'заведения':
        user.status = action.restaurants()
    elif message.text.lower() == 'настройки':
        pass
    elif message.text.lower() == 'корзина':
        pass


@bot.message_handler(content_types=['location'])
def get_user_location(message):
    user = TelegramUser.objects.get(user_id=message.chat.id)
    action = BotAction(bot, message, user)
    if user.status == 4:
        if message.location is not None:
            user.status = action.nearest_restaurant(message.location.latitude, message.location.longitude)


@bot.callback_query_handler(func=lambda c: True)
def inline_logic(c):
    user = TelegramUser.objects.get(user_id=c.message.chat.id)
    action = BotAction(bot, c.message, user)
    if c.data == "nearest_restaurants":
        action.send_location()

    if c.data == 'all_restaurants':
        action.all_restaurants()

    if 'restaurant_' in c.data:
        try:
            param = c.data.split('_')
            rest_id = int(param[1])
            page = int(param[2])
        except Exception as err:
            print(err)
            return None
        restaurant = Restaurant.objects.filter(pk=rest_id).first()
        if restaurant:
            menu = restaurant.menu_struct
            menu_struct = MenuStruct(menu, 0)
            if menu_struct.type == 'products':
                action.restaurant_menu(restaurant.pk, page, menu_struct)
            elif menu_struct.type == 'categories':
                action.restaurant_category(restaurant.pk, menu_struct, page)

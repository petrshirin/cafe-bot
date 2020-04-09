from django.shortcuts import render
from django.http import HttpResponse
from telebot import TeleBot, types
from .models import *
from .messages import *
from .menu_parser import *
import os

# Create your views here.

bot = TeleBot('')


def get_web_hook(request, bot_id):
    bot_orm = TelegramBot.objects.filter(pk=bot_id).first()
    json_data = json.loads(request.body)
    if not bot_orm:
        print('fail bot')
        return HttpResponse('fail bot', status=403)
    print(json_data.get("token"))
    if json_data.get("token") == str(bot_orm.token):
        global bot
        bot.token = bot_orm.token
        request_body_dict = json_data
        update = types.Update.de_json(request_body_dict)
        bot.process_new_updates([update])
        return HttpResponse('ok', status=200)
    else:
        print('fail token')
        return HttpResponse('fail token', status=403)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    telegram_bot = TelegramBot.objects.filter(token=bot.token).first()
    user = TelegramUser.objects.filter(telegram_bot=telegram_bot, user_id=message.chat.id).first()
    if not user:
        user = TelegramUser(user_id=message.chat.id, telegram_bot=telegram_bot, role=TelegramUserRole.objects.get(pk=1), user_name=message.from_user.first_name)
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
    bot.send_message(message.chat.id, message_text.format(user.user_name, telegram_bot.name, telegram_bot.name), reply_markup=markup)


@bot.message_handler(content_types=['text'])
def text_messages(message):
    user = TelegramUser.objects.get(user_id=message.chat.id)
    action = BotAction(bot, message, user)
    if message.text.lower() == 'главное меню':
        user.step = action.main_menu()
    elif message.text.lower() == 'заведения':
        user.step = action.restaurants()
    elif message.text.lower() == 'настройки':
        action.settings()
    elif message.text.lower() == 'корзина':
        action.basket()
    elif message.text.lower() == 'скидки и бонусы':
        action.bonus_systems()
    elif message.text.lower() == 'отмена':
        if user.step == 21:
            user.step = action.cheques()
    else:
        if user.step == 21:
            email = message.text
            user.email = email

            try:
                user.save()
            except Exception as err:
                print(err)
                bot.send_message(message.chat.id, 'Неверно введен Email, попробуйте заного')
                user.step = action.add_email()
            user.step = action.cheques(True)

    user.save()


@bot.message_handler(content_types=['location'])
def get_user_location(message):
    user = TelegramUser.objects.get(user_id=message.chat.id)
    action = BotAction(bot, message, user)
    print(user.step)
    if user.step == 2:
        if message.location is not None:
            user.step = action.nearest_restaurant(message.location.latitude, message.location.longitude)


@bot.callback_query_handler(func=lambda c: True)
def inline_logic(c):
    print(c.data)
    user = TelegramUser.objects.get(user_id=c.message.chat.id)
    action = BotAction(bot, c.message, user)
    if c.data == "nearest_restaurants":
        user.step = action.send_location()

    elif c.data == 'all_restaurants':
        user.step = action.all_restaurants()

    elif c.data == 'main_menu':
        user.step = action.main_menu()

    elif c.data == 'settings':
        user.step = action.settings()

    elif c.data == 'my_cheques':
        user.step = action.cheques()

    elif c.data == 'add_email':
        user.step = action.add_email()

    elif c.data == 'my_cards':
        user.step = action.cards()

    elif c.data == 'clear_basket':
        user.step = action.clear_basket()

    elif c.data == 'basket_history':
        user.step = action.basket_history()

    elif c.data == 'basket':
        user.step = action.basket()

    elif 'createpay_' in c.data:
        try:
            param = c.data.split('_')
            transaction_id = int(param[1])
        except Exception as err:
            print(err)
            return None
        user.step = action.create_pay(transaction_id)

    elif 'mycard_' in c.data:
        try:
            param = c.data.split('_')
            card_id = int(param[1])
        except Exception as err:
            print(err)
            return None
        user.step = action.show_card(card_id)

    elif 'my_sales' == c.data:
        user.step = action.bonus_systems()

    elif 'sale_' == c.data:
        try:
            param = c.data.split('_')
            user_sale_id = int(param[1])
        except Exception as err:
            print(err)
            return None
        user.step = action.sale(user_sale_id)

    elif 'restaurant_' in c.data:
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
            menu_struct = MenuStruct(menu, -1)
            if menu_struct.type == 'products':
                user.step = action.restaurant_menu(restaurant.pk, page, menu_struct)
            elif menu_struct.type == 'categories':
                user.step = action.restaurant_category(restaurant.pk, menu_struct, page)

    elif 'category_' in c.data:
        try:
            param = c.data.split('_')
            rest_id = int(param[1])
            category_id = int(param[2])
            page = int(param[3])
        except Exception as err:
            print(err)
            return
            pass
        restaurant = Restaurant.objects.filter(pk=rest_id).first()
        if restaurant:
            menu = restaurant.menu_struct
            menu_struct = MenuStruct(menu, -1)
            category = menu_struct.get_category(category_id)
            if category is None:
                category = menu_struct
            if category.type == 'products':
                user.step = action.restaurant_menu(restaurant.pk, page, category)
            elif category.type == 'categories':
                user.step = action.restaurant_category(restaurant.pk, category, page)
            else:
                user.step = action.restaurant_category(restaurant.pk, category, page)

    elif 'product_' in c.data:
        try:
            param = c.data.split('_')
            rest_id = int(param[1])
            product_id = int(param[2])
        except Exception as err:
            print(err)
            return
        restaurant = Restaurant.objects.filter(pk=rest_id).first()
        if restaurant:
            menu = restaurant.menu_struct
            menu_struct = MenuStruct(menu, -1)
            product = menu_struct.get_product(product_id)
            if product:
                user.step = action.restaurant_product(rest_id, product)

    elif 'addtobasket_' in c .data:
        try:
            param = c.data.split('_')
            rest_id = int(param[1])
            product_id = int(param[2])
        except Exception as err:
            print(err)
            return
        user_product = TelegramUserProduct.objects.filter(pk=product_id).first()
        if user_product:
            user.step = action.add_to_basket(rest_id, user_product)

    elif 'additions_' in c.data:
        try:
            param = c.data.split('_')
            rest_id = int(param[1])
            product_id = int(param[2])
        except Exception as err:
            print(err)
            return
        user_product = TelegramUserProduct.objects.filter(pk=product_id).first()
        if user_product:
            additions = user_product.product.additions.all()
            user.step = action.restaurant_additions(rest_id, user_product, additions)

    elif 'additionadd_' in c.data:
        try:
            param = c.data.split('_')
            rest_id = int(param[1])
            product_id = int(param[2])
            addition_id = int(param[3])
        except Exception as err:
            print(err)
            return
        restaurant = Restaurant.objects.filter(pk=rest_id).first()
        user_product = TelegramUserProduct.objects.filter(pk=product_id).first()
        if user_product:
            addition = Addition.objects.filter(pk=addition_id).first()
            if addition:
                user.step = action.add_addition(rest_id, user_product, addition)

    elif 'buyproduct_' in c.data:
        try:
            param = c.data.split('_')
            rest_id = int(param[1])
            product_id = int(param[2])
        except Exception as err:
            print(err)
            return
        user.step = action.buy_product(rest_id, product_id)

    elif 'productpay_' in c.data:
        try:
            param = c.data.split('_')
            rest_id = int(param[1])
            product_id = int(param[2])
        except Exception as err:
            print(err)
            return
        user.step = action.pay_card(rest_id, product_id)

    elif 'productpayanouther_' in c.data:
        try:
            param = c.data.split('_')
            rest_id = int(param[1])
            product_id = int(param[2])
        except Exception as err:
            print(err)
            return
        user.step = action.pay_another_card(rest_id, product_id)

    elif 'choicecard_' in c.data:
        try:
            param = c.data.split('_')
            rest_id = int(param[1])
            transaction_id = int(param[2])
            user_card_id = int(param[3])
        except Exception as err:
            print(err)
            return
        user.step = action.choice_card(rest_id, transaction_id, user_card_id)

    user.save()



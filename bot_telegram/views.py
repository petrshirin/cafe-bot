from django.http import HttpResponse

from .menu_parser import *
from .messages import *
from telebot import TeleBot, types
import logging

# Create your views here.

LOG = logging.getLogger(__name__)
bot = TeleBot('')


def get_web_hook(request, token):
    bot_orm = TelegramBot.objects.filter(token=token).first()
    json_data = json.loads(request.body)
    if not bot_orm:
        LOG.error('fail bot')
        return HttpResponse('fail bot', status=500)
    LOG.debug(str(json_data).encode('utf-8'))
    global bot
    bot.token = bot_orm.token
    request_body_dict = json_data
    update = types.Update.de_json(request_body_dict)
    bot.process_new_updates([update])
    return HttpResponse('ok', status=200)


@bot.message_handler(commands=['start'])
def send_welcome(message):
    telegram_bot = TelegramBot.objects.filter(token=bot.token).first()
    user = TelegramUser.objects.filter(telegram_bot=telegram_bot, user_id=message.chat.id).first()
    if not user:
        user = TelegramUser(user_id=message.chat.id, telegram_bot=telegram_bot, role=TelegramUserRole.objects.get(pk=1), user_name=message.from_user.first_name)
        user.save()
    action = BotAction(bot, message, user)
    message_text = action.get_message_text('welcome_message', '''Привет, {}
Добро пожаловать в бота {}
Правила публичной оферты Карты принимаются после первого платежа в системе
Давай уже закажем!
''')
    message_text = message_text.format(user.user_name, telegram_bot.name)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('Главное Меню'))
    if telegram_bot.public_offer:
        bot.send_document(chat_id=message.chat.id, data=open(telegram_bot.public_offer.path, 'rb'), caption=message_text, reply_markup=markup, parse_mode='markdown')
    elif telegram_bot.public_offer_url:
        bot.send_message(chat_id=message.chat.id, text=message_text, parse_mode='markdown')
    else:
        bot.send_message(chat_id=message.chat.id, text=message_text, parse_mode='markdown')

    action.main_menu()


@bot.message_handler(content_types=['text'])
def text_messages(message):
    user = TelegramUser.objects.get(user_id=message.chat.id)
    action = BotAction(bot, message, user)
    #if not action.check_restaurant_time():
    #    bot.send_message(message.chat.id, action.get_message_text('all_restaurant_closed', 'Все заведения сейчас закрыты'))
    if message.text.lower() == '🏠главное меню':
        user.step = action.main_menu()
    elif message.text.lower() == 'главное меню':
        user.step = action.main_menu()
    elif message.text.lower() == action.get_message_text('restaurant_button_name', 'заведения').lower():
        #if not action.check_restaurant_time():
        #    bot.send_message(message.chat.id, action.get_message_text('all_restaurant_closed', 'Все заведения сейчас закрыты'))
        #    return
        user.step = action.restaurants()
    elif message.text.lower() == '⚙️настройки':
        action.settings()
    elif message.text.lower() == '🛒корзина':
        action.basket()
    elif message.text.lower() == '🎁скидки и бонусы':
        action.bonus_systems()
    elif message.text.lower() == 'отмена':
        if user.step == 21:
            user.step = action.cheques()
        elif user.step == 51:
            user.step = 0
    else:
        if user.step == 21:
            email = message.text
            user.telegramusersettings.email = email

            try:
                user.telegramusersettings.save()
            except Exception as err:
                LOG.error(err)
                bot.send_message(message.chat.id, 'Неверно введен Email, попробуйте заного')
                user.step = action.add_email()
            user.step = action.cheques(True)
#        elif user.step == 51:
#            phone = re.match(r'((8|\+7)[\- ]?)?(\(?\d{3}\)?[\- ]?)?[\d\- ]{7}', message.text)
#            if phone:
#                user.phone = phone.group()
#                bot.send_message(message.chat.id, 'Номер сохранен')
#                user.step = 0
#            else:
#                bot.send_message(message.chat.id, 'Вы неверно ввели номер телефона, повторите попытку')

    user.save()


@bot.message_handler(content_types=['contact'])
def get_user_phone(message):
    user = TelegramUser.objects.get(user_id=message.chat.id)
    phone = message.contact.phone_number
    action = BotAction(bot, message, user)
    if phone:
        user.phone = phone
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(types.KeyboardButton(action.get_message_text('restaurant_button_name', 'Заведения')), types.KeyboardButton('🛒Корзина'))
        markup.add(types.KeyboardButton('🎁Скидки и бонусы'), types.KeyboardButton('⚙️Настройки'))
        bot.send_message(message.chat.id, 'Номер сохранен', reply_markup=markup)

    user.step = 0
    user.save()


@bot.message_handler(content_types=['location'])
def get_user_location(message):
    user = TelegramUser.objects.get(user_id=message.chat.id)
    action = BotAction(bot, message, user)
    LOG.debug(user.step)
    if message.location is not None:
        user.step = action.nearest_restaurant(message.location.latitude, message.location.longitude)


@bot.callback_query_handler(func=lambda c: True)
def inline_logic(c):
    LOG.debug(c.data)
    user = TelegramUser.objects.get(user_id=c.message.chat.id)
    action = BotAction(bot, c.message, user)

    if 'acceptorder_' in c.data:
        try:
            param = c.data.split('_')
            transaction_id = int(param[1])
        except Exception as err:
            LOG.error(err)
            return None

        user.step = action.accept_order(transaction_id)

    elif 'confirmorder_' in c.data:
        try:
            param = c.data.split('_')
            transaction_id = int(param[1])
        except Exception as err:
            LOG.error(err)
            return None
        user.step = action.confirm_order(transaction_id)

    elif c.data == "nearest_restaurants":
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

    elif 'sale_' in c.data:
        try:
            param = c.data.split('_')
            user_sale_id = param[1]
        except Exception as err:
            LOG.error(err)
            return None
        user.step = action.sale(user_sale_id)

    elif c.data == 'clear_basket':
        user.step = action.clear_basket()

    elif c.data == 'basket_history':
        user.step = action.basket_history()

    elif c.data == 'basket':
        user.step = action.basket()

    elif 'productbasket_' in c.data:
        try:
            param = c.data.split('_')
            product = int(param[1])
        except Exception as err:
            LOG.error(err)
            return None
        user.step = action.product_basket(product)

    elif c.data == 'complete_current_order':
        user.step = action.complete_current_order()

    elif 'paycardcompleteorder_' in c.data:
        try:
            param = c.data.split('_')
            transaction_id = int(param[1])
        except Exception as err:
            LOG.error(err)
            return None
        user.step = action.pay_card_current_order(transaction_id)

    elif 'cardcompleteanotherorder_' in c.data:
        try:
            param = c.data.split('_')
            transaction_id = int(param[1])
        except Exception as err:
            LOG.error(err)
            return None
        user.step = action.card_complete_order_another(transaction_id)

    elif 'cardcompletebonusorder_' in c.data:
        try:
            param = c.data.split('_')
            transaction_id = int(param[1])
        except Exception as err:
            LOG.error(err)
            return None
        user.step = action.card_complete_order_bonus(transaction_id)

    elif 'repeatonemoreproduct_' in c.data:
        try:
            param = c.data.split('_')
            user_product = int(param[1])
        except Exception as err:
            LOG.error(err)
            return None

        user.step = action.repeat_one_more_product(user_product)

    elif 'repeatpay_' in c.data:
        try:
            param = c.data.split('_')
            transaction_id = int(param[1])
        except Exception as err:
            LOG.error(err)
            return None

        user.step = action.repeat_pay(transaction_id)

    elif 'paycardrepeat_' in c.data:
        try:
            param = c.data.split('_')
            transaction_id = int(param[1])
        except Exception as err:
            LOG.error(err)
            return None

        user.step = action.pay_card_repeat_menu(transaction_id)

    elif 'cardrepeat_' in c.data:
        try:
            param = c.data.split('_')
            transaction_id = int(param[1])
        except Exception as err:
            LOG.error(err)
            return None
        user.step = action.card_repeat(transaction_id)

    elif 'cardrepeatanother_' in c.data:
        try:
            param = c.data.split('_')
            transaction_id = int(param[1])
        except Exception as err:
            LOG.error(err)
            return None
        user.step = action.card_repeat_another(transaction_id)

    elif 'cardrepeatbonus_' in c.data:
        try:
            param = c.data.split('_')
            transaction_id = int(param[1])
        except Exception as err:
            LOG.error(err)
            return None
        user.step = action.card_repeat_bonus(transaction_id)

    elif 'mycard_' in c.data:
        try:
            param = c.data.split('_')
            card_id = int(param[1])
        except Exception as err:
            LOG.error(err)
            return None
        user.step = action.show_card(card_id)

    elif 'deletecard_' in c.data:

        try:
            param = c.data.split('_')
            card_id = int(param[1])
        except Exception as err:
            LOG.error(err)
            return None
        user.step = action.delete_card( card_id)

    elif 'my_sales' == c.data:
        user.step = action.bonus_systems()

    elif 'sale_' == c.data:
        try:
            param = c.data.split('_')
            user_sale_id = int(param[1])
        except Exception as err:
            LOG.error(err)
            return None
        user.step = action.sale(user_sale_id)

    elif 'restaurant_' in c.data:
        try:
            param = c.data.split('_')
            rest_id = int(param[1])
            page = int(param[2])
        except Exception as err:
            LOG.error(err)
            return None
        restaurant = Restaurant.objects.filter(pk=rest_id).first()
        if not action.check_restaurant_time(rest_id):
            bot.send_message(action.message.chat.id, action.get_message_text('restaurant_closed', 'Заведение сейчас закрыто'))
            return
        if not action.check_restaurant_in_basket(rest_id):
            return
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
            LOG.error(err)
            return
            pass
        restaurant = Restaurant.objects.filter(pk=rest_id).first()
        if restaurant:
            menu = restaurant.menu_struct
            menu_struct = MenuStruct(menu, -1)
            category = menu_struct.get_category(category_id)
            LOG.debug(category)
            if category is None:
                category = menu_struct
            if category.type == 'products':
                user.step = action.restaurant_menu(restaurant.pk, page, category)
            elif category.type == 'categories':
                user.step = action.restaurant_category(restaurant.pk, category, page)
            else:
                user.step = action.restaurant_category(restaurant.pk, category, page)

    elif 'buyproduct_' in c.data:
        try:
            param = c.data.split('_')
            rest_id = int(param[1])
            product_id = int(param[2])
        except Exception as err:
            LOG.error(err)
            return
        LOG.debug(rest_id, product_id)
        user.step = action.buy_product(rest_id, product_id)

    elif 'paycardproduct_' in c.data:
        try:
            param = c.data.split('_')
            rest_id = int(param[1])
            product_id = int(param[2])
        except Exception as err:
            LOG.error(err)
            return
        LOG.debug(rest_id, product_id)
        user.step = action.pay_card_product(rest_id, product_id)

    elif 'product_' in c.data:
        try:
            param = c.data.split('_')
            rest_id = int(param[1])
            product_id = int(param[2])
        except Exception as err:
            LOG.error(err)
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
            LOG.error(err)
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
            LOG.error(err)
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
            LOG.error(err)
            return
        restaurant = Restaurant.objects.filter(pk=rest_id).first()
        user_product = TelegramUserProduct.objects.filter(pk=product_id).first()
        if user_product:
            addition = Addition.objects.filter(pk=addition_id).first()
            if addition:
                user.step = action.add_addition(rest_id, user_product, addition)

    elif 'productpayanother_' in c.data:
        try:
            param = c.data.split('_')
            rest_id = int(param[1])
            product_id = int(param[2])
        except Exception as err:
            LOG.error(err)
            return
        user.step = action.pay_another_card(rest_id, product_id)

    elif 'choicecard_' in c.data:
        try:
            param = c.data.split('_')
            rest_id = int(param[1])
            user_card_id = int(param[2])
            transaction_id = int(param[3])
        except Exception as err:
            LOG.error(err)
            return
        user.step = action.choice_card(rest_id, transaction_id, user_card_id)

    elif 'productbonuspay_' in c.data:
        try:
            param = c.data.split('_')
            restaurant_id = int(param[1])
            user_product_id = int(param[2])
        except Exception as err:
            LOG.error(err)
            return
        user_product = TelegramUserProduct.objects.filter(pk=user_product_id).first()
        if not user_product:
            bot.send_message(chat_id=action.message.chat.id,
                             text="такой продукт больше не существует, выберите его заново")
            return 1

        user_product.is_store = True
        user_product.save()
        restaurant = Restaurant.objects.filter(pk=restaurant_id).first()

        additions_price = 0
        for addition in user_product.additions.all():
            additions_price += addition.price * 100
        transaction = Transaction(user=user, count=user_product.product.price * 100 + additions_price, restaurant=restaurant)
        transaction.save()
        transaction.products.add(user_product)
        transaction.save()

        user.step = action.pay_bonuses(restaurant_id, transaction.pk)

    user.save()



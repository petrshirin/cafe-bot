from .models import *
from telebot import TeleBot, types, apihelper
from geopy import distance as geopy_distance
from .menu_parser import *
from .pay_system import *
from django.db.models import Q
from django.utils import timezone


class BotAction:

    def __init__(self, bot, message, user):
        self.bot = bot
        self.message = message
        self.user = user

    def get_message_text(self, tag, message):
        message_to_send = TelegramMessage.objects.filter(tag=tag, bot=self.user.telegram_bot).first()
        if not message_to_send:
            return message
        else:
            return message_to_send.text

    def accept_order(self, transaction_id):
        transaction = Transaction.objects.filter(pk=transaction_id).first()
        if not transaction:
            pass
        message_text_user = self.get_message_text('accept_order', 'Заказ принят в обработку')
        markup = types.InlineKeyboardMarkup(row_width=1)
        transaction.status = 4
        transaction.save()
        markup.add(types.InlineKeyboardButton('✅Завершить заказ', callback_data=f'confirmorder_{transaction_id}'))
        self.bot.edit_message_text(chat_id=self.user.user_id, text=self.message.text, message_id=self.message.message_id, reply_markup=markup)
        self.bot.send_message(transaction.user.user_id, message_text_user)
        return self.user.step

    def confirm_order(self, transaction_id):
        transaction = Transaction.objects.filter(pk=transaction_id).first()
        if not transaction:
            pass
        message_text_user = self.get_message_text('accept_order', f'Заказ №{transaction.pk}, покажите это сообщение или чек об оплате')
        transaction.status = 5
        transaction.save()
        self.bot.edit_message_text(chat_id=self.user.user_id, text="ВЫПОЛНЕН\n\n" + self.message.text, message_id=self.message.message_id)
        self.bot.send_message(transaction.user.user_id, message_text_user)
        return self.user.step

    def main_menu(self):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(types.KeyboardButton(self.get_message_text('restaurant_button_name', 'Заведения')), types.KeyboardButton('🛒Корзина'))
        markup.add(types.KeyboardButton('🎁Скидки и бонусы'), types.KeyboardButton('⚙️Настройки'))
        message_text = self.get_message_text('main_menu', 'Главное меню')
        self.bot.send_message(self.message.chat.id, message_text, reply_markup=markup)

        return 1

    def settings(self):
        markup = types.InlineKeyboardMarkup(row_width=3)
        markup.add(types.InlineKeyboardButton('💳Карты', callback_data='my_cards'),
                   types.InlineKeyboardButton('🧾Чеки', callback_data='my_cheques'),
                   types.InlineKeyboardButton('Назад', callback_data='main_menu'))
        message_text = self.get_message_text('settings', 'Ваши настройки')
        self.bot.send_message(self.message.chat.id, message_text, reply_markup=markup)
        return 10

    def cheques(self, added=None):
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton('Ввести Email', callback_data='add_email'))
        markup.add(types.InlineKeyboardButton('Назад', callback_data='settings'))
        message_text = self.get_message_text('cheques', 'Вы можете получать e-mail онлайн чеки.')
        if added:
            message_text += '\n\n\nEmail изменен'
        try:
            self.bot.edit_message_text(chat_id=self.message.chat.id, text=message_text,
                                       message_id=self.message.message_id, reply_markup=markup)
        except Exception as err:
            self.bot.send_message(self.message.chat.id, message_text, reply_markup=markup)
        return 20

    def add_email(self):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=1)
        markup.add(types.KeyboardButton('Отмена'))
        message_text = self.get_message_text('add_email', 'Введите Email на который хотети получать чеки об оплате')
        self.bot.send_message(self.message.chat.id, message_text, reply_markup=markup)
        return 21

    def cards(self):
        markup = types.InlineKeyboardMarkup(row_width=1)
        cards = Card.objects.filter(user=self.user).all()
        for card in cards:
            markup.add(types.InlineKeyboardButton(f'{card.card_number}', callback_data=f'mycard_{card.pk}'))
        markup.add(types.InlineKeyboardButton('Назад', callback_data='settings'))
        message_text = self.get_message_text('cards', 'Ваши карты, выберите карту, чтобы удалить ее')
        self.bot.edit_message_text(chat_id=self.message.chat.id, text=message_text,
                                   message_id=self.message.message_id, reply_markup=markup)
        return 30

    def show_card(self, card_id):
        markup = types.InlineKeyboardMarkup(row_width=1)
        card = Card.objects.filter(user=self.user, pk=card_id).first()
        if card:
            markup.add(types.InlineKeyboardButton('Удалить', callback_data=f'deletecard_{card.pk}'))
            markup.add(types.InlineKeyboardButton('Назад', callback_data='my_cards'))
            message_text = self.get_message_text('card', 'Ваша карта:\n\n{}\n\nВыберите действие.').format(card.card_number)
            self.bot.edit_message_text(chat_id=self.message.chat.id, text=message_text,
                                       message_id=self.message.message_id, reply_markup=markup)
            return 31
        else:
            self.bot.send_message(self.message.chat.id, 'Такой карты не существует')
            return self.cards()

    def delete_card(self, card_id):
        card = Card.objects.filter(user=self.user, pk=card_id).first()
        if card:
            card.is_deleted = True
            card.save()
            return self.cards()
        else:
            self.bot.send_message(self.message.chat.id, 'Такой карты не существует')
            return self.cards()

    def bonus_system(self):
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton('Скидки на 23 и 8 марта', callback_data='people_days_sale'),
                   types.InlineKeyboardButton('Бонусная программа', callback_data='base_bonus_system'))
        message_text = self.get_message_text('bonus_system', 'Бонусы и скидки.')
        self.bot.edit_message_text(chat_id=self.message.chat.id, text=message_text,
                                   message_id=self.message.message_id, reply_markup=markup)
        return 40

    def bonus_systems(self):
        markup = types.InlineKeyboardMarkup(row_width=1)
        message_text = self.get_message_text('bonus_systems', 'Ваши 🎁Скидки и бонусы, нажмите, для подробной информации')
        sales = UserSale.objects.filter(sale__bot=self.user.telegram_bot, user=self.user)
        for sale in sales:
            markup.add(types.InlineKeyboardButton(f'{sale.sale.name}', callback_data=f'sale_{sale.pk}'))
        markup.add(types.InlineKeyboardButton('Назад', callback_data='main_menu'))
        self.bot.send_message(chat_id=self.message.chat.id, text=message_text, reply_markup=markup)
        return self.user.step

    def sale(self, user_sale_id):
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton('Назад', callback_data='my_sales'))
        sale = UserSale.objects.filter(pk=user_sale_id).first()
        if sale:
            message_text = f'{sale.sale.name}\n\n{sale.sale.description}'
            if sale.sale.is_cash_back:
                message_text += f'\n\nСейчас у вас {self.user.bonus.count} бонусов'
                if self.user.bonus.count != 0:
                    markup.add(types.InlineKeyboardButton('Потратить', callback_data='all_restaurants'))
            self.bot.edit_message_text(chat_id=self.message.chat.id, text=message_text,
                                       message_id=self.message.message_id, reply_markup=markup)
            return self.user.step
        else:
            self.bot.send_message(self.message.chat.id, 'Такой скидки больше не существует')
            return self.bonus_system()

    def basket(self):
        markup = types.InlineKeyboardMarkup(row_width=2)
        user_basket = self.user.telegrambasket
        products = user_basket.products.all()
        for product in products:
            markup.add(types.InlineKeyboardButton(f'{product.product.name} {product.product.volume}{product.product.unit} ({product.product.price}руб.)', callback_data=f'productbasket_{product.id}'))
        markup.add(types.InlineKeyboardButton('❌Очистить корзину', callback_data='clear_basket'),
                   types.InlineKeyboardButton('📖История заказов', callback_data='basket_history'))
        if products:
            markup.add(types.InlineKeyboardButton('↩️Назад к выбору продуктов', callback_data=f'restaurant_{user_basket.products.all()[0].restaurant.pk}_0'))
            markup.add(types.InlineKeyboardButton('✅Завершить текущий заказ', callback_data='complete_current_order'))
        message_text = self.get_message_text('basket', 'Ваша корзина\n\n Нажмите на продукт чтобы удалить')
        self.bot.send_message(self.message.chat.id, message_text, reply_markup=markup)
        return 7

    def clear_basket(self):
        user_basket = self.user.telegrambasket
        user_basket.products.all().delete()
        return self.basket()

    def basket_history(self):
        transactions = Transaction.objects.filter(user=self.user, status=5, is_bonuses=False).all()
        markup = types.InlineKeyboardMarkup(row_width=1)
        for transaction in transactions:
            markup.add(types.InlineKeyboardButton(f'{transaction.pk} {transaction.restaurant.name} {transaction.count / 100}руб.', callback_data=f'repeatpay_{transaction.pk}'))
        markup.add(types.InlineKeyboardButton('Назад', callback_data='basket'))
        message_text = self.get_message_text('basket_history', 'Ваша история заказов')
        self.bot.edit_message_text(chat_id=self.message.chat.id, message_id=self.message.message_id,
                                   text=message_text, reply_markup=markup)
        return self.user.step

    def product_basket(self, product_id):
        user_product = TelegramUserProduct.objects.filter(pk=product_id).first()
        if not user_product:
            self.bot.edit_message_text(chat_id=self.message.chat.id,
                                       text="Вы не можете это сделать")
            return self.basket()
        user_product.delete()
        markup = types.InlineKeyboardMarkup(row_width=2)
        user_basket = self.user.telegrambasket
        for product in user_basket.products.all():
            markup.add(types.InlineKeyboardButton(f'{product.product.name} {product.product.volume}{product.product.unit} ({product.product.price}руб.)', callback_data=f'productbasket_{product.id}'))
        markup.add(types.InlineKeyboardButton('❌Очистить корзину', callback_data='clear_basket'),
                   types.InlineKeyboardButton('📖История заказов', callback_data='basket_history'))
        if user_basket.products.all():
            markup.add(types.InlineKeyboardButton('✅Завершить текущий заказ', callback_data='complete_current_order'))
        message_text = self.get_message_text('basket', 'Ваша корзина\n\n Нажмите на продукт чтобы удалить')
        self.bot.edit_message_text(chat_id=self.message.chat.id, text=message_text, message_id=self.message.message_id, reply_markup=markup)

    def complete_current_order(self):
        user_products = TelegramUserProduct.objects.filter(is_basket=True, is_store=False, user=self.user).all()
        count = 0
        transaction = Transaction(user=self.user, restaurant=user_products[0].restaurant)
        transaction.save()
        for user_product in user_products:
            transaction.products.add(user_product)
            count += user_product.product.price * 100
            for addition in user_product.additions.all():
                count += addition.price * 100
        transaction.count = count
        transaction.save()
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton('💳Оплатить картой', callback_data=f'paycardcompleteorder_{transaction.pk}'))
        if self.user.bonus.count >= count / 100:
            markup.add(types.InlineKeyboardButton('🎁Оплатить бонусами', callback_data=f'cardcompletebonusorder_{transaction.pk}'))
        markup.add(types.InlineKeyboardButton('В корзину', callback_data=f'basket'))
        message_text = self.get_message_text('buyproduct', 'Выберите действие\n\n')
        self.bot.edit_message_text(chat_id=self.message.chat.id, message_id=self.message.message_id,
                                   text=message_text, reply_markup=markup)
        return self.user.step

    def pay_card_current_order(self, transaction_id):
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup = self.card_complete_order(transaction_id, markup)
        markup.add(types.InlineKeyboardButton('➕Оплатить новой картой', callback_data=f'cardcompleteanotherorder_{transaction_id}'))
        message_text = self.get_message_text('choice_card_type', 'Выберите Способ оплаты')
        self.bot.send_message(chat_id=self.message.chat.id, text=message_text, reply_markup=markup)
        return self.user.step

    def card_complete_order(self, transaction_id, markup):
        transaction = Transaction.objects.filter(pk=transaction_id).first()

        user_cards = Card.objects.filter(~Q(rebill_id=None), is_deleted=False, user=self.user).all()
        for user_card in user_cards:
            markup.add(types.InlineKeyboardButton(f'{user_card.card_number}', callback_data=f'choicecard_{transaction.restaurant.pk}_{user_card.pk}_{transaction.pk}'))
        user_basket = self.user.telegrambasket
        user_basket.products.all().delete()
        return markup

    def card_complete_order_another(self, transaction_id):
        transaction = Transaction.objects.filter(pk=transaction_id).first()
        restaurant = transaction.restaurant

        for user_product in transaction.products.all():
            user_product.is_store = True
            user_product.save()

        owner = restaurant.telegram_bot.owner
        payment_system = PaySystem(restaurant.restaurantsettings.payment_type, TinkoffPay, owner.ownersettings.terminal_key, owner.ownersettings.password)
        transaction = payment_system.init_pay(self.user, transaction)

        if transaction.url:
            message_text = self.get_message_text('payment_link', 'Ваша ссылка на оплату\n\n{}\n').format(transaction.url)
            self.bot.send_message(self.message.chat.id, message_text)
        else:
            manager = restaurant.managers.objects.filter(is_active=True).first()
            message_text = self.get_message_text('init_payment_fail', f'Произошла ошибка при созании платежа, обратитесь к [администратору](https://t.me/{manager.name})')
            self.bot.send_message(self.message.chat.id, message_text, parse_mode='Markdown')
        user_basket = self.user.telegrambasket
        user_basket.products.all().delete()
        return self.user.step

    def card_complete_order_bonus(self, transaction_id):
        transaction = Transaction.objects.filter(pk=transaction_id).first()
        restaurant = transaction.restaurant

        for user_product in transaction.products.all():
            user_product.is_store = True
            user_product.save()
        self.pay_bonuses(restaurant.pk, transaction.pk)

    def repeat_pay(self, transaction_id):
        transaction = Transaction.objects.filter(pk=transaction_id).first()
        count = 0
        for product in transaction.products.all():
            count += product.product.price
            for addition in product.additions.all():
                count += addition.price
        transaction.count = count

        if not transaction:
            message_text = self.get_message_text('invalid transaction', 'Транзакция устарела, закажите все товары заново')
            self.bot.edit_message_text(chat_id=self.message.chat.id, message_id=self.message.message_id,
                                       text=message_text)
            return self.user.step
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton('💳Оплатить картой', callback_data=f'paycardrepeat_{transaction.pk}'))
        if self.user.bonus.count >= count / 100:
            markup.add(types.InlineKeyboardButton('🎁Оплатить бонусами', callback_data=f'cardrepeatbonus_{transaction.pk}'))
        markup.add(types.InlineKeyboardButton('Вернуться к истории заказов', callback_data=f'basket_history'))
        message_text = self.get_message_text('buyproduct', 'Выберите действие\n\n')
        self.bot.edit_message_text(chat_id=self.message.chat.id, message_id=self.message.message_id,
                                   text=message_text, reply_markup=markup)
        user_basket = self.user.telegrambasket
        user_basket.products.all().delete()
        return self.user.step

    def pay_card_repeat_menu(self, transaction_id):
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton('Повторить заказ', callback_data=f'cardrepeat_{transaction_id}'))
        markup.add(types.InlineKeyboardButton('➕Оплатить новой картой', callback_data=f'cardrepeatanother_{transaction_id}'))
        markup.add(types.InlineKeyboardButton('Назад', callback_data=f'repeatpay_{transaction_id}'))
        message_text = self.get_message_text('choice_card_type', 'Выберите Способ оплаты')
        self.bot.send_message(chat_id=self.message.chat.id, text=message_text, reply_markup=markup)
        return self.user.step

    def card_repeat(self, transaction_id):
        transaction = Transaction.objects.filter(pk=transaction_id).first()
        transaction = Transaction(user=transaction.user, count=transaction.count, restaurant=transaction.restaurant, card=transaction.card)
        transaction.save()
        owner = transaction.restaurant.telegram_bot.owner.pk
        payment_system = PaySystem(transaction.restaurant.restaurantsettings.payment_type, TinkoffPay, owner.ownersettings.terminal_key, owner.ownersettings.password)
        transaction = payment_system.do_pay(self.user, transaction, transaction.card)
        transaction.save()
        if transaction.payment_id:
            self.bot.send_message(self.message.chat.id, "Заказ выполняется")
        else:
            self.bot.send_message(self.message.chat.id, "Произошла ошибка при заказе")
        return self.user.step

    def card_repeat_another(self, transaction_id):
        transaction = Transaction.objects.filter(pk=transaction_id).first()
        transaction = Transaction(user=transaction.user, count=transaction.count, restaurant=transaction.restaurant, card=transaction.card)
        transaction.save()

        restaurant = transaction.restaurant

        owner = restaurant.telegram_bot.owner
        payment_system = PaySystem(restaurant.restaurantsettings.payment_type, TinkoffPay, owner.ownersettings.terminal_key, owner.ownersettings.password)
        transaction = payment_system.init_pay(self.user, transaction)

        if transaction.url:
            message_text = self.get_message_text('payment_link', 'Ваша ссылка на оплату\n\n{}\n').format(transaction.url)
            self.bot.send_message(self.message.chat.id, message_text)
        else:
            manager = restaurant.managers.objects.filter(is_active=True).first()
            message_text = self.get_message_text('init_payment_fail', f'Произошла ошибка при созании платежа, обратитесь к [администратору](https://t.me/{manager.name})')
            self.bot.send_message(self.message.chat.id, message_text, parse_mode='Markdown')
        return self.user.step

    def card_repeat_bonus(self, transaction_id):
        transaction = Transaction.objects.filter(pk=transaction_id).first()
        transaction = Transaction(user=transaction.user, count=transaction.count, restaurant=transaction.restaurant, card=transaction.card)
        transaction.save()

        restaurant = transaction.restaurant
        self.pay_bonuses(restaurant.pk, transaction.pk)

    def restaurants(self):
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton('Ближайшие', callback_data='nearest_restaurants'))
        restaurants = Restaurant.objects.filter(telegram_bot=TelegramBot.objects.get(token=self.bot.token)).all()
        for restaurant in restaurants:
            markup.add(types.InlineKeyboardButton(restaurant.restaurantsettings.address, callback_data=f'restaurant_{restaurant.pk}_0'))
        message_text = self.get_message_text('restaurants', 'Наши заведения')
        self.bot.send_message(self.message.chat.id, message_text, reply_markup=markup)
        return 2

    def all_restaurants(self):
        restaurants = Restaurant.objects.filter(telegram_bot=TelegramBot.objects.get(token=self.bot.token)).all()
        markup = types.InlineKeyboardMarkup(row_width=1)
        for restaurant in restaurants:
            markup.add(types.InlineKeyboardButton(restaurant.restaurantsettings.address, callback_data=f'restaurant_{restaurant.pk}_0'))
        message_text = self.get_message_text('all_restaurants', 'Выберите из списка ниже заведение.')
        self.bot.send_message(self.message.chat.id, message_text, reply_markup=markup)

        return 3

    def send_location(self):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2, one_time_keyboard=True)
        markup.add(types.KeyboardButton('Мое местоположение', request_location=True),
                   types.KeyboardButton('Главное меню'))

        message_text = self.get_message_text('nearest_restaurant', 'Отправьте свое местоположение, чтобы найти ближайший ресторан')
        self.bot.send_message(self.message.chat.id, message_text, reply_markup=markup)
        return 4

    def nearest_restaurant(self, latitude, longitude):
        restaurants = Restaurant.objects.filter(telegram_bot=TelegramBot.objects.get(token=self.bot.token)).all()
        distances = []
        for restaurant in restaurants:
            rest_latitude = restaurant.restaurantsettings.latitude
            rest_longitude = restaurant.restaurantsettings.longitude
            rest_distance = '{:.3f}'.format(geopy_distance.vincenty((latitude, longitude), (rest_latitude, rest_longitude)).km)
            distances.append(rest_distance)
        markup = types.InlineKeyboardMarkup(row_width=1)
        distances.sort()
        rang = 3
        if len(distances) < 3:
            rang = len(distances)
        for i in range(0, rang):
            markup.add(types.InlineKeyboardButton(f'{restaurants[i].restaurantsettings.address} ({distances[i]}km)', callback_data=f'restaurant_{restaurants[i].pk}_0'))
        message_text = self.get_message_text('nearests_restaurants', 'Выберите один из ближайших ресторанов')
        self.bot.send_message(self.message.chat.id, message_text, reply_markup=markup)
        return 5

    def restaurant_category(self, restaurant_id, rest_category, page):
        restaurant = Restaurant.objects.get(pk=restaurant_id)
        markup = types.InlineKeyboardMarkup(row_width=3)
        offset_menu = page * 10
        menu = rest_category
        max_pages = int((len(menu.products) + len(menu.categories)) / 5) if ((len(menu.products) + len(menu.categories)) % 5 == 0) else int((len(menu.products) + len(menu.categories)) / 5 + 1)
        next_page = (page + 1) if (page + 1 < max_pages) else 0
        previous_page = (page - 1) if (page - 1 > 0) else max_pages - 1
        all_items = menu.products + menu.categories
        print(len(menu.products) + len(menu.categories))
        for j in range(offset_menu, offset_menu + 10):
            if j >= (len(menu.products) + len(menu.categories)):
                break
            item = all_items[j]
            if isinstance(item, MenuStruct):
                markup.add(types.InlineKeyboardButton(f'{item.name}', callback_data=f'category_{restaurant.pk}_{item.id}_0'))
            elif isinstance(item, MenuProduct):
                markup.add(types.InlineKeyboardButton(f'{item.name} {item.volume} {item.unit}.({item.price}₽)', callback_data=f'product_{restaurant.pk}_{item.id}'))

        if len(menu.products) + len(menu.categories) > 10:
            markup.add(types.InlineKeyboardButton(f'{previous_page}/{max_pages}', callback_data=f'category_{restaurant.pk}_{menu.id}_{previous_page}'),
                       types.InlineKeyboardButton('Назад', callback_data=f'category_{restaurant.pk}_{menu.previous_id}_0'),
                       types.InlineKeyboardButton(f'{next_page}/{max_pages}', callback_data=f'category_{restaurant.pk}_{menu.id}_{next_page}'))
        else:
            if menu.previous_id == -1:
                markup.add(types.InlineKeyboardButton('Назад', callback_data=f'all_restaurants'))
            else:
                markup.add(types.InlineKeyboardButton('Назад', callback_data=f'category_{restaurant.pk}_{menu.previous_id}_0'))
        message_text = self.get_message_text('category', 'Выберите категорию или товар')
        try:
            self.bot.edit_message_text(chat_id=self.message.chat.id, message_id=self.message.message_id,
                                       text=message_text, reply_markup=markup)
        except apihelper.ApiException:
            self.bot.send_message(chat_id=self.message.chat.id, text=message_text, reply_markup=markup)
        return self.user.step

    def restaurant_menu(self, restaurant_id, page, struct):
        restaurant = Restaurant.objects.get(pk=restaurant_id)
        menu = struct
        offset_menu = page * 10
        max_pages = int(len(menu.products) / 5) if (len(menu.products) % 5 == 0) else int(len(menu.products) / 5 + 1)
        next_page = (page + 1) if (page + 1 < max_pages) else 0
        previous_page = (page - 1) if (page - 1 > 0) else max_pages - 1
        markup = types.InlineKeyboardMarkup(row_width=3)
        for i in range(offset_menu, offset_menu + 10):
            if i >= len(menu.products):
                break
            markup.add(types.InlineKeyboardButton(f'{menu.products[i].name} {menu.products[i].volume} {menu.products[i].unit}.({menu.products[i].price}₽)', callback_data=f'product_{restaurant.pk}_{menu.products[i].id}'))
        if len(menu.products) > 10:
            markup.add(types.InlineKeyboardButton(f'{previous_page + 1}/{max_pages}', callback_data=f'category_{restaurant.pk}_{menu.id}_{previous_page}'),
                       types.InlineKeyboardButton(f'Назад', callback_data=f'category_{restaurant.pk}_{menu.previous_id}_0'),
                       types.InlineKeyboardButton(f'{next_page + 1}/{max_pages}', callback_data=f'category_{restaurant.pk}_{menu.id}_{previous_page}'))
        else:
            markup.add(types.InlineKeyboardButton('Назад', callback_data=f'category_{restaurant.pk}_{menu.previous_id}_0'))
        message_text = self.get_message_text('restaurant', 'Выберите товар')
        self.bot.edit_message_text(chat_id=self.message.chat.id, message_id=self.message.message_id, text=message_text, reply_markup=markup)

        return self.user.step

    def restaurant_product(self, restaurant_id, product):
        restaurant = Restaurant.objects.get(pk=restaurant_id)
        product_orm = restaurant.products.filter(pk=product.id).first()
        if product_orm:
            user_product = TelegramUserProduct.objects.filter(user=self.user, product=product_orm,
                                                              is_basket=False, is_store=False).first()
            if not user_product:
                user_product = TelegramUserProduct(user=self.user, product=product_orm, is_basket=False, is_store=False, restaurant=restaurant)
                user_product.save()

            addition_price = 0
            for addition in user_product.additions.all():
                addition_price += addition

            message_text = self.get_message_text('product', 'Вы выбрали: {}')
            if addition_price:
                message_text = message_text.format(f'\n{product_orm.name}\n{product_orm.volume} {product_orm.unit}.\n{product_orm.price} + {addition_price}₽\n\n{product_orm.description}')
            else:
                message_text = message_text.format(f'\n{product_orm.name}\n{product_orm.volume} {product_orm.unit}.\n{product_orm.price} + {addition_price}₽\n\n{product_orm.description}')

            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(types.InlineKeyboardButton('✅Купить', callback_data=f'buyproduct_{restaurant.pk}_{user_product.product.pk}'))
            if product_orm.additions.all():
                markup.add(types.InlineKeyboardButton(f'⚙️Опции продукта', callback_data=f'additions_{restaurant.pk}_{user_product.pk}'))
            markup.add(types.InlineKeyboardButton(f'Назад', callback_data=f'category_{restaurant.pk}_{product.previous_id}_0'))

            if product_orm.image:
                self.bot.send_photo(self.message.chat.id, open(product_orm.image.path, 'rb'), caption=message_text, reply_markup=markup)
            else:
                self.bot.edit_message_text(chat_id=self.message.chat.id, text=message_text, message_id=self.message.message_id, reply_markup=markup)
        else:
            message_text = self.get_message_text('product_not_found', 'Извините, такого продукта сейчас нет.')
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(types.InlineKeyboardButton(f'Назад', callback_data=f'category_{restaurant.pk}_{product.previous_id}'))
            self.bot.edit_message_text(chat_id=self.message.chat.id, text=message_text, message_id=self.message.message_id, reply_markup=markup)
        return self.user.step

    def restaurant_additions(self, restaurant_id, user_product, additions):
        restaurant = Restaurant.objects.get(pk=restaurant_id)
        markup = types.InlineKeyboardMarkup(row_width=1)
        count_additions = 0
        all_user_additions = user_product.additions.all()
        for addition in additions:
            addition_orm = Addition.objects.filter(pk=addition.id).first()
            if addition_orm and addition_orm not in all_user_additions:
                count_additions += 1
                markup.add(types.InlineKeyboardButton(f'{addition_orm.name} ({addition_orm.price}₽)', callback_data=f'additionadd_{restaurant.pk}_{user_product.pk}_{addition_orm.pk}'))
        markup.add(types.InlineKeyboardButton('Назад', callback_data=f'product_{restaurant.pk}_{user_product.product.pk}'))

        if count_additions == 0:
            message_text = self.get_message_text('additions_not_found', 'В этот продукт ничего нельзя добавить')
            try:
                self.bot.edit_message_text(chat_id=self.message.chat.id, text=self.message.text + f'\n\n{message_text}',
                                           message_id=self.message.message_id, reply_markup=markup)
            except Exception as err:
                print(err)
                self.bot.edit_message_caption(chat_id=self.message.chat.id, caption=self.message.caption + f'\n\n{message_text}',
                                              message_id=self.message.message_id, reply_markup=markup)

        else:
            message_text = self.get_message_text('additions', 'Выберите, что хотите добавить')
            try:
                self.bot.edit_message_text(chat_id=self.message.chat.id, text=self.message.text + f'\n\n{message_text}',
                                           message_id=self.message.message_id, reply_markup=markup)
            except Exception as err:
                print(err)
                self.bot.edit_message_caption(chat_id=self.message.chat.id, caption=self.message.caption + f'\n\n{message_text}',
                                              message_id=self.message.message_id, reply_markup=markup)
        return self.user.step

    def add_addition(self, restaurant_id, user_product, addition):
        restaurant = Restaurant.objects.get(pk=restaurant_id)
        markup = types.InlineKeyboardMarkup(row_width=1)
        user_product.additions.add(addition)
        user_product.save()
        count_additions = 0
        all_user_additions = user_product.additions.all()
        for addition in user_product.product.additions.all():
            addition_orm = Addition.objects.filter(pk=addition.id).first()
            if addition_orm and addition_orm not in all_user_additions:
                count_additions += 1
                markup.add(types.InlineKeyboardButton(f'{addition_orm.name} ({addition_orm.price}₽)', callback_data=f'additionadd_{restaurant.pk}_{user_product.pk}_{addition_orm.pk}'))
        markup.add(types.InlineKeyboardButton('Назад', callback_data=f'product_{restaurant.pk}_{user_product.product.pk}'))

        addition_added = f'{addition.name} добавлен\n'
        addition_price = 0
        for addition in user_product.additions.all():
            addition_price += addition

        message_text = self.get_message_text('product', 'Вы выбрали: {}')
        if addition_price:
            message_text = message_text.format(f'\n{user_product.product.name}\n{user_product.product.volume} {user_product.product.unit}.\n{user_product.product.price} + {addition_price}₽\n\n{user_product.product.description}')
        else:
            message_text = message_text.format(f'\n{user_product.product.name}\n{user_product.product.volume} {user_product.product.unit}.\n{user_product.product.price} + {addition_price}₽\n\n{user_product.product.description}')
        try:
            self.bot.edit_message_text(chat_id=self.message.chat.id, text=message_text + f'\n\n{addition_added}',
                                       message_id=self.message.message_id, reply_markup=markup)
        except Exception as err:
            print(err)
            self.bot.edit_message_caption(chat_id=self.message.chat.id, text=message_text + f'\n\n{addition_added}',
                                       message_id=self.message.message_id, reply_markup=markup)
        return self.user.step

    def buy_product(self, restaurant_id, product_id):
        restaurant = Restaurant.objects.get(pk=restaurant_id)
        markup = types.InlineKeyboardMarkup(row_width=1)
        last_transaction = Transaction.objects.filter(user=self.user, status=0, url=None)
        if last_transaction:
            last_transaction.delete()
        product_orm = restaurant.products.filter(pk=product_id).first()
        if product_orm:
            user_product = TelegramUserProduct.objects.filter(user=self.user, product=product_orm,
                                                              is_basket=False, is_store=False).first()
            additions_price = 0
            for addition in user_product.product.additions.all():
                additions_price += addition.price

            if user_product:
                markup.add(types.InlineKeyboardButton('➡️Добавить в корзину и продолжить покупки', callback_data=f'addtobasket_{restaurant.pk}_{user_product.pk}'))
                markup.add(types.InlineKeyboardButton('💳Оплатить картой', callback_data=f'paycardproduct_{restaurant.pk}_{user_product.pk}'))
                if self.user.bonus.count >= user_product.product.price + additions_price:
                    markup.add(types.InlineKeyboardButton('🎁Оплатить бонусами', callback_data=f'productbonuspay_{restaurant.pk}_{user_product.pk}'))
                markup.add(types.InlineKeyboardButton('🛒Перейти в корзину', callback_data=f'basket'))
                markup.add(types.InlineKeyboardButton('Вернуться к продукту', callback_data=f'product_{restaurant.pk}_{user_product.product.pk}'))
                message_text = self.get_message_text('buyproduct', 'Выберите действие')
                self.bot.send_message(chat_id=self.message.chat.id, text=message_text, reply_markup=markup)
            else:
                message_text = self.get_message_text('invalid_user_product', 'Вы не можете выбрать этот продукт')
                self.bot.send_message(chat_id=self.message.chat.id, text=message_text, reply_markup=markup)

        else:
            message_text = self.get_message_text('product_not_found', 'Извините, такого продукта сейчас нет.')
            self.bot.send_message(chat_id=self.message.chat.id, text=message_text)
        return self.user.step

    def pay_card_product(self, restaurant_id, user_product_id):
        user_product = TelegramUserProduct.objects.filter(pk=user_product_id).first()
        if not user_product:
            self.bot.send_message(chat_id=self.message.chat.id, text="такой продукт больше не существует, выебрите его заного")
            return 1

        restaurant = Restaurant.objects.filter(pk=restaurant_id).first()

        additions_price = 0
        for addition in user_product.additions.all():
            additions_price += addition.price * 100
        transaction = Transaction(user=self.user, count=user_product.product.price * 100 + additions_price, restaurant=restaurant)
        transaction.save()

        markup = types.InlineKeyboardMarkup(row_width=1)
        markup = self.pay_card(restaurant_id, transaction, markup)
        markup.add(types.InlineKeyboardButton('➕Добавить новую карту', callback_data=f'productpayanother_{restaurant_id}_{user_product_id}'))
        markup.add(types.InlineKeyboardButton('Назад', callback_data=f'buyproduct_{restaurant_id}_{user_product.product.pk}'))
        message_text = self.get_message_text('choice_card_type', 'Выберите Способ оплаты')
        self.bot.send_message(chat_id=self.message.chat.id, text=message_text, reply_markup=markup)
        return self.user.step

    def add_to_basket(self, restaurant_id, user_product):

        # Вейк ап сити правка
        restaurant = Restaurant.objects.filter(pk=restaurant_id).first()
        menu = restaurant.menu_struct
        menu_struct = MenuStruct(menu, -1)
        user_product.is_basket = True
        user_product.save()
        self.user.telegrambasket.products.add(user_product)

        if menu_struct.type == 'products':
            self.restaurant_menu(restaurant.pk, 0, menu_struct)
        elif menu_struct.type == 'categories':
            self.restaurant_category(restaurant.pk, menu_struct, 0)

        message_text = self.get_message_text('added_to_basket', f'{user_product.product.name} добавлен в корзину')
        self.bot.send_message(self.message.chat.id, message_text)
        return self.user.step

        user_product.is_basket = True
        self.user.telegrambasket.products.add(user_product)
        message_text = self.get_message_text('added_to_basket', f'{user_product.product.name} добавлен в корзину')
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton(f'Добавить ещё 1', callback_data=f'repeatonemoreproduct_{user_product.pk}'))
        markup.add(types.InlineKeyboardButton(f'✅Завершить заказ', callback_data='complete_current_order'))
        markup.add(types.InlineKeyboardButton(f'Продолжить покупки', callback_data=f'restaurant_{restaurant_id}_0'))
        self.bot.edit_message_text(chat_id=self.message.chat.id, text=message_text, message_id=self.message.message_id, reply_markup=markup)
        user_product.save()
        return self.user.step

    def repeat_one_more_product(self, product_id):
        user_product = TelegramUserProduct.objects.filter(pk=product_id).first()
        if not user_product:
            self.bot.send_message(chat_id=self.message.chat.id, text="Такого продукта больше нет")
            return self.user.step
        new_user_product = TelegramUserProduct(user=user_product.user, product=user_product.product, restaurant=user_product.restaurant)
        new_user_product.save()
        for addition in user_product.additions.all():
            new_user_product.additions.add(addition)
        new_user_product.is_basket = True
        self.user.telegrambasket.products.add(new_user_product)
        message_text = self.get_message_text('added_to_basket', f'{new_user_product.product.name} добавлен в корзину')
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton(f'✅Завершить заказ', callback_data='complete_current_order'))
        markup.add(types.InlineKeyboardButton(f'Продолжить покупки', callback_data=f'restaurant_{new_user_product.restaurant.pk}_0'))
        markup.add(types.InlineKeyboardButton(f'Добавить ещё 1', callback_data=f'repeatonemoreproduct_{new_user_product.pk}'))
        self.bot.edit_message_text(chat_id=self.message.chat.id, text=self.message.text+"\nПродукт добавлен", message_id=self.message.message_id, reply_markup=markup)
        user_product.save()
        return self.user.step

    def pay_another_card(self, restaurant_id, product_id):
        try:
            product = TelegramUserProduct.objects.get(pk=product_id)
        except TelegramUserProduct.DoesNotExist:
            message_text = self.get_message_text('product_not_found', 'Извините, такого продукта сейчас нет.')
            self.bot.send_message(chat_id=self.message.chat.id, text=message_text)
            return self.user.step
        try:
            restaurant = Restaurant.objects.get(pk=restaurant_id)
        except Restaurant.DoesNotExist:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            markup.add(types.KeyboardButton('🛒Корзина'), types.KeyboardButton('Заведения'))
            markup.add(types.KeyboardButton('🎁Скидки и бонусы'), types.KeyboardButton('⚙️Настройки'))
            self.bot.send_message(self.message.chat.id, 'Ресторан пропал, закажите в другом', reply_markup=markup)
            return 1

        additions_price = 0
        for addition in product.additions.all():
            additions_price += addition.price * 100
        transaction = Transaction(user=self.user, count=product.product.price * 100 + additions_price, restaurant=restaurant)
        transaction.save()
        transaction.products.add(product)
        product.is_store = True
        product.save()
        owner = restaurant.telegram_bot.owner
        payment_system = PaySystem(restaurant.restaurantsettings.payment_type, TinkoffPay, owner.ownersettings.terminal_key, owner.ownersettings.password)
        transaction = payment_system.init_pay(self.user, transaction)

        if transaction.url:
            message_text = self.get_message_text('payment_link', 'Ваша ссылка на оплату\n\n{}\n').format(transaction.url)
            self.bot.send_message(self.message.chat.id, message_text)
            step = self.get_user_phone()
            return step
        else:
            manager = restaurant.managers.objects.filter(is_active=True).first()
            message_text = self.get_message_text('init_payment_fail', f'Произошла ошибка при созании платежа, обратитесь к [администратору](https://t.me/{manager.name})')
            self.bot.send_message(self.message.chat.id, message_text, parse_mode='Markdown')
        return self.user.step

    def get_user_phone(self):
        if not self.user.phone:
            message_text = self.get_message_text('get_phone', 'Введите свой номер телефона\n\n'
                                                              'Номер необходим для связи бариста с вами')
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=2)
            markup.add(types.KeyboardButton('Отправить свой телефон', request_contact=True),
                       types.KeyboardButton('Отмена'))
            self.bot.send_message(self.message.chat.id, message_text, reply_markup=markup)
            return 51
        else:
            return self.user.step

    def pay_card(self, restaurant_id, transaction, markup):
        restaurant = Restaurant.objects.get(pk=restaurant_id)
        user_cards = Card.objects.filter(~Q(rebill_id=None), is_deleted=False, user=self.user).all()
        for user_card in user_cards:
            markup.add(types.InlineKeyboardButton(f'{user_card.card_number}', callback_data=f'choicecard_{restaurant.pk}_{user_card.pk}_{transaction.pk}'))

        return markup

    def choice_card(self, restaurant_id, transaction_id, user_card_id):
        transaction = Transaction.objects.filter(pk=transaction_id).first()
        user_card = Card.objects.filter(pk=user_card_id).first()
        if transaction:
            for product in transaction.products.all():
                product.is_store = True
                product.save()
            try:
                restaurant = Restaurant.objects.get(pk=restaurant_id)
            except Restaurant.DoesNotExist:
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
                markup.add(types.KeyboardButton('🛒Корзина'), types.KeyboardButton('Заведения'))
                markup.add(types.KeyboardButton('🎁Скидки и бонусы'), types.KeyboardButton('⚙️Настройки'))
                self.bot.send_message(self.message.chat.id, 'Ресторан пропал, закажите в другом', reply_markup=markup)
                return 1
            owner = restaurant.telegram_bot.owner
            payment_system = PaySystem(restaurant.restaurantsettings.payment_type, TinkoffPay, owner.ownersettings.terminal_key, owner.ownersettings.password)
            card = user_card
            if not card:
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
                markup.add(types.KeyboardButton('🛒Корзина'), types.KeyboardButton('Заведения'))
                markup.add(types.KeyboardButton('🎁Скидки и бонусы'), types.KeyboardButton('⚙️Настройки'))
                self.bot.send_message(self.message.chat.id, 'Карта пропала, привяжите ее по новой.', reply_markup=markup)
                return 1

            transaction = payment_system.do_pay(self.user, transaction, card)

            if transaction.payment_id:
                message_text = self.get_message_text('do_pay', 'Платеж выполняется').format(transaction.url)
                self.bot.send_message(self.message.chat.id, message_text)
            else:
                manager = restaurant.managers.objects.filter(is_active=True).first()
                message_text = self.get_message_text('init_payment_fail', f'Произошла ошибка при созании платежа, обратитесь к [администратору](https://t.me/{manager.name})')
                self.bot.send_message(self.message.chat.id, message_text, parse_mode='Markdown')
        else:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            markup.add(types.KeyboardButton('🛒Корзина'), types.KeyboardButton('Заведения'))
            markup.add(types.KeyboardButton('🎁Скидки и бонусы'), types.KeyboardButton('⚙️Настройки'))
            self.bot.send_message(self.message.chat.id, 'Такой транзакции уже нет, выберите товар заного', reply_markup=markup)
            return 1
        return self.user.step

    def pay_bonuses(self, restaurant_id, transaction_id):
        transaction = Transaction.objects.filter(pk=transaction_id).first()

        if transaction:
            try:
                restaurant = Restaurant.objects.get(pk=restaurant_id)
            except Restaurant.DoesNotExist:
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
                markup.add(types.KeyboardButton('🛒Корзина'), types.KeyboardButton('Заведения'))
                markup.add(types.KeyboardButton('🎁Скидки и бонусы'), types.KeyboardButton('⚙️Настройки'))
                self.bot.send_message(self.message.chat.id, 'Ресторан пропал, закажите в другом', reply_markup=markup)
                return 1
            payment_system = PaySystem(restaurant.restaurantsettings.payment_type, TinkoffPay)
            transaction.is_bonuses = True
            try:
                transaction = payment_system.init_pay(self.user, transaction)
            except NotEnoughBonuses:
                message_text = self.get_message_text('not_enough_bonuses', 'У вас недостаточно бонусов на счете, оплатите заказ картой')
                self.bot.edit_message_text(chat_id=self.message.chat.id, text=self.message.text + f'\n\n{message_text}',
                                           message_id=self.message.message_id)
                return self.user.step
            message_text = self.get_message_text('complete_order_bonus', 'Заказ оплачен бонусами')
            self.bot.edit_message_text(chat_id=self.message.chat.id, text=message_text,
                                       message_id=self.message.message_id)
            transaction.status = 2
            manager = transaction.restaurant.managers.filter(is_active=True, is_free=True).first()
            if not manager:
                manager = transaction.restaurant.managers.filter(is_active=True).first()
                if not manager:
                    self.bot.send_message(transaction.user.user_id, 'Оплата произведена, сейчас нет работающих менеджеров, '
                                                                    'Мы помним про ваш заказ, как только он освободится, вам придет оповещение')
                    transaction.status = 6

            message_text = f'Заказ №{transaction.pk}\n'
            message_text += f'{self.user.user_name} tel: {self.user.phone}\n\n'
            for product in transaction.products.all():
                i = 1
                message_text += f'{product.product.name} {product.product.valume}{product.product.unit}\n'
                for addition in product.additions.all():
                    message_text += f'{i}. {addition.name}\n'
                message_text += '\n'
            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(types.InlineKeyboardButton('Принять заказ', callback_data=f'acceptorder_{transaction.pk}'))
            self.bot.send_message(manager.user_id, message_text, reply_markup=markup)
            transaction.save()
            return self.user.step

    def check_restaurant_time(self, restaurant_id=None):
        if restaurant_id is None:
            restaurants = Restaurant.objects.filter(telegram_bot=self.user.telegram_bot).all()
            for restaurant in restaurants:
                if restaurant.restaurantsettings.time_opened < timezone.now().time() or restaurant.restaurantsettings.time_closed > timezone.now().time():
                    return True
        else:
            restaurant = Restaurant.objects.filter(pk=restaurant_id).first()
            if restaurant:
                if restaurant.restaurantsettings.time_opened < timezone.now().time() or restaurant.restaurantsettings.time_closed > timezone.now().time():
                    return True
                else:
                    return False
            else:
                return False

    def check_restaurant_in_basket(self, restaurant_id):
        restaurant = Restaurant.objects.filter(pk=restaurant_id).first()
        if restaurant:
            basket = TelegramBasket.objects.filter(user=self.user).first()
            if basket:
                for product in basket.products.all():
                    if product.restaurant != restaurant:
                        markup = types.InlineKeyboardMarkup(row_width=1)
                        markup.add(types.InlineKeyboardButton(f'{product.restaurant.restaurantsettings.address}', callback_data=f'restaurant_{product.restaurant.pk}_0'))
                        self.bot.send_message(self.message.chat.id, self.get_message_text('two_restaurants_in_basket', 'Вы заказали уже в другом ресторане, отчистите корзина или продолжите покупки в этом ресторане'), reply_markup=markup)
                        return False
        return True

from .models import *
from telebot import TeleBot, types
from geopy import distance as geopy_distance
from .menu_parser import *
from .pay_system import *


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

    def main_menu(self):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(types.KeyboardButton('Корзина'), types.KeyboardButton('Заведения'))
        markup.add(types.KeyboardButton('Скидки и бонусы'), types.KeyboardButton('Настройки'))
        message_text = self.get_message_text('main_menu', 'Главное меню')
        print(self.bot.token)
        self.bot.send_message(self.message.chat.id, message_text, reply_markup=markup)

        return 1

    def settings(self):
        markup = types.InlineKeyboardMarkup(row_width=3)
        markup.add(types.InlineKeyboardButton('Карты', callback_data='my_cards'),
                   types.InlineKeyboardButton('Чеки', callback_data='my_cheques'),
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
        message_text = self.get_message_text('bonus_systems', 'Ваши кидки, нажмите, для подробной информации')
        sales = UserSale.objects.filter(sale__bot=self.user.telegram_bot)
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
            self.bot.edit_message_text(chat_id=self.message.chat.id, text=message_text,
                                       message_id=self.message.message_id, reply_markup=markup)
            return self.user.step
        else:
            self.bot.send_message(self.message.chat.id, 'Такой скидки больше не существует')
            return self.bonus_system()

    def basket(self):
        markup = types.InlineKeyboardMarkup(row_width=2)
        user_basket = self.user.telegrambasket
        for product in user_basket.products.all():
            markup.add(types.InlineKeyboardButton(f'{product.product.name} {product.product.volume} ({product.product.price})', callback_data=f'productbasket_{product.id}'))
        markup.add(types.InlineKeyboardButton('Отчистить корзину', callback_data='clear_basket'),
                   types.InlineKeyboardButton('История заказов', callback_data='basket_history'))
        markup.add(types.InlineKeyboardButton('Главное меню', callback_data='main_menu'))
        message_text = self.get_message_text('basket', 'Ваша корзина\n\n выберите продукт для подробной информации')
        self.bot.send_message(self.message.chat.id, message_text, reply_markup=markup)
        return 7

    def clear_basket(self):
        user_basket = self.user.telegrambasket
        user_basket.products.all().delete()
        return self.basket()

    def basket_history(self):
        transactions = Transaction.objects.filter(user=self.user, status=2, is_bonuses=False).all()
        markup = types.InlineKeyboardMarkup(row_width=1)
        for transaction in transactions:
            markup.add(types.InlineKeyboardButton(f'{transaction.pk} {transaction.restaurant.name} {transaction.count / 100}руб.', callback_data=f'createpay_{transaction.pk}'))
        markup.add(types.InlineKeyboardButton('Назад', callback_data='basket'))
        message_text = self.get_message_text('basket_history', 'Ваша история заказов')
        self.bot.edit_message_text(chat_id=self.message.chat.id, message_id=self.message.message_id,
                                   text=message_text, reply_markup=markup)
        return self.user.step

    def create_pay(self, transaction_id):
        transaction = Transaction.objects.filter(pk=transaction_id).first()
        transaction = Transaction(user=transaction.user, count=transaction.count, restaurant=transaction.restaurant, card=transaction.card)
        transaction.save()
        owner = transaction.restaurant.telegram_bot.owner.pk
        payment_system = PaySystem(transaction.restaurant.restaurantsettings.payment_type, TinkoffPay, owner.ownersettings.terminal_key, owner.ownersettings.password)
        transaction = payment_system.do_pay(self.user, transaction, transaction.card)
        transaction.save()
        if transaction.status == 1:
            self.bot.send_message(self.message.chat.id, "Заказ выполняется")
        else:
            self.bot.send_message(self.message.chat.id, "Произошла ошибка при заказе")
        return self.user.step

    def restaurants(self):
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(types.InlineKeyboardButton('Ближайшие', callback_data='nearest_restaurants'),
                   types.InlineKeyboardButton('Все адреса', callback_data='all_restaurants'))
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
            markup.add(types.InlineKeyboardButton(f'{restaurants[i].name} ({distances[i]}km)', callback_data=f'restaurant_{restaurants[i].pk}_0'))
        message_text = self.get_message_text('nearests_restaurants', 'Выберите один из ближайших ресторанов')
        self.bot.send_message(self.message.chat.id, message_text, reply_markup=markup)
        return 5

    def restaurant_category(self, restaurant_id, rest_category, page):
        restaurant = Restaurant.objects.get(pk=restaurant_id)
        markup = types.InlineKeyboardMarkup(row_width=3)
        offset_menu = page * 5
        menu = rest_category
        max_pages = int((len(menu.products) + len(menu.categories)) / 5) if ((len(menu.products) + len(menu.categories)) % 5 == 0) else int((len(menu.products) + len(menu.categories)) / 5 + 1)
        next_page = (page + 1) if (page + 1 < max_pages) else max_pages - 1
        previous_page = (page - 1) if (page - 1 > 0) else max_pages - 1
        all_items = menu.products + menu.categories
        print(len(menu.products) + len(menu.categories))
        for j in range(offset_menu, offset_menu + 5):
            if j >= (len(menu.products) + len(menu.categories)):
                break
            item = all_items[j]
            if isinstance(item, MenuStruct):
                markup.add(types.InlineKeyboardButton(f'{item.name}', callback_data=f'category_{restaurant.pk}_{item.id}_0'))
            elif isinstance(item, MenuProduct):
                markup.add(types.InlineKeyboardButton(f'{item.name} {item.volume} {item.unit}.({item.price}₽)', callback_data=f'product_{restaurant.pk}_{item.id}'))
            if j == 5:
                break

        markup.add(types.InlineKeyboardButton(f'{previous_page + 1}/{max_pages}', callback_data=f'category_{restaurant.pk}_{menu.id}_{previous_page}'),
                   types.InlineKeyboardButton('Назад', callback_data=f'category_{restaurant.pk}_{rest_category.previous_id}_0'),
                   types.InlineKeyboardButton(f'{next_page + 1}/{max_pages}', callback_data=f'category_{restaurant.pk}_{menu.id}_{previous_page}'))
        message_text = self.get_message_text('category', 'Выберите категорию или товар')
        self.bot.edit_message_text(chat_id=self.message.chat.id, message_id=self.message.message_id,
                                   text=message_text, reply_markup=markup)

        return self.user.step

    def restaurant_menu(self, restaurant_id, page, struct):
        restaurant = Restaurant.objects.get(pk=restaurant_id)
        menu = struct
        offset_menu = page * 5
        max_pages = int(len(menu.products) / 5) if (len(menu.products) % 5 == 0) else int(len(menu.products) / 5 + 1)
        next_page = (page + 1) if (page + 1 < max_pages) else max_pages - 1
        previous_page = (page - 1) if (page - 1 > 0) else max_pages - 1
        markup = types.InlineKeyboardMarkup(row_width=3)
        for i in range(offset_menu, offset_menu + 5):
            if i >= len(menu.products):
                break
            markup.add(types.InlineKeyboardButton(f'{menu.products[i].name} {menu.products[i].volume} {menu.products[i].unit}.({menu.products[i].price}₽)', callback_data=f'product_{restaurant.pk}_{menu.products[i].id}'))
        markup.add(types.InlineKeyboardButton(f'{previous_page + 1}/{max_pages}', callback_data=f'category_{restaurant.pk}_{menu.id}_{previous_page}'),
                   types.InlineKeyboardButton(f'Назад', callback_data=f'category_{restaurant.pk}_{menu.previous_id}_0'),
                   types.InlineKeyboardButton(f'{next_page + 1}/{max_pages}', callback_data=f'category_{restaurant.pk}_{menu.id}_{previous_page}'))
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
                user_product = TelegramUserProduct(user=self.user, product=product_orm, is_basket=False, is_store=False)
                user_product.save()
            message_text = self.get_message_text('product', 'Вы выбрали: {}')
            message_text = message_text.format(f'\n{product_orm.name}\n{product_orm.volume} {product_orm.unit}.\n{product_orm.price}₽\n\n{product_orm.description}')

            markup = types.InlineKeyboardMarkup(row_width=1)
            markup.add(types.InlineKeyboardButton('Купить', callback_data=f'buyproduct_{restaurant.pk}_{user_product.pk}'))
            if product.additions:
                markup.add(types.InlineKeyboardButton(f'Добавить что в {product_orm.name}', callback_data=f'additions_{restaurant.pk}_{user_product.pk}'))
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
        for addition in additions:
            addition_orm = Addition.objects.filter(pk=addition.id).first()
            if addition_orm:
                count_additions += 1
                markup.add(types.InlineKeyboardButton(f'{addition_orm.name} ({addition_orm.price}₽)', callback_data=f'additionadd_{restaurant.pk}_{user_product.pk}_{addition_orm.pk}'))
        markup.add(types.InlineKeyboardButton('Назад', callback_data=f'product_{restaurant.pk}_{additions[0].previos_id}'))

        if count_additions == 0:
            message_text = self.get_message_text('additions_not_found', 'В этот продукт ничего нельзя добавить')
            self.bot.edit_message_text(chat_id=self.message.chat.id, text=self.message.text + f'\n\n{message_text}',
                                       message_id=self.message.message_id)
        return self.user.step

    def add_addition(self, restaurant_id, user_product, addition):
        restaurant = Restaurant.objects.get(pk=restaurant_id)
        markup = types.InlineKeyboardMarkup(row_width=1)
        count_additions = 0
        user_product.additions.add(addition)
        user_product.save()
        for addition in user_product.product.additions.all():
            addition_orm = Addition.objects.filter(pk=addition.id).first()
            if addition_orm:
                if addition in user_product.additions.all() or addition == addition:
                    count_additions += 1
                    markup.add(types.InlineKeyboardButton(f'{addition_orm.name} ({addition_orm.price}₽)', callback_data=f'additionadd_{restaurant.pk}_{user_product.pk}_{addition_orm.pk}'))
        markup.add(types.InlineKeyboardButton('Назад', callback_data=f'product_{restaurant.pk}_{addition[0].previos_id}'))

        message_text = f'{addition.name} добавлен\n'
        self.bot.edit_message_text(chat_id=self.message.chat.id, text=self.message.text + f'\n\n{message_text}',
                                   message_id=self.message.message_id)
        return self.user.step

    def buy_product(self, restaurant_id, product_id):
        restaurant = Restaurant.objects.get(pk=restaurant_id)
        markup = types.InlineKeyboardMarkup(row_width=3)
        last_transaction = Transaction.objects.filter(user=self.user, status=0, url=None)
        if last_transaction:
            last_transaction.delete()
        product_orm = restaurant.products.filter(pk=product_id).first()
        if product_orm:
            user_product = TelegramUserProduct.objects.filter(user=self.user, product=product_orm,
                                                              is_basket=False, is_store=False).first()
            if user_product:
                markup.add(types.InlineKeyboardButton('Добавить в корзину и продолжить покупки', callback_data=f'addtobasket_{restaurant.pk}_{user_product.pk}'))
                markup.add(types.InlineKeyboardButton('Оплатить картой', callback_data=f'productpay_{restaurant.pk}_{user_product.pk}'))
                markup.add(types.InlineKeyboardButton('Оплатить другой картой', callback_data=f'productpayanouther_{restaurant.pk}_{user_product.pk}'))
                markup.add(types.InlineKeyboardButton('Оплатить бонусами', callback_data=f'productbonuspay_{restaurant.pk}_{user_product.pk}'))
                markup.add(types.InlineKeyboardButton('Перейти в корзину', callback_data=f'basket'))
                markup.add(types.InlineKeyboardButton('Вернуться к продукту', callback_data=f'buyproduct_{restaurant.pk}_{user_product.pk}'))
                message_text = self.get_message_text('buyproduct', 'Выберите действие')
                self.bot.edit_message_text(chat_id=self.message.chat.id, text=message_text, message_id=self.message.message_id, reply_markup=markup)


        else:
            message_text = self.get_message_text('product_not_found', 'Извините, такого продукта сейчас нет.')
            self.bot.edit_message_text(chat_id=self.message.chat.id, text=message_text, message_id=self.message.message_id)
        return self.user.step

    def add_to_basket(self, restaurant_id, user_product):
        user_product.is_basket = True
        self.user.telegrambasket.products.add(user_product)
        message_text = self.get_message_text('added_to_basket', f'{user_product.product.name} добавлен в корзину')
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton(f'Завершить заказ', callback_data='complete_order'))
        markup.add(types.InlineKeyboardButton(f'Продолжить покупки', callback_data=f'restaurant_{restaurant_id}'))
        self.bot.edit_message_text(chat_id=self.message.chat.id, text=message_text, message_id=self.message.message_id, reply_markup=markup)
        user_product.save()
        return self.user.step

    def calculate_sale(self):
        pass

    def pay_another_card(self, restaurant_id, product_id):
        try:
            product = TelegramUserProduct.objects.get(pk=product_id)
        except TelegramUserProduct.DoesNotExist:
            message_text = self.get_message_text('product_not_found', 'Извините, такого продукта сейчас нет.')
            self.bot.send_message(chat_id=self.message.chat.id, text=message_text)
            return self.user.step
        restaurant = Restaurant.objects.get(pk=restaurant_id)
        transaction = Transaction(user=self.user, count=product.product.price * 100)
        transaction.products.add(product)
        product.is_store = True
        product.save()
        owner = restaurant.telegram_bot.owner.pk
        payment_system = PaySystem(restaurant.restaurantsettings.payment_type, TinkoffPay, owner.ownersettings.terminal_key, owner.ownersettings.password)
        transaction = payment_system.init_pay(self.user, transaction)

        if transaction.url:
            message_text = self.get_message_text('payment_link', 'Ваша ссылка на оплату\n\n{}\n').format(transaction.url)
            self.bot.send_message(self.message.chat.id, message_text)
        else:
            message_text = self.get_message_text('init_payment_fail', 'Произошла ошибка при созании платежа, обратитесь к администратору')
            self.bot.send_message(self.message.chat.id, message_text)
        return self.user.step

    def pay_card(self, restaurant_id, product_id):
        try:
            product = TelegramUserProduct.objects.get(pk=product_id)
        except TelegramUserProduct.DoesNotExist:
            message_text = self.get_message_text('product_not_found', 'Извините, такого продукта сейчас нет.')
            self.bot.send_message(chat_id=self.message.chat.id, text=message_text)
            return self.user.step
        restaurant = Restaurant.objects.get(pk=restaurant_id)
        transaction = Transaction(user=self.user, count=product.product.price * 100)
        transaction.products.add(product)
        product.is_store = True
        product.save()
        last_transactions = Transaction.objects.filter(user=self.user, payment_type=restaurant.restaurantsettings.payment_type).all()
        if last_transactions:
            transaction.save()
            user_cards = Card.objects.filter(is_deleted=False, user=self.user).all()
            markup = types.InlineKeyboardMarkup(row_width=1)
            for user_card in user_cards:
                markup.add(types.InlineKeyboardButton(f'{user_card.card_number}', callback_data=f'choicecard_{restaurant.pk}_{user_card.pk}_{transaction.pk}'))
            markup.add(types.InlineKeyboardButton('Назад', callback_data=f'buyproduct_{restaurant.pk}_{product.pk}'))
            message_text = self.get_message_text('choice_card', 'Выберите карту для оплаты')
            self.bot.edit_message_text(chat_id=self.message.chat.id, text=message_text,
                                       message_id=self.message.message_id, reply_markup=markup)
            return self.user.step
        else:
            self.bot.edit_message_text(chat_id=self.message.chat.id, text=self.message.text + f"\n\nУ вас не найдено ни одной карты, выберите оплатить другой картой, чтобы она привязалась",
                                       message_id=self.message.message_id)
            return self.user.step

    def choice_card(self, restaurant_id, transaction_id, user_card_id):
        transaction = Transaction.objects.filter(pk=transaction_id).first()

        if transaction:
            try:
                restaurant = Restaurant.objects.get(pk=restaurant_id)
            except Restaurant.DoesNotExist:
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
                markup.add(types.KeyboardButton('Корзина'), types.KeyboardButton('Заведения'))
                markup.add(types.KeyboardButton('Скидки и бонусы'), types.KeyboardButton('Настройки'))
                self.bot.send_message(self.message.chat.id, 'Ресторан пропал, закажите в другом', reply_markup=markup)
                return 0
            owner = restaurant.telegram_bot.owner.pk
            payment_system = PaySystem(restaurant.restaurantsettings.payment_type, TinkoffPay, owner.ownersettings.terminal_key, owner.ownersettings.password)

            try:
                card = Card.objects.get(pk=user_card_id)
            except Card.DoesNotExist:
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
                markup.add(types.KeyboardButton('Корзина'), types.KeyboardButton('Заведения'))
                markup.add(types.KeyboardButton('Скидки и бонусы'), types.KeyboardButton('Настройки'))
                self.bot.send_message(self.message.chat.id, 'Карта пропала, привяжите ее по новой.', reply_markup=markup)
                return 0

            transaction = payment_system.do_pay(self.user, transaction, card)

            if transaction.payment_id:
                message_text = self.get_message_text('do_pay', 'Платеж выполняется').format(transaction.url)
                self.bot.send_message(self.message.chat.id, message_text)
            else:
                message_text = self.get_message_text('init_payment_fail', 'Произошла ошибка при созании платежа, обратитесь к администратору')
                self.bot.send_message(self.message.chat.id, message_text)
        else:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            markup.add(types.KeyboardButton('Корзина'), types.KeyboardButton('Заведения'))
            markup.add(types.KeyboardButton('Скидки и бонусы'), types.KeyboardButton('Настройки'))
            self.bot.send_message(self.message.chat.id, 'Такой транзакции уже нет, выберите товар заного', reply_markup=markup)
            return 0
        return self.user.step

    def pay_bonuses(self, restaurant_id, transaction_id, user_card_id):
        transaction = Transaction.objects.filter(pk=transaction_id).first()

        if transaction:
            try:
                restaurant = Restaurant.objects.get(pk=restaurant_id)
            except Restaurant.DoesNotExist:
                markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
                markup.add(types.KeyboardButton('Корзина'), types.KeyboardButton('Заведения'))
                markup.add(types.KeyboardButton('Скидки и бонусы'), types.KeyboardButton('Настройки'))
                self.bot.send_message(self.message.chat.id, 'Ресторан пропал, закажите в другом', reply_markup=markup)
                return 0
            payment_system = PaySystem(restaurant.restaurantsettings.payment_type, TinkoffPay)
            transaction.is_bonuses = True
            try:
                transaction = payment_system.init_pay(self.user, transaction)
            except NotEnoughBonuses:
                message_text = self.get_message_text('not_enough_bonuses', 'У вас недостаточно бонусов на счете, оплатите заказ картой')
                self.bot.edit_message_text(chat_id=self.message.chat.id, text=self.message.text + f'\n\n{message_text}',
                                           message_id=self.message.message_id)
                return self.user.step
            transaction.save()
            return self.user.step

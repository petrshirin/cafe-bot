from .models import *
from telebot import TeleBot, types
from geopy import distance as geopy_distance


class BotAction:

    def __init__(self, bot, message, user):
        self.bot = TeleBot('')  # bot
        self.message = message
        self.user = user

    @staticmethod
    def get_message_text(tag, message):
        message_to_send = TelegramMessage.objects.filter(tag=tag).first()
        if not message_to_send:
            return message
        else:
            return message_to_send.text

    def main_menu(self):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
        markup.add(types.KeyboardButton('Корзина'), types.KeyboardButton('Заведения'))
        markup.add(types.KeyboardButton('Скидки и бонусы'), types.KeyboardButton('Настройки'))
        message_text = self.get_message_text('main_menu', 'Главное меню')
        self.bot.send_message(self.message.chat.id, message_text, reply_markup=markup)

        return 1

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
            rest_distance = geopy_distance.vincenty((latitude, longitude), (rest_latitude, rest_longitude)).km
            distances.append(rest_distance)
        markup = types.InlineKeyboardMarkup(row_width=1)
        distances.sort()
        for i in range(0, 3):
            markup.add(types.InlineKeyboardButton(f'{restaurants[i].name} ({distances[i]}km)', callback_data=f'restaurant_{restaurants[i].pk}_0'))
        message_text = self.get_message_text('nearests_restaurants', 'Выберите один из ближайших ресторанов')
        self.bot.send_message(self.message.chat.id, message_text, reply_markup=markup)
        return 5

    def restaurant_category(self, restaurant_id, rest_category, deep):
        restaurant = Restaurant.objects.get(pk=restaurant_id)
        markup = types.InlineKeyboardMarkup(row_width=1)
        for category in rest_category['categories']:
            markup.add(types.InlineKeyboardButton(f'{category.name}', callback_data=f'category_{restaurant.pk}_{category["id"]}'))
        markup.add(types.InlineKeyboardButton(f'categoryback_{deep}'))
        message_text = self.get_message_text('category', 'Выберите категорию')
        self.bot.send_message(self.message.chat.id, message_text, reply_markup=markup)

        return self.user.status

    def restaurant_menu(self, restaurant_id, page, struct):
        restaurant = Restaurant.objects.get(pk=restaurant_id)
        menu = struct.product
        offset_menu = page * 5
        max_pages = len(menu) / 5 if (len(menu) % 5 == 0) else len(menu) / 5 + 1
        next_page = (page + 1) if (page + 1 <= max_pages) else 0
        previous_page = (page - 1) if (page - 1 >= 0) else max_pages - 1

        markup = types.InlineKeyboardMarkup(row_width=3)
        for i in range(offset_menu, offset_menu + 5):
            markup.add(types.InlineKeyboardButton(f'{menu[i].name} ({menu.price}₽)', callback_data=f'product_{restaurant.pk}_{menu.products[i].id}'))
        markup.add(types.InlineKeyboardButton(f'{previous_page + 1}/{max_pages}', callback_data=f'category_{restaurant.pk}_{menu.id}_{previous_page}'),
                   types.InlineKeyboardButton(f'Назад', callback_data=f'categoryback_'),
                   types.InlineKeyboardButton(f'{next_page + 1}/{max_pages}', callback_data=f'category_{restaurant.pk}_{menu.id}_{previous_page}'))
        message_text = self.get_message_text('restaurant', 'Выберите товар')
        self.bot.send_message(self.message.chat.id, message_text, reply_markup=markup)

        return self.user.status

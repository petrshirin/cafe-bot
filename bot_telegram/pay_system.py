import requests
from .models import *
from .exceptions import NotEnoughBonuses
from .pay_systems.Tinkoff import TinkoffPay
from django.conf import settings
from telebot import TeleBot, types


class PaySystem:

    def __init__(self, system_type, pay_system, terminal_key=None, password=None):
        self.type = system_type
        self.url = f'{settings.PAYMENT_URL}/{self.type}/'
        if self.type == 'Tinkoff':
            self.worker = pay_system(terminal_key, password, self.url)
        else:
            self.worker = None

    @staticmethod
    def calculate_sale(user, transaction):
        user_sales = UserSale.objects.filter(user=user, count__gte=1).all()
        for user_sale in user_sales:
            if not user_sale.sale.is_cash_back:
                transaction.count = transaction.count * (1-user_sale.sale.percent)
                user_sale.count -= 1
                if user_sale.count == 0:
                    user_sale.delete()
                else:
                    user_sale.save()
        transaction.save()

    def init_pay(self, user, transaction):
        self.calculate_sale(user, transaction)
        if transaction.is_bonuses:
            if user.bonus.count >= transaction.count / 100:
                user.bonus.count -= transaction.count / 100
                user.bonus.save()
                transaction.is_bonuses = True
                transaction.status = 2
                transaction.save()
                return transaction
            raise NotEnoughBonuses
        else:
            self.url += str(user.user_id)
            self.worker.URL = self.url
            response = self.worker.init_parent_pay(transaction.count, transaction.pk, "Cafe bot payment", user.user_id, user.telegramusersettings.email, transaction.products.all())

            if response:
                transaction.payment_id = response['PaymentId']
                transaction.status = 1
                transaction.url = response['PaymentURL']
                transaction.is_parent = True
            else:
                transaction.status = 3
            transaction.save()
            return transaction

    def do_pay(self, user, transaction, card):
        self.calculate_sale(user, transaction)
        if transaction.is_bonuses:
            if user.bonus.count * 100 >= transaction.count:
                user.bonus -= transaction.count
            raise NotEnoughBonuses
        else:

            response = self.worker.do_pay(card.rebill_id, transaction.count, transaction.pk, "Cafe bot payment", user.user_id, user.telegramusersettings.email)
            if response:
                transaction.card = card
                print(response)
                transaction.payment_id = response['PaymentId']
                transaction.status = 2
                transaction.save()
                bot = TeleBot(transaction.restaurant.telegram_bot.token)
                manager = transaction.restaurant.managers.filter(is_active=True, is_free=True).first()
                if not manager:
                    manager = transaction.restaurant.managers.filter(is_active=True).first()
                    if not manager:
                        bot.send_message(transaction.user.user_id, 'Оплата произведена, сейчас нет работающих менеджеров, '
                                                                   'Мы помним про ваш заказ, как только он освободится, вам придет оповещение')
                        transaction.status = 6

                message_text = f'Заказ №{transaction.pk}\n\n'
                message_text += f'{transaction.user.user_name} tel: {transaction.user.phone}\n\n'
                for product in transaction.products.all():
                    i = 1
                    message_text += f'{product.product.name} {product.product.volume}{product.product.unit}\n'
                    for addition in product.additions.all():
                        message_text += f'{i}. {addition.name}\n'
                        i += 1
                    message_text += '\n'
                markup = types.InlineKeyboardMarkup(row_width=1)
                markup.add(types.InlineKeyboardButton('Принять заказ', callback_data=f'acceptorder_{transaction.pk}'))
                bot.send_message(manager.user_id, message_text, reply_markup=markup)
                calculate_cash_back(transaction)
            else:
                transaction.card = card
                transaction.status = 3
            transaction.save()
            return transaction

    def get_user_cards(self, user):
        if self.worker:
            response = self.worker.get_user_card(user)
            if response:
                cards = []
                for response_card in response:
                    if response_card.get('RebillId'):
                        card = Card.objects.filter(rebill_id=response_card['RebillId']).first()
                        if response_card['Status'] == 'I':
                            self.delete_user_card(user, response_card['CardId'])
                            if card:
                                card.is_deleted = True
                                card.save()
                        if card and (response_card['CardType'] == 0 or response_card['CardType'] == 2):
                            if not card.card_number:
                                card.card_number = response_card['Pan']
                            cards.append(card)
                return cards
        return None

    def delete_user_card(self, user, card_id):
        if self.worker:
            self.worker.delete_card(user, card_id)
            return True
        return False



def calculate_cash_back(transaction):
    user = transaction.user
    user_cash_back_sale = UserSale.objects.filter(user=user, sale__is_cash_back=True).first()
    if user_cash_back_sale:
        user.bonus.count += transaction.count // 100 * user_cash_back_sale.sale.percent
        user.bonus.save()
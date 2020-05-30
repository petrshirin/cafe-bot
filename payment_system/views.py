from bot_telegram.models import Transaction, Card, UserSale
import json
import logging

from bot_telegram.models import Transaction, Card, UserSale
from django.http import HttpResponse
from telebot import TeleBot, types

# Create your views here.

LOG = logging.getLogger(__name__)


def get_payment_tinkoff(request, user_id=None):

    if user_id is None:
        LOG.error('invalid url to post')
        return HttpResponse('fail', status=400)

    if request.method == 'POST':
        try:
            data = json.loads(request.body, encoding='utf-8')
        except json.JSONDecodeError:
            LOG.error('error in parse json body')
            return HttpResponse('fail', status=400)

        LOG.debug(data)
        transaction = Transaction.objects.filter(payment_id=data['PaymentId'], user__user_id=int(user_id)).first()
        if transaction:

            if data.get('Status') == 'CONFIRMED':
                if transaction.status > 1:
                    return HttpResponse('OK', status=200)
                if data.get('RebillId'):
                    card = Card.objects.filter(card_number=data['Pan'], is_deleted=False, user=transaction.user).first()
                    if not card:
                        card = Card(user=transaction.user, rebill_id=data['RebillId'], card_number=data['Pan'])
                        card.save()
                    if not card.rebill_id:
                        card.rebill_id = str(data.get('RebillId'))
                    transaction.card = card
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
                        LOG.debug("OK 200")
                        return HttpResponse('OK', status=200)

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
                LOG.debug('OK 200')
                return HttpResponse("OK", status=200)

            elif data.get('Status') == 'PREAUTHORIZING':
                transaction.status = 1
                transaction.save()

            elif data.get('Status') == 'REJECTED' or data.get('Status') == 'CANCELED' or data.get('Status') == 'DEADLINE_EXPIRED':
                transaction.status = 3
                bot = TeleBot(transaction.restaurant.telegram_bot.token)
                bot.send_message(transaction.user.user_id, f'Заказ №{transaction.pk} отменен')
                transaction.save()
                LOG.debug('OK 200')
                return HttpResponse("OK", status=200)

        else:
            return HttpResponse('fail transaction', status=401)

    LOG.debug('OK 200')
    return HttpResponse("OK", status=200)


def calculate_cash_back(transaction):
    user = transaction.user
    user_cash_back_sale = UserSale.objects.filter(user=user, sale__is_cash_back=True).first()
    if user_cash_back_sale:
        user.bonus.count += transaction.count // 100 * user_cash_back_sale.sale.percent
        user.bonus.save()


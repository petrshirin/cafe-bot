from django.shortcuts import render
from bot_telegram.models import Transaction, Card, Owner, Restaurant
from django.http import HttpResponse
from bot_telegram.pay_system import PaySystem
from bot_telegram.pay_systems.Tinkoff import TinkoffPay
import json
import logging
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
                if data.get('RebillId'):
                    card = Card.objects.filter(card_number=data.get['Pan'], is_deleted=False).first()
                    if not card:
                        card = Card(user=transaction.user, rebill_id=data['RebillId'], card_number=data['Pan'])
                        card.save()
                    if not card.rebill_id:
                        card.rebill_id = str(data.get('RebillId'))
                    transaction.card = card
                    transaction.save()

            elif data.get('Status') == 'PREAUTHORIZING':
                transaction.status = 1
                transaction.save()

            elif data.get('Status') == 'REJECTED' or data.get('Status') == 'CANCELED' or data.get('Status') == 'DEADLINE_EXPIRED':
                transaction.status = 3
                transaction.save()

        else:
            return HttpResponse('fail transaction', status=401)

    return HttpResponse('ok', status=201)


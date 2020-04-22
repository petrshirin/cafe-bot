from django.shortcuts import render
from ..bot_telegram.models import Transaction, Card, Owner, Restaurant
from django.http import HttpResponse
from ..bot_telegram.pay_system import PaySystem
from ..bot_telegram.pay_systems.Tinkoff import TinkoffPay
# Create your views here.


def get_payment_tinkoff(request):

    if request.method == 'POST':
        data = request.data
        print(data)
        transaction = Transaction.objects.filter(payment_id=data['PaymentId']).first()
        if transaction:
            if data['Status'] == 'CONFIRMED':
                if not data['RebillID']:
                    owner = transaction.restaurant.telegram_bot.owner
                    pay_system = PaySystem('Tinkoff', TinkoffPay, owner.ownersettings.terminal_key, owner.ownersettings.password)
                    cards = pay_system.get_user_cards(transaction.user)
                    request_card = None
                    for card in cards:
                        if Card.objects.filter(card_number = card['Pan']).first():
                            continue
                        else:
                            request_card = card
                    if request_card and request_card['Status'] != 'I':
                        card = Card(user=transaction.user, rebill_id=data['RebillID'], card_number= request_card['Pan'])
                        card.save()

            elif data['Status'] == 'PREAUTHORIZING':
                transaction.status = 1
                transaction.save()

            elif data['Status'] == 'REJECTED' or data['Status'] == 'CANCELED' or data['Status'] == 'DEADLINE_EXPIRED':
                transaction.status = 3
                transaction.save()

        else:
            return HttpResponse('fail transaction', status=401)

    return HttpResponse('ok', status=201)


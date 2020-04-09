import requests
from hashlib import sha256
import logging


class TinkoffPay:

    def __init__(self, terminal_key, password, url):
        self.terminal_key = terminal_key
        self.password = password
        self.URL = url

    def init_parent_pay(self, amount, order_id, description, customer_key, email=None, products=None):
        body = {
            'TerminalKey': self.terminal_key,
            'Amount': amount,
            'OrderId': str(order_id),
            'Token': '',
            'Description': f'{description}',
            'Recurrent': 'Y',
            'CustomerKey': f'{customer_key}',
            'NotificationURL': self.URL
        }

        body = self.do_sign(body)

        if email and products:
            body['Receipt'] = {
                "Email": email,
                'Taxation': 'osn',
                'Items': [{
                    'Name': item.name,
                    'Quantity': 1,
                    'Amount': item.price * 100,
                    'Price': item.price * 100,
                    "Tax": 'none'
                } for item in products]
            }

        res = requests.post('https://securepay.tinkoff.ru/v2/Init', body=body)

        if res.ok:
            res = res.json()
            return res
        else:
            logging.error(res.json()['ErrorCode'], res.json()['Message'], res.json()['Details'])

    def do_pay(self, rebill_id, amount, order_id, description, customer_key, email=None, products=None):
        body = {
            'TerminalKey': self.terminal_key,
            'Amount': amount,
            'OrderId': str(order_id),
            'Token': '',
            'Description': f'{description}',
            'CustomerKey': f'{customer_key}',
            'NotificationURL': self.URL
        }

        body = self.do_sign(body)

        if email and products:
            body['Receipt'] = {
                "Email": email,
                'Taxation': 'osn',
                'Items': [{
                    'Name': item.name,
                    'Quantity': 1,
                    'Amount': item.price * 100,
                    'Price': item.price * 100,
                    "Tax": 'none'
                } for item in products]
            }

        res = requests.post('https://securepay.tinkoff.ru/v2/Init', body=body)

        if res.ok:
            res = res.json()
            body = {
                'TerminalKey': self.terminal_key,
                'PaymentId': res['PaymentId'],
                'RebillId': rebill_id,
                'Token': '',
            }
            if email:
                body['SendEmail'] = True
                body['InfoEmail'] = email
            body = self.do_sign(body)
            res = requests.post('https://securepay.tinkoff.ru/v2/Charge', body=body)

            if res.ok:
                res = res.json()
                return res
            else:
                logging.error(res.json()['ErrorCode'], res.json()['Message'], res.json()['Details'])
                return None

        else:
            logging.error(res.json()['ErrorCode'], res.json()['Message'], res.json()['Details'])
            return None

    def get_user_card(self, user):
        body = {
            'TerminalKey': self.terminal_key,
            'CustomerKey': f'{user.user_id}',
            'Token': ''
        }
        body = self.do_sign(body)

        res = requests.post('https://securepay.tinkoff.ru/v2/GetCardList', body=body)
        if res.ok:
            res = res.json()
            return res
        else:
            logging.error(res.json()['ErrorCode'], res.json()['Message'], res.json()['Details'])
            return None

    def delete_user_card(self, user, card_id):
        body = {
            'TerminalKey': self.terminal_key,
            'CustomerKey': f'{user.user_id}',
            'CardId': str(card_id),
            'Token': ''
        }
        body = self.do_sign(body)
        res = requests.post('https://securepay.tinkoff.ru/v2/GetCardList', body=body)

        if res.ok:
            res = res.json()
            return res
        else:
            logging.error(res.json()['ErrorCode'], res.json()['Message'], res.json()['Details'])
            return None

    def do_sign(self, body):
        body['password'] = self.password
        sorted_body = {}
        data_str = ''
        # сортировка
        list_keys = list(body.keys())
        list_keys.sort()
        for key in list_keys:
            sorted_body[key] = body[key]
        for item in sorted_body.values():
            data_str += str(item)

        sorted_body['Token'] = sha256(bytes(data_str, encoding='utf-8')).hexdigest()
        del sorted_body['password']
        return sorted_body





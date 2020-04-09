from abc import ABC

from django.core.management.base import LabelCommand
import telebot


class Command(LabelCommand):

    def handle(self, label, **options):
        try:
            telebot.TeleBot(label).set_webhook('https://mytesttelegrambotdev.ru/telegram_bot/webhook/label/')
            self.stdout.write('webhook installed')
        except Exception as err:
            self.stdout.write(err)


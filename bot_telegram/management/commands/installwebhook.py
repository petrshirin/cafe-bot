from django.core.management.base import LabelCommand
import telebot
from bot_telegram.models import TelegramBot


class Command(LabelCommand):

    def handle(self, label, host, **options):
        try:
            telebot.TeleBot(label).delete_webhook()
            bot = TelegramBot.objects.get(token=label)
            telebot.TeleBot(label).set_webhook(f'{host}/telegram_bot/webhook/{bot.token}')
            self.stdout.write('webhook installed')
        except Exception as err:
            self.stdout.write(err)


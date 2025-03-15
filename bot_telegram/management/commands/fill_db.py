from django.core.management.base import BaseCommand
from bot_telegram.models import *


class Command(BaseCommand):
    help = 'Fill db default value'

    struct = '''{
  "additions": [
    {
      "id": 1,
      "name": "Ваниль",
      "price": 20
    },
    {
      "id": 2,
      "name": "Карамель",
      "price": 20
    }
  ],
  "products": null,
  "id": 0,
  "categories": [
    {
      "id": 1,
      "name": "Еда и Десерты",
      "products": [
        {
              "id": 7,
              "name": "Десерт 2",
              "price": 1500,
              "description": "description1",
              "volume": "500",
              "unit": "мл",
              "cooking_time": "01:00:00",
              "additions": null
            }
      ],
      "categories": [
        {
          "id": 3,
          "name": "Комбо",
          "products": [
            {
              "id": 1,
              "name": "Комбо 1",
              "description": "description1",
              "volume": "500",
              "unit": "мл",
              "price": 500,
              "cooking_time": "01:00:00",
              "additions": null
            },
            {
              "id": 2,
              "name": "Комбо 1",
              "price": 1500,
              "description": "description1",
              "volume": "500",
              "unit": "мл",
              "cooking_time": "01:00:00",
              "additions": null
            }
          ]
        },
        {
          "id": 4,
          "name": "Еда",
          "products": [
            {
              "id": 3,
              "name": "Еда 1",
              "description": "description1",
              "volume": "500",
              "unit": "мл",
              "price": 200,
              "cooking_time": "00:30:00",
              "additions": null
            },
            {
              "id": 4,
              "name": "Комбо 1",
              "price": 400,
              "description": "description1",
              "volume": "500",
              "unit": "мл",
              "cooking_time": "00:20:00",
              "additions": null
            }
          ]
        },
        {
          "id": 5,
          "name": "Десерты",
          "products": [
            {
              "id": 5,
              "name": "Десерт 1",
              "price": 500,
              "description": "description1",
              "volume": "500",
              "unit": "мл",
              "cooking_time": "01:00:00",
              "additions": null
            },
            {
              "id": 6,
              "name": "Десерт 2",
              "price": 1500,
              "description": "description1",
              "volume": "500",
              "unit": "мл",
              "cooking_time": "01:00:00",
              "additions": null
            }
          ]
        }
        ]
    },
    {
      "id": 2,
      "name": "Еда и Десерты",
      "products": null,
      "categories": [
        {}
      ]
    }
  ]
}'''

    def handle(self, *args, **options):
        tg_bot = TelegramBot.objects.filter(pk=1).first()
        if not tg_bot:
            owner = Owner.objects.create(user=User.objects.get(pk=1), name='devOwner', FIO='devOwner', TIN="000")
            tg_bot = TelegramBot.objects.create(owner=owner, name='MyTestTelegramBotDev', token='904287379:AAFfP3aLUBJZ_xvUrP7jsed3CjSzsaAmIig')
        TelegramUserRole.objects.get_or_create(key=1, name='SimpleUser')
        TelegramUserRole.objects.get_or_create(key=2, name='Admin')
        rest = Restaurant.objects.get_or_create(name='dev_rest', telegram_bot=tg_bot, menu_struct=self.struct)
        RestaurantSettings.objects.get_or_create(restaurant=rest, address="Address", latitude=52.286108, longitude=104.276995)
        self.stdout.write('db filled')

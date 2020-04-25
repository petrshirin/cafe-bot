from django.contrib import admin
from .models import *
# Register your models here.

admin.site.register(Owner)
admin.site.register(OwnerSettings)
admin.site.register(TelegramBot)
admin.site.register(TelegramMessage)
admin.site.register(TelegramUser)
admin.site.register(TelegramUserRole)
admin.site.register(TelegramUserSettings)
admin.site.register(Restaurant)
admin.site.register(RestaurantSettings)
admin.site.register(RestaurantMenu)
admin.site.register(Addition)
admin.site.register(Card)
admin.site.register(Cheque)
admin.site.register(Sale)
admin.site.register(UserSale)
admin.site.register(Bonus)
admin.site.register(TelegramBasket)
admin.site.register(TelegramUserProduct)
admin.site.register(Transaction)



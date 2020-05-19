from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.fields import JSONField

from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver


class NonStrippingTextField(models.TextField):
    """A TextField that does not strip whitespace at the beginning/end of
    it's value.  Might be important for markup/code."""

    def formfield(self, **kwargs):
        kwargs['strip'] = False
        return super(NonStrippingTextField, self).formfield(**kwargs)


# Create your models here.


class Owner(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    FIO = models.CharField(max_length=255)
    TIN = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.pk} {self.name}"


class OwnerSettings(models.Model):
    user = models.OneToOneField(Owner, on_delete=models.CASCADE)
    terminal_key = models.CharField(max_length=150)
    password = models.CharField(max_length=150)


class TelegramBot(models.Model):
    name = models.CharField(max_length=255)
    token = models.CharField(max_length=100)
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE)
    public_offer = models.FileField(upload_to='public_offer/', default=None, blank=True, null=True)

    def __str__(self):
        return f"{self.pk} {self.name} {self.owner.name}"


class TelegramMessage(models.Model):
    tag = models.CharField(max_length=255)
    text = NonStrippingTextField()
    bot = models.ForeignKey(TelegramBot, on_delete=models.CASCADE, default=None, null=True)


class Addition(models.Model):
    name = models.CharField(max_length=255)
    price = models.IntegerField()

    def __str__(self):
        return f'{self.pk}. {self.name} ({self.price}руб.)'


class RestaurantMenu(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField()
    image = models.ImageField(upload_to='images/', default=None, null=True, blank=True)
    volume = models.IntegerField(default=1)
    unit = models.CharField(max_length=30)
    price = models.IntegerField()
    cooking_time = models.DurationField()
    additions = models.ManyToManyField(Addition, null=True, blank=True)

    def __str__(self):
        return f'{self.pk}. {self.name} {self.volume}{self.unit}. ({self.price}руб.)'


class RestaurantManager(models.Model):
    name = models.CharField(max_length=255)
    user_id = models.IntegerField()
    is_active = models.BooleanField(default=False)
    is_free = models.BooleanField(default=True)


class Restaurant(models.Model):
    name = models.CharField(max_length=255)
    telegram_bot = models.ForeignKey(TelegramBot, on_delete=models.CASCADE)
    menu_struct = JSONField()
    products = models.ManyToManyField(RestaurantMenu, default=None, null=True)
    managers = models.ManyToManyField(RestaurantManager, blank=True, default=None)

    class Meta:
        ordering = ['-pk']


class RestaurantSettings(models.Model):
    restaurant = models.OneToOneField(Restaurant, on_delete=models.CASCADE)
    address = models.CharField(max_length=255)
    payment_type = models.CharField(max_length=60, default='Tinkoff')
    latitude = models.FloatField()
    longitude = models.FloatField()
    time_opened = models.TimeField(default=None, null=True, blank=True)
    time_closed = models.TimeField(default=None, null=True, blank=True)


class TelegramUserRole(models.Model):
    key = models.IntegerField(default=1)
    name = models.CharField(max_length=255)


class TelegramUser(models.Model):
    user_id = models.IntegerField()
    telegram_bot = models.ForeignKey(TelegramBot, on_delete=models.CASCADE)
    role = models.ForeignKey(TelegramUserRole, on_delete=models.CASCADE)
    step = models.IntegerField(default=0)
    user_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, default=None, blank=True, null=True)


class TelegramUserProduct(models.Model):
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE)
    product = models.ForeignKey(RestaurantMenu, on_delete=models.CASCADE)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, default=None, null=True, blank=True)
    additions = models.ManyToManyField(Addition, null=True, blank=True)
    is_basket = models.BooleanField(default=False)
    is_store = models.BooleanField(default=False)


class TelegramBasket(models.Model):
    user = models.OneToOneField(TelegramUser, on_delete=models.CASCADE)
    products = models.ManyToManyField(TelegramUserProduct)


class Card(models.Model):
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE)
    card_number = models.CharField(max_length=25, default=None, null=True, blank=True)
    rebill_id = models.CharField(max_length=60, default=None, null=True, blank=True)
    is_deleted = models.BooleanField(default=False)


class TelegramUserSettings(models.Model):
    user = models.OneToOneField(TelegramUser, on_delete=models.CASCADE)
    language = models.CharField(max_length=5)
    email = models.EmailField()


class Bonus(models.Model):
    user = models.OneToOneField(TelegramUser, on_delete=models.CASCADE)
    count = models.IntegerField(default=0)


class Sale(models.Model):
    name = models.CharField(max_length=255)
    bot = models.ForeignKey(TelegramBot, on_delete=models.CASCADE)
    description = NonStrippingTextField(default="Обычная скидка")
    count_transaction = models.IntegerField(default=999999)
    base_sale = models.BooleanField()
    is_cash_back = models.BooleanField()
    percent = models.FloatField(default=0.1)
    is_active = models.BooleanField(default=True)


class UserSale(models.Model):
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE)
    sale = models.ForeignKey(Sale, models.CASCADE)
    count = models.IntegerField(default=999999)


class Transaction(models.Model):
    """
    0 - created pay
    1 - processing pay
    2 - confirmed pay
    3 - canceled
    4 - in queue
    5 - confirmed order
    6 - non reserved order
    """
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE)
    card = models.ForeignKey(Card, on_delete=models.CASCADE, default=None, blank=True, null=True)
    products = models.ManyToManyField(TelegramUserProduct)
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    payment_id = models.IntegerField(default=None, null=True, blank=True)
    is_parent = models.BooleanField(default=False)
    count = models.IntegerField(default=0)
    is_bonuses = models.BooleanField(default=False)
    status = models.IntegerField(default=0)
    url = models.URLField(default=None, null=True, blank=True)


class Cheque(models.Model):
    transaction = models.ForeignKey(Transaction, on_delete=models.CASCADE)
    name = models.CharField
    date = models.DateTimeField(auto_now=True)
    email = models.EmailField()


@receiver(post_save, sender=TelegramUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        TelegramUserSettings.objects.create(user=instance)
        TelegramBasket.objects.create(user=instance)
        Bonus.objects.create(user=instance, count=0)
        sales = Sale.objects.filter(base_sale=True, bot=instance.telegram_bot, is_active=True).all()
        for sale in sales:
            UserSale.objects.create(user=instance, sale=sale, count=sale.count_transaction)


@receiver(post_save, sender=TelegramUser)
def save_user_profile(sender, instance, **kwargs):
    instance.telegramusersettings.save()
    instance.telegrambasket.save()


@receiver(post_save, sender=Owner)
def create_owner_settings(sender, instance, created, **kwargs):
    if created:
        OwnerSettings.objects.create(user=instance)


@receiver(post_save, sender=Owner)
def save_owner_settings(sender, instance, **kwargs):
    instance.ownersettings.save()


@receiver(post_save, sender=Sale)
def control_user_sales(sender, instance, created, **kwargs):
    if created:
        users = TelegramUser.objects.filter(telegram_bot=instance.bot).all()
        if instance.base_sale and instance.is_active:
            for user in users:
                user_sale = UserSale.objects.filter(user=user, sale=instance).first()
                if not user_sale:
                    user_sale = UserSale(user=user, sale=instance, count=instance.count_transaction)
                    user_sale.save()
        if not instance.is_active:
            for user in users:
                user_sale = UserSale.objects.filter(user=user, sale=instance).first()
                if user_sale:
                    user_sale.delete()



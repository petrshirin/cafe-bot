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


class TelegramBot(models.Model):
    name = models.CharField(max_length=255)
    token = models.CharField(max_length=100)
    owner = models.ForeignKey(Owner, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.pk} {self.name} {self.owner.name}"


class TelegramMessage(models.Model):
    tag = models.CharField(max_length=255)
    text = NonStrippingTextField()


class Addition(models.Model):
    name = models.CharField(max_length=255)
    price = models.IntegerField()


class RestaurantMenu(models.Model):
    product = models.CharField(max_length=255)
    price = models.IntegerField()
    cooking_time = models.DurationField()
    additions = models.ManyToManyField(Addition)


class Restaurant(models.Model):
    name = models.CharField(max_length=255)
    telegram_bot = models.ForeignKey(TelegramBot, on_delete=models.CASCADE)
    menu_struct = JSONField()
    # products = models.ManyToManyField(RestaurantMenu, default=None, null=True)


class RestaurantSettings(models.Model):
    restaurant = models.OneToOneField(Restaurant, on_delete=models.CASCADE)
    address = models.CharField(max_length=255)
    latitude = models.FloatField()
    longitude = models.FloatField()


class TelegramUserRole(models.Model):
    name = models.CharField(max_length=255)


class TelegramUser(models.Model):
    user_id = models.IntegerField()
    telegram_bot = models.ForeignKey(TelegramBot, on_delete=models.CASCADE)
    role = models.ForeignKey(TelegramUserRole, on_delete=models.CASCADE)
    step = models.IntegerField(default=0)
    user_name = models.CharField(max_length=255)


class Card(models.Model):
    card_number = models.CharField(max_length=20)


class Cheque(models.Model):
    name = models.CharField
    date = models.DateTimeField(auto_now=True)
    email = models.EmailField()


class TelegramUserSettings(models.Model):
    user = models.OneToOneField(TelegramUser, on_delete=models.CASCADE)
    language = models.CharField(max_length=5)
    cards = models.ManyToManyField(Card)
    email = models.EmailField()
    cheque = models.ManyToManyField(Cheque)


class Transaction(models.Model):
    user = models.OneToOneField(TelegramUser, on_delete=models.CASCADE)
    status = models.CharField(max_length=255)
    hash = models.CharField(max_length=255)


@receiver(post_save, sender=TelegramUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        TelegramUserSettings.objects.create(user=instance)
        Transaction.objects.create(user=instance)


@receiver(post_save, sender=TelegramUser)
def save_user_profile(sender, instance, **kwargs):
    instance.telegramusersettings.save()
    instance.transaction.save()




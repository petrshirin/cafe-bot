import json


class MenuAddition:

    def __init__(self, addition, previous_id):
        self.id = addition['id']
        self.name = addition['name']
        self.price = addition['price']
        self.previous_id = previous_id


class MenuProduct:

    def __init__(self, product, previous_id):
        self.id = product['id']
        self.name = product['name']
        self.product = []
        self.previous_id = previous_id
        self.price = product['price']
        self.volume = product['volume']
        self.unit = product['unit']
        self.time_cooking = product['time_cooking']
        self.additions = self.parse_additions(product)

    def parse_additions(self, product):
        additions = []
        if product['additions']:
            for addition in product['additions']:
                additions.append(MenuAddition(addition, self.id))
        return additions


class MenuStruct:

    def __str__(self):
        return f'{self.id}. {self.type} {self.name}'

    def __init__(self, menu, previous_id):
        self.menu = menu
        if type(self.menu) == str:
            self.menu = json.loads(self.menu)
        self.type = None
        self.name = self.menu.get('name', None)
        self.previous_id = previous_id
        self.id = self.menu.get('id', None)
        self.categories = []
        self.products = []
        self.create_struct()
        self.all_products = []

    def create_struct(self):

        if self.menu.get('products') and self.menu.get('categories'):
            self.type = 'categories'
            self.products = []
            for product in self.menu['products']:
                self.products.append(MenuProduct(product, self.id))
            self.categories = []
            for category in self.menu['categories']:
                self.categories.append(MenuStruct(category, self.id))
        elif self.menu.get('products'):
            self.type = 'products'
            self.products = []
            for product in self.menu['products']:
                self.products.append(MenuProduct(product, self.id))
        elif self.menu.get('categories'):
            self.type = 'categories'
            for category in self.menu['categories']:
                self.categories.append(MenuStruct(category, self.id))

    def get_category(self, category_id):
        for category in self.categories:
            if category.id == category_id:
                return category
        for category in self.categories:
            category = category.get_category( category_id)
            if category:
                return category

    def get_product(self, product_id):
        for product in self.products:
            if product.id == product_id:
                return product
        for category in self.categories:
            for product in category.products:
                if product.id == product_id:
                    return product
        for category in self.categories:
            return category.get_product(product_id)


if __name__ == '__main__':
    f = open('C:/Users/Admin/WorkFreelance/CafeBot/cafebot/bot_telegram/pay_systems/menu.json', 'r', encoding='utf-8')
    m = MenuStruct(json.loads(f.read()), -1)
    print(m.get_category(18))

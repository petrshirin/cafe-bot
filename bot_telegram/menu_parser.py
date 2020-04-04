

class MenuAddition:

    def __init__(self, addition):
        self.id = addition['id']
        self.name = addition['name']
        self.price = addition['price']


class MenuProduct:

    def __init__(self, product):
        self.id = product['id']
        self.name = product['name']
        self.product = []
        self.price = product['price']
        self.time_cooking = product['time_cooking']
        self.additions = self.parse_additions(product)

    @staticmethod
    def parse_additions(product):
        additions = []
        if product['additions']:
            for addition in product['additions']:
                additions.append(MenuAddition(addition))
        return additions


class MenuStruct:

    def __init__(self, menu, deep):
        self.menu = menu
        self.type = None
        self.deep = deep
        self.name = self.menu.get('name', None)
        self.id = self.menu.get('id', None)
        self.categories = []
        self.products = []
        self.create_struct()
        self.all_products = []

    def create_struct(self):
        if self.menu.get('products'):
            self.type = 'products'
            self.products = []
            for product in self.menu['products']:
                self.products.append(MenuProduct(product))
        elif self.menu.get('categories'):
            self.type = 'categories'
            for category in self.menu['categories']:
                self.categories.append(MenuStruct(category, self.deep + 1))

    def get_category(self, category_id):
        for category in self.categories:
            if category.id == category_id:
                return category
        for category in self.categories:
            return category.get_category(category_id)

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
      "products": null,
      "categories": [
        {
          "id": 3,
          "name": "Комбо",
          "products": [
            {
              "id": 1,
              "name": "Комбо 1",
              "price": 500,
              "time_cooking": "01:00:00",
              "additions": null
            },
            {
              "id": 2,
              "name": "Комбо 1",
              "price": 1500,
              "time_cooking": "01:00:00",
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
              "price": 200,
              "time_cooking": "00:30:00",
              "additions": null
            },
            {
              "id": 4,
              "name": "Комбо 1",
              "price": 400,
              "time_cooking": "00:20:00",
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
              "time_cooking": "01:00:00",
              "additions": null
            },
            {
              "id": 6,
              "name": "Десерт 2",
              "price": 1500,
              "time_cooking": "01:00:00",
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


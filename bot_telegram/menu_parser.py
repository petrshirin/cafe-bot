import json
from typing import List, Union, Dict


class BaseStruct:

    def __init__(self, struct: Union[str, Dict], previous_id: int):
        self.categories: List[BaseStruct] = []
        self.products: List[BaseStruct] = []
        self.all_additions: List[BaseStruct] = []
        self.type = 'categories'
        self.struct = struct or {}
        if type(self.struct) == str:
            self.struct = json.loads(self.struct)
        self.struct_key: int = self.struct.get('id')
        self.previous_id: int = previous_id

    def get_data(self):
        return self.struct


class MenuAddition(BaseStruct):

    def __init__(self, struct: Dict, previous_id: int):
        super().__init__(struct, previous_id)
        self.name: str = self.struct.get('name')
        self.price: float = self.struct.get('price')


class MenuProduct(BaseStruct):

    def __init__(self, struct: Dict, previous_id: int):
        super().__init__(struct, previous_id)
        self.name: str = self.struct.get('name')
        self.price: float = self.struct.get('price')
        self.volume: str = self.struct.get('volume')
        self.unit: str = self.struct.get('unit')
        self.cooking_time: str = self.struct.get('cooking_time')
        self.description: str = self.struct.get('description')
        self.additions: List[MenuAddition] = self.parse_additions(self.struct)

    def get_addition_data(self, addition_id):
        for addition in self.all_additions:
            if addition.struct_key == addition_id:
                return addition.get_data()

    def parse_additions(self, product) -> List[MenuAddition]:
        additions = []
        if product.get('additions'):
            for addition_id in product['additions']:
                additions.append(MenuAddition(self.get_addition_data(addition_id), self.struct_key))
        return additions


class MenuStruct(BaseStruct):

    def __str__(self):
        return f'{self.struct_key}. {self.type} {self.name}'

    def __init__(self, struct: Union[str, Dict], previous_id: int):
        super().__init__(struct, previous_id)
        self.name: str = self.struct.get('name', None)
        self.previous_id: int = previous_id
        self.categories: List[MenuStruct] = []
        self.products: List[MenuProduct] = []
        self.create_struct()

    def create_struct(self):
        if self.previous_id == -1:
            for addition in self.struct['additions']:
                self.all_additions.append(MenuAddition(addition, self.struct_key))

        if self.struct.get('products'):
            self.type = 'products'
            self.products = []
            for product in self.struct['products']:
                self.products.append(MenuProduct(product, self.struct_key))
        if self.struct.get('categories'):
            self.type = 'categories'
            for category in self.struct['categories']:
                self.categories.append(MenuStruct(category, self.struct_key))

    def get_category(self, category_id):
        for category in self.categories:
            if category.struct_key == category_id:
                return category
        for category in self.categories:
            category = category.get_category(category_id)
            if category:
                return category

    def get_product(self, product_id):
        for product in self.products:
            if product.struct_key == product_id:
                return product
        for category in self.categories:
            for product in category.products:
                if product.struct_key == product_id:
                    return product
        for category in self.categories:
            product = category.get_product(product_id)
            if product:
                return product

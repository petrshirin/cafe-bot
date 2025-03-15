
def calculate_max_pages(menu):
    if (len(menu.products) + len(menu.categories)) % 5 == 0:
        return int((len(menu.products) + len(menu.categories)) / 5)
    else:
        return int((len(menu.products) + len(menu.categories)) / 5 + 1)

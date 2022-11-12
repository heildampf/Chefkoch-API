import re
import json
import requests as rq
from bs4 import BeautifulSoup
import lxml
import cchardet

class Category:
    id_pattern = re.compile("(/rs/s0)(g\d*)")

    def __init__(self, title, url=None, id=None):
        self.title = title.replace("&", "")
        if url is not None:
            self.id = Category.id_pattern.search(url).group(2)
        if id is not None:
            self.id = id

    def __str__(self):
        return json.dumps(self.__dict__, ensure_ascii=False)


class Ingredient:
    def __init__(self, name, amount):
        self.name = name
        self.amount = amount

    def __str__(self):
        return json.dumps(self.__dict__, ensure_ascii=False)


class Recipe:
    def __init__(self, name, id, category, ingredients, text, instructions, tags, kcal, rating, ratings_amount, recipe_url, images):
        self.name = name
        self.id = id
        self.category = category
        self.ingredients = ingredients
        self.text = text
        self.instructions = instructions
        self.tags = tags
        self.kcal = kcal
        self.rating = rating
        self.ratings_amount = ratings_amount
        self.recipe_url = recipe_url
        self.images = images

    """ @staticmethod
    def from_json(json_obj):
        name = json_obj['name']
        id = json_obj['id']
        category = Category(json_obj['category']['title'], id=json_obj['category']['id'])
        ingredients = [Ingredient(ingredient['name'], ingredient['amount']) for ingredient in json_obj['ingredients']]
        return Recipe(name, id, category, ingredients) """

    def __str__(self):
        return json.dumps({
            "name": self.name,
            "id": self.id,
            "category": self.category.__dict__,
            "ingredients": [ingredient.__dict__ for ingredient in self.ingredients]
             }, ensure_ascii=False)


class ChefKochAPI:
    base_url = "https://www.chefkoch.de/"

    @staticmethod
    def get_categories():
        response = rq.get(ChefKochAPI.base_url + "rezepte/kategorien/")
        soup = BeautifulSoup(response.text, 'lxml')

        categories = []
        for category_column in soup.findAll("div", {"class": "category-column"}):
            for category_container in category_column.findChildren():
                category = category_container.find('a', href=True)
                try:
                    title = category.string
                    url = category["href"]
                except Exception:
                    continue
                categories.append(Category(title, url=url))

        return categories

    @staticmethod
    def parse_recipes(category, end_index=0, start_index=0):
        page_index = 0
        recipe_index = 0
        recipe_amount = None
        requests_session = rq.Session()
        # index = start_index
        while True:
            # Actual part before .html is irrelevant, but site wont serve any results if missing
            response = requests_session.get(ChefKochAPI.base_url + 'rs/' + 's' + str(page_index) + category.id + '/recipes.html')
            if response.status_code == 404:
                return
            soup = BeautifulSoup(response.text, 'lxml')
            if recipe_amount is None:
                recipe_amount_string = soup.find_all("span", {"class": "ds-text-category"})[0]
                recipe_amount = int(recipe_amount_string.get_text().strip().split(" ")[0].replace(".", ""))
                print("Crawling " + category.title + " with " + str(recipe_amount) + " recipes.")
            page_index += 1
            for recipe_list_item in soup.find_all("a", {"class": "ds-teaser-link"}):

                recipe_id = recipe_list_item['href'].replace("https://www.chefkoch.de/rezepte/", "")
                recipe_id = recipe_id[0: recipe_id.index('/')]
                recipe_url = recipe_list_item['href']
                recipe_response = requests_session.get(recipe_url)

                if recipe_response.status_code != 200:
                    continue

                recipe_soup = BeautifulSoup(recipe_response.text, 'lxml')
                if hasattr(recipe_soup.find("h1"), 'contents'):
                    recipe_name = recipe_soup.find("h1").contents[0]
                    # print(category.title + ": " + recipe_name)
                    ingredients_tables = recipe_soup.find_all("table", {"class": "ingredients"})
                    recipe_ingredients = []
                    for ingredients_table in ingredients_tables:
                        ingredients_table_body = ingredients_table.find("tbody")
                        for row in ingredients_table_body.find_all('tr'):
                            cols = row.find_all('td')
                            recipe_ingredients.append(
                                Ingredient(re.sub(' +', ' ', cols[1].text.strip().replace(u"\u00A0", " ")),
                                        re.sub(' +', ' ', cols[0].text.strip().replace(u"\u00A0", " "))))
                            
                    print(str(recipe_index) + " - ", sep=' ', end='', flush=True)
                    
                    yield Recipe(recipe_name.replace(u"\u00A0", " "), recipe_id.replace(u"\u00A0", " "),
                                category, recipe_ingredients, recipe_url)
                    
                if recipe_index >= recipe_amount -10:
                    print(str(recipe_index) + " recipes in category " +  category.title + " crawled!")
                    return
                
                recipe_index += 1
                """ if 0 < end_index < index:
                    return """


class DataParser:

    @staticmethod
    def write_recipes_to_json(file_path, recipes, ):
        with open(file_path + ".json", "w") as txt_file:
            txt_file.write("[")
            for recipe in recipes:
                try:
                    txt_file.write(str(recipe))
                    txt_file.write(",")
                except Exception:
                    pass
            txt_file.write("{}]")

    @staticmethod
    def load_recipes_from_json(file_path):
        raw_text = ""
        with open(file_path) as file:
            raw_text = file.read()

        recipes = []
        for obj in json.loads(raw_text):
            if len(obj.keys()) > 0:
                recipes.append(Recipe.from_json(obj))
        return recipes

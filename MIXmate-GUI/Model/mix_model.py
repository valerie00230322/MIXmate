
class MixModel:

    def get_ingredients_for_cocktail(self, cocktail_id):
        self.cursor.execute("""
            SELECT ingredient_id, amount_ml, order_index
            FROM cocktail_ingredients
            WHERE cocktail_id = ?
            ORDER BY order_index ASC
        """, (cocktail_id,))
        return self.cursor.fetchall()

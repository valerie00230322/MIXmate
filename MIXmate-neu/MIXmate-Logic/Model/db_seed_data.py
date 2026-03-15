SEED_INGREDIENTS = [
    {"ingredient_id": 1, "name": "Rum"},
    {"ingredient_id": 2, "name": "Cola"},
    {"ingredient_id": 3, "name": "Weisswein"},
    {"ingredient_id": 4, "name": "Holundersirup"},
    {"ingredient_id": 5, "name": "Limettensaft"},
    {"ingredient_id": 6, "name": "Tonic"},
    {"ingredient_id": 7, "name": "Gin"},
    {"ingredient_id": 8, "name": "Orangensaft"},
    {"ingredient_id": 9, "name": "Vodka"},
]

SEED_COCKTAILS = [
    {"cocktail_id": 1, "cocktail_name": "RumCola"},
    {"cocktail_id": 2, "cocktail_name": "Hugo"},
    {"cocktail_id": 3, "cocktail_name": "GinTonic"},
    {"cocktail_id": 4, "cocktail_name": "Vodka-Orange"},
    {"cocktail_id": 5, "cocktail_name": "Test"},
]

SEED_COCKTAIL_INGREDIENTS = [
    {"cocktail_id": 1, "ingredient_id": 1, "amount_ml": 50.0, "order_index": 1},
    {"cocktail_id": 1, "ingredient_id": 2, "amount_ml": 150.0, "order_index": 2},
    {"cocktail_id": 2, "ingredient_id": 3, "amount_ml": 80.0, "order_index": 1},
    {"cocktail_id": 2, "ingredient_id": 4, "amount_ml": 20.0, "order_index": 2},
    {"cocktail_id": 2, "ingredient_id": 5, "amount_ml": 10.0, "order_index": 3},
    {"cocktail_id": 3, "ingredient_id": 7, "amount_ml": 40.0, "order_index": 1},
    {"cocktail_id": 3, "ingredient_id": 6, "amount_ml": 120.0, "order_index": 2},
    {"cocktail_id": 4, "ingredient_id": 9, "amount_ml": 60.0, "order_index": 1},
    {"cocktail_id": 4, "ingredient_id": 8, "amount_ml": 120.0, "order_index": 2},
]

SEED_PUMPS = [
    {"pump_id": 1, "pump_number": 1, "ingredient_id": 1, "flow_rate_ml_s": 10.0, "position_steps": 660},
    {"pump_id": 2, "pump_number": 2, "ingredient_id": 2, "flow_rate_ml_s": 12.0, "position_steps": 580},
    {"pump_id": 3, "pump_number": 3, "ingredient_id": 3, "flow_rate_ml_s": 11.5, "position_steps": 580},
    {"pump_id": 4, "pump_number": 4, "ingredient_id": 4, "flow_rate_ml_s": 8.0, "position_steps": 700},
    {"pump_id": 5, "pump_number": 5, "ingredient_id": 5, "flow_rate_ml_s": 5.0, "position_steps": 900},
    {"pump_id": 6, "pump_number": 6, "ingredient_id": 6, "flow_rate_ml_s": 13.0, "position_steps": 1100},
]

SEED_LEVELS = [
    {"levelnumber": 1, "extension_distance": 50.0},
    {"levelnumber": 2, "extension_distance": 90.0},
]

SEED_MACHINE_PARAMETERS = [
    {"param_key": "cocktail_source_level_1", "param_value": 1.0},
    {"param_key": "mixer_height_mm", "param_value": 10.0},
    {"param_key": "mixer_ausschub_distance_mm", "param_value": 0.0},
    {"param_key": "mixer_direction_left", "param_value": 1.0},
    {"param_key": "load_unload_position_mm", "param_value": 0.0},
    {"param_key": "homing_safe_height_mm", "param_value": 0.0},
]

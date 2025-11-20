import json
import os

class Persistence:
    def __init__(self, filepath='savegame.json'):
        self.filepath = filepath

    def save_game(self, game):
        data = {
            'money': game.yukkurrium.money,
            'yukkuris': [],
            'items': []
        }

        for y in game.yukkurrium.yukkuris:
            data['yukkuris'].append({
                'type': y.type_name,
                'stats': y.stats,
                'position': y.position
            })

        for i in game.yukkurrium.items:
            data['items'].append({
                'type_key': i.type_key,
                'position': i.position
            })

        try:
            with open(self.filepath, 'w') as f:
                json.dump(data, f, indent=4)
            print("Game Saved.")
        except Exception as e:
            print(f"Failed to save: {e}")

    def load_game(self, game):
        if not os.path.exists(self.filepath):
            print("No save file found.")
            return

        try:
            with open(self.filepath, 'r') as f:
                data = json.load(f)

            game.yukkurrium.money = data.get('money', 1000)
            game.yukkurrium.yukkuris = []
            game.yukkurrium.items = []

            for y_data in data.get('yukkuris', []):
                # We need to spawn then override stats
                new_y = game.yukkurrium.spawn_yukkuri(y_data['type'], y_data['position'][0], y_data['position'][1])
                if new_y:
                    new_y.stats = y_data['stats']

            for i_data in data.get('items', []):
                key = i_data.get('type_key')
                # Use force_place_item to avoid cost deduction
                game.yukkurrium.force_place_item(key, i_data['position'][0], i_data['position'][1])

            # Ensure money is correct (though force_place doesn't touch it, good to set it explicitly)
            game.yukkurrium.money = data.get('money', 1000)

            print("Game Loaded.")
        except Exception as e:
            print(f"Failed to load: {e}")

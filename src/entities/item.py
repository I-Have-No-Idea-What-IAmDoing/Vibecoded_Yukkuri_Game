import uuid

class Item:
    def __init__(self, type_key, type_data, x, y):
        self.id = str(uuid.uuid4())
        self.type_key = type_key # Store the key used to create this item (e.g., "BeanPaste")
        self.name = type_data.get('name', 'Unknown')
        self.type = type_data.get('type', 'misc')
        self.data = type_data # Store raw data for interactions (nutrition, etc)
        self.color = type_data.get('color', [128, 128, 128])
        self.position = [x, y]
        self.width = 20
        self.height = 20

    def get_rect(self):
        return (self.position[0], self.position[1], self.width, self.height)

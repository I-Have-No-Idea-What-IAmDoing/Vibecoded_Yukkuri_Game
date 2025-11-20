import yaml
import os
import logging

logger = logging.getLogger(__name__)

class DataLoader:
    def __init__(self, data_dir='data'):
        self.data_dir = data_dir
        self.yukkuri_types = {}
        self.items = {}
        self.ai_actions = {}

    def load_all(self):
        self.yukkuri_types = self.load_yaml('yukkuri_types.yaml')
        self.items = self.load_yaml('items.yaml')
        self.ai_actions = self.load_yaml('ai_actions.yaml')
        logger.info("All data loaded successfully.")

    def load_yaml(self, filename):
        filepath = os.path.join(self.data_dir, filename)
        if not os.path.exists(filepath):
            logger.error(f"File not found: {filepath}")
            return {}

        try:
            with open(filepath, 'r') as f:
                data = yaml.safe_load(f)
                if data is None:
                    return {}
                return data
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file {filename}: {e}")
            return {}

    def get_yukkuri_type(self, name):
        return self.yukkuri_types.get(name)

    def get_item_type(self, name):
        return self.items.get(name)

    def get_action(self, name):
        return self.ai_actions.get(name)

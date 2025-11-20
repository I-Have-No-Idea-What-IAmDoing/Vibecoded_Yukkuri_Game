import toml
import yaml
import os

def load_config(file_path):
    """Loads a configuration file, supporting both TOML and YAML."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Configuration file not found: {file_path}")

    _, extension = os.path.splitext(file_path)
    try:
        with open(file_path, "r") as f:
            if extension == ".toml":
                return toml.load(f)
            elif extension in [".yaml", ".yml"]:
                return yaml.safe_load(f)
            else:
                raise ValueError(f"Unsupported config file format: {extension}")
    except (toml.TomlDecodeError, yaml.YAMLError, ValueError) as e:
        print(f"Error loading configuration file {file_path}: {e}")
        return None

def validate_yukkuri_type(data):
    """Validates the structure of a Yukkuri type definition."""
    required_keys = ["name", "base_health", "base_happiness"]
    for key in required_keys:
        if key not in data:
            raise ValueError(f"Missing required key in yukkuri type: {key}")
    return True

def validate_item_type(data):
    """Validates the structure of an item type definition."""
    required_keys = ["name", "type", "value"]
    for key in required_keys:
        if key not in data:
            raise ValueError(f"Missing required key in item type: {key}")
    return True

def load_yukkuri_types(file_path="data/yukkuri_types.toml"):
    """Loads and validates all Yukkuri type definitions."""
    types_data = load_config(file_path)
    if types_data:
        for name, data in types_data.items():
            validate_yukkuri_type(data)
    return types_data

def load_item_types(file_path="data/item_types.toml"):
    """Loads and validates all item type definitions."""
    types_data = load_config(file_path)
    if types_data:
        for name, data in types_data.items():
            validate_item_type(data)
    return types_data

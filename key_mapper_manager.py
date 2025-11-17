import json
import os

class KeyMapperManager:
    def __init__(self, mapping_file='key_mapping.json'):
        self.mapping_file = mapping_file
        self.mappings = {}
        self.load_mappings()

    def load_mappings(self):
        """Loads key override mappings from the JSON file."""
        if os.path.exists(self.mapping_file):
            try:
                with open(self.mapping_file, 'r', encoding='utf-8') as f:
                    self.mappings = json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading mapping file: {e}")
                self.mappings = {}
        else:
            self.mappings = {}

    def save_mappings(self):
        """Saves the current key mappings to the JSON file."""
        try:
            with open(self.mapping_file, 'w', encoding='utf-8') as f:
                json.dump(self.mappings, f, indent=4, ensure_ascii=False)
        except IOError as e:
            print(f"Error saving mapping file: {e}")

    def get_override(self, detected_key_info):
        """Gets the override target name for a given detected key."""
        return self.mappings.get(detected_key_info)

    def add_or_update_mapping(self, detected_key_info, target_name):
        """Adds or updates a mapping."""
        self.mappings[detected_key_info] = target_name

    def remove_mapping(self, detected_key_info):
        """Removes a mapping."""
        if detected_key_info in self.mappings:
            del self.mappings[detected_key_info]

    def get_all_mappings(self):
        """Returns all mappings as a dictionary."""
        return self.mappings

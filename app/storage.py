import json
import os
import numpy as np

class UserManager:
    def __init__(self, db_file="users.json"):
        self.db_file = db_file
        self.users = self.load_users()

    def load_users(self):
        if not os.path.exists(self.db_file):
            return {}
        try:
            with open(self.db_file, 'r') as f:
                data = json.load(f)
                # Convert lists back to numpy arrays for encodings
                for user in data:
                    if 'encoding' in data[user]:
                        data[user]['encoding'] = np.array(data[user]['encoding'])
                return data
        except:
            return {}

    def save_users(self):
        data_to_save = {}
        for user, info in self.users.items():
            info_copy = info.copy()
            if 'encoding' in info_copy:
                info_copy['encoding'] = info_copy['encoding'].tolist()
            data_to_save[user] = info_copy
            
        with open(self.db_file, 'w') as f:
            json.dump(data_to_save, f)

    def register_user(self, name, encoding, gesture="Fist"):
        # We allow re-registering to update gestures or just check before calling
        if name in self.users:
            return False # Already exists
        self.users[name] = {
            "encoding": encoding,
            "gestures": [gesture]
        }
        self.save_users()
        return True

    def add_gesture(self, name, gesture):
        if name in self.users:
            if gesture not in self.users[name]['gestures']:
                self.users[name]['gestures'].append(gesture)
                self.save_users()
            return True
        return False
        
    def get_known_encodings(self):
        encodings = []
        names = []
        for name, data in self.users.items():
            encodings.append(data['encoding'])
            names.append(name)
        return encodings, names

    def get_user_gestures(self, name):
        if name in self.users:
            return self.users[name]['gestures']
        return []
    
    def get_user_count(self):
        return len(self.users)

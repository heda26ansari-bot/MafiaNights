import json
import os

FILE = "nicknames.json"

class NicknameManager:
    def __init__(self):
        self.data = {}
        self.load()

    def load(self):
        if os.path.exists(FILE):
            try:
                with open(FILE, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except:
                self.data = {}
        else:
            self.save()

    def save(self):
        with open(FILE, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)

    def set(self, user_id, nickname):
        self.data[str(user_id)] = nickname
        self.save()

    def get(self, user_id):
        return self.data.get(str(user_id))

    def all(self):
        return self.data

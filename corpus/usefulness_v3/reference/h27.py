class UserIndex:
    def __init__(self, users):
        self._by_id = {}
        for user in users:
            self._by_id.setdefault(user["id"], user)

    def get(self, uid):
        return self._by_id.get(uid)

    def __len__(self):
        return len(self._by_id)

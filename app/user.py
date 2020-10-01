from flask_login import UserMixin

from db import get_db


class User(UserMixin):
    def __init__(self, id_, name, profile_pic):
        self.id = id_
        self.name = name
        self.profile_pic = profile_pic

    @staticmethod
    def get(user_id):
        db = get_db()
        user = db.execute(
            "SELECT * FROM user WHERE id = ?", (user_id,)
        ).fetchone()
        if not user:
            return None

        user = User(
            id_=user[0], name=user[1], profile_pic=user[2]
        )
        return user

    @staticmethod
    def create(id_, name, profile_pic):
        db = get_db()
        db.execute(
            "INSERT INTO user (id, name, profile_pic)"
            " VALUES (?, ?, ?)",
            (id_, name, profile_pic),
        )
        db.commit()

    @staticmethod
    def delete(id_):
        db = get_db()
        db.execute(
            "DELETE FROM user WHERE id = ?",
            (id_,),
        )
        db.commit()
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint

from app import db

if TYPE_CHECKING:
    from flask_sqlalchemy.model import Model
else:
    Model = db.Model


class Client(Model):
    __tablename__ = "client"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    surname = db.Column(db.String(50), nullable=False)
    credit_card = db.Column(db.String(50))
    car_number = db.Column(db.String(10))

    parking = db.relationship("ClientParking", backref="client")

    def __init__(
        self,
        id: int | None = None,
        name: str = "",
        surname: str = "",
        credit_card: str | None = None,
        car_number: str = "",
    ) -> None:
        if id is not None:
            self.id = id

        self.name = name
        self.surname = surname
        self.credit_card = credit_card
        self.car_number = car_number

    def to_json(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class Parking(Model):
    __tablename__ = "parking"

    id = db.Column(db.Integer, primary_key=True)
    address = db.Column(db.String(100), nullable=False)
    opened = db.Column(db.Boolean)
    count_places = db.Column(db.Integer, nullable=False)
    count_available_places = db.Column(db.Integer, nullable=False)

    clients = db.relationship("ClientParking", backref="parking")

    def __init__(
        self,
        id: int | None = None,
        address: str = "",
        opened: bool = False,
        count_places: int = 0,
        count_available_places: int = 0,
    ) -> None:
        if id is not None:
            self.id = id

        self.address = address
        self.opened = opened
        self.count_places = count_places
        self.count_available_places = count_available_places

    def to_json(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    __table_args__ = (
        CheckConstraint(
            "count_available_places <= count_places",
            name="check_available_vs_total_places",
        ),
        CheckConstraint(
            "count_available_places >= 0", name="check_available_places_non_negative"
        ),
    )


class ClientParking(Model):
    __tablename__ = "client_parking"

    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey("client.id"))
    parking_id = db.Column(db.Integer, db.ForeignKey("parking.id"))
    time_in = db.Column(db.DateTime)
    time_out = db.Column(db.DateTime)

    __table_args__ = (
        db.UniqueConstraint("client_id", "parking_id", name="unique_client_parking"),
    )

    def __init__(
        self,
        client_id: int,
        parking_id: int,
        time_in: datetime,
    ) -> None:
        self.client_id = client_id
        self.parking_id = parking_id
        self.time_in = time_in

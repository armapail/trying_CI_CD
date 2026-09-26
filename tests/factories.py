import factory
from models import Client, Parking
from app import db
import random


class ClientFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Client
        sqlalchemy_session = db.session

    name = factory.Faker('first_name')
    surname = factory.Faker('last_name')
    credit_card = factory.Maybe(
        factory.LazyAttribute(lambda o: random.choice([True, False])),
        yes_declaration='',
        no_declaration=factory.Faker('credit_card_number')
    )
    car_number = factory.Faker('bothify', text='??###?')


class ParkingFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Parking
        sqlalchemy_session = db.session

    address = factory.Faker('address')
    opened = random.choice([True, False])
    count_places = factory.LazyAttribute(lambda x: random.randrange(10, 1000))
    count_available_places = factory.LazyAttribute(lambda o: random.randrange(0, o.count_places))

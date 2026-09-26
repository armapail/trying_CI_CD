from models import Client, Parking
from factories import ClientFactory, ParkingFactory


def test_add_client(client, db_session) -> None:
    """
    Проверяет создание клиента через POST /clients.

    Сначала фабрика создаёт и сохраняет одного клиента.
    Затем endpoint создаёт второго клиента на основе данных,
    отправленных в форме.

    Поэтому после запроса в таблице ожидаются две записи.

    Args:
        client: Тестовый HTTP-клиент Flask.
        db_session: SQLAlchemy-сессия тестовой базы.

    """
    user = ClientFactory()
    response = client.post(
        '/clients',
        data={
            "name": user.name,
            "surname": user.surname,
            "credit_card": user.credit_card,
            "car_number": user.car_number
        }
    )

    assert response.status_code == 201
    assert response.data == b'Ok'

    assert user.id is not None
    assert len(db_session.query(Client).all()) == 2


def test_add_parking(client, db_session) -> None:
    """
    Проверяет создание парковки через POST /parkings.

    Сначала фабрика создаёт и сохраняет одну парковку.
    Затем endpoint создаёт вторую парковку с теми же данными.

    Args:
        client: Тестовый HTTP-клиент Flask.
        db_session: SQLAlchemy-сессия тестовой базы.

    """
    parking = ParkingFactory()
    response = client.post(
        '/parkings',
        data={
            "address": parking.address,
            "opened": parking.opened,
            "count_places": parking.count_places,
            "count_available_places": parking.count_available_places
        }
    )

    assert response.status_code == 201

    assert parking.id is not None
    assert parking.count_places >= parking.count_available_places
    assert len(db_session.query(Parking).all()) == 2

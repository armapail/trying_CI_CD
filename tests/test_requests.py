import pytest
from sqlalchemy.exc import IntegrityError

from models import Client, ClientParking, Parking


@pytest.mark.parametrize(
    "url",
    [
        "/clients",
        "/clients/1",
    ],
)
def test_get_urls(client, db_session, url: str) -> None:
    """
    Проверяет получение списка клиентов и клиента по идентификатору.

    Перед выполнением запроса в тестовую базу добавляются два клиента.

    Args:
        client: Тестовый HTTP-клиент Flask.
        db_session: SQLAlchemy-сессия тестовой базы.
        url: URL, который необходимо проверить.

    """
    db_session.add_all(
        [
            Client(name="Tester", surname="yes", credit_card="123123"),
            Client(name="Another", surname="Tester"),
        ]
    )
    db_session.commit()

    response = client.get(url)
    assert response.status_code == 200


def test_add_client(client, db_session) -> None:
    """
    Проверяет создание клиента через POST /clients.

    Проверяется, что:

    - endpoint возвращает HTTP 201;
    - тело ответа равно ``Ok``;
    - клиент появляется в базе данных;
    - значения полей сохраняются корректно.

    Args:
        client: Тестовый HTTP-клиент Flask.
        db_session: SQLAlchemy-сессия тестовой базы.
    """
    response = client.post(
        "/clients",
        data={
            "name": "Third",
            "surname": "Tester",
            "credit_card": "321321",
            "car_number": "AE777E",
        },
    )

    assert response.status_code == 201
    assert response.data == b"Ok"

    created_client = db_session.query(Client).filter_by(credit_card="321321").first()

    assert created_client is not None
    assert created_client.name == "Third"


def test_add_parking(client, db_session) -> None:
    """
    Проверяет создание парковки через POST /parkings.

    Также проверяется ограничение базы данных:
    количество свободных мест не может быть больше
    общего количества мест.

    Args:
        client: Тестовый HTTP-клиент Flask.
        db_session: SQLAlchemy-сессия тестовой базы.

    """
    response = client.post(
        "/parkings",
        data={
            "address": "Тут",
            "opened": True,
            "count_places": 100,
            "count_available_places": 2,
        },
    )

    assert response.status_code == 201

    new_parking = db_session.query(Parking).filter_by(address="Тут").first()

    assert new_parking is not None
    assert new_parking.count_places == 100
    assert new_parking.count_available_places == 2

    with pytest.raises(IntegrityError):
        response = client.post(
            "/parkings",
            data={
                "address": "Не тут",
                "opened": True,
                "count_places": 100,
                "count_available_places": 200,
            },
        )

        assert response.status_code == 500


@pytest.fixture()
def db_test_data(db_session) -> None:
    """
    Заполняет тестовую базу данными клиентов и парковок.

    В базу добавляются:

    - три клиента;
    - две парковки;

    Args:
        db_session: SQLAlchemy-сессия тестовой базы.
    """
    db_session.add_all(
        [
            Client(
                id=99999,
                name="Poul",
                surname="yes",
                credit_card="123123",
                car_number="123",
            ),
            Client(
                id=99998,
                name="Fred",
                surname="yes",
                credit_card="",
                car_number="123",
            ),
            Client(
                id=99997,
                name="Piter",
                surname="yes",
                credit_card="321321",
                car_number="123",
            ),
            Parking(
                id=99999,
                address="Гагарина 2",
                opened=True,
                count_places=200,
                count_available_places=2,
            ),
            Parking(
                id=99998,
                address="Гагарина 20",
                opened=False,
                count_places=200,
                count_available_places=100,
            ),
        ]
    )
    db_session.commit()


@pytest.mark.parking_actions
def test_parking_entrance(client, db_session, db_test_data) -> None:
    """Проверяет сценарии въезда клиента на парковку.

    Проверяются следующие случаи:

    - отсутствующая парковка или клиент;
    - въезд на закрытую парковку;
    - успешный въезд двух клиентов;
    - попытка въезда при отсутствии свободных мест;
    - уменьшение количества свободных мест;

    Args:
        client: Тестовый HTTP-клиент Flask.
        db_session: SQLAlchemy-сессия тестовой базы.
        db_test_data: Фикстура с начальными данными.
    """
    response = client.post(
        "/client_parkings", data={"client_id": 10003, "parking_id": 10003}
    )
    assert response.status_code == 404

    response = client.post(
        "/client_parkings", data={"client_id": 99999, "parking_id": 99998}
    )
    assert response.status_code == 400

    response = client.post(
        "/client_parkings", data={"client_id": 99999, "parking_id": 99999}
    )
    assert response.status_code == 201

    response = client.post(
        "/client_parkings", data={"client_id": 99998, "parking_id": 99999}
    )
    assert response.status_code == 201

    response = client.post(
        "/client_parkings", data={"client_id": 99997, "parking_id": 99999}
    )
    assert response.status_code == 400

    client_parking = db_session.query(ClientParking).filter_by(parking_id=99999).all()
    parking = db_session.query(Parking).filter_by(id=99999).first()

    assert len(client_parking) == 2
    assert parking.address == "Гагарина 2"
    assert parking.opened
    assert parking.count_available_places == 0


@pytest.mark.parking_actions
def test_parking_exit(client, db_session, db_test_data) -> None:
    """
    Проверяет сценарии выезда клиента с парковки.

    Проверяются следующие случаи:

    - успешный выезд клиента с кредитной картой;
    - увеличение количества свободных мест;
    - заполнение времени выезда;
    - отказ клиенту без кредитной карты;
    - отсутствие изменения времени выезда при ошибке.

    Args:
        client: Тестовый HTTP-клиент Flask.
        db_session: SQLAlchemy-сессия тестовой базы.
        db_test_data: Фикстура с начальными данными.
    """
    client_parking = db_session.query(ClientParking).filter_by(parking_id=99999).all()
    parking = db_session.query(Parking).filter_by(id=99999).first()
    if len(client_parking) == 0:
        response = client.post(
            "/client_parkings", data={"client_id": 99999, "parking_id": 99999}
        )
        assert response.status_code == 201

        response = client.post(
            "/client_parkings", data={"client_id": 99998, "parking_id": 99999}
        )
        assert response.status_code == 201

    response = client.delete(
        "/client_parkings", data={"client_id": 99999, "parking_id": 99999}
    )
    client_parking = (
        db_session.query(ClientParking)
        .filter_by(parking_id=99999, client_id=99999)
        .first()
    )
    assert response.status_code == 200
    assert parking.count_available_places == 1
    assert client_parking.time_in < client_parking.time_out

    response = client.delete(
        "/client_parkings", data={"client_id": 99998, "parking_id": 99999}
    )
    client_parking = (
        db_session.query(ClientParking)
        .filter_by(parking_id=99999, client_id=99998)
        .first()
    )
    assert response.status_code == 400
    assert client_parking.time_out is None

from datetime import datetime

from flask import Flask, Response, jsonify, request
from flask.json.provider import DefaultJSONProvider
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import update

db = SQLAlchemy()


def create_app(test_config=None) -> Flask:
    """
    Создаёт и настраивает Flask-приложение парковки.

    Returns:
        Настроенный экземпляр Flask-приложения.

    """
    app = Flask(__name__)

    json_provider = app.json
    assert isinstance(json_provider, DefaultJSONProvider)
    json_provider.ensure_ascii = False
    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI="sqlite:///parking.db",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )

    if test_config is not None:
        app.config.update(test_config)

    db.init_app(app)

    from models import Client, ClientParking, Parking

    def before_first_request() -> None:
        db.create_all()

    with app.app_context():
        before_first_request()

    @app.teardown_appcontext
    def shutdown_session(_exception: BaseException | None = None) -> None:
        """
        Закрывает текущую SQLAlchemy-сессию после завершения контекста.

        Args:
            _exception: Исключение, возникшее во время обработки запроса.
                Параметр передаётся Flask автоматически.
        """
        db.session.remove()

    @app.route("/clients", methods=["GET"])
    def get_clients() -> tuple[Response, int]:
        """
        Возвращает список всех клиентов.

        Returns:
            JSON-массив клиентов и HTTP-статус 200.
        """
        clients = db.session.query(Client).all()
        clients_list = [c.to_json() for c in clients]

        return jsonify(clients_list), 200

    @app.route("/clients", methods=["POST"])
    def create_client() -> tuple[str, int]:
        """
        Создаёт нового клиента.

        Ожидает данные формы:

        - ``name`` — имя клиента;
        - ``surname`` — фамилия клиента;
        - ``credit_card`` — номер карты, необязательное поле;
        - ``car_number`` — номер автомобиля, необязательное поле.

        Returns:
            ``Ok`` и HTTP-статус 201.
        """
        name = request.form.get("name", type=str)
        surname = request.form.get("surname", type=str)
        credit_card = request.form.get("credit_card", type=str, default="")
        car_number = request.form.get("car_number", type=str, default="")

        if name is None or surname is None:
            return "Не указанно имя или фамилия", 400

        new_client = Client(
            name=name, surname=surname, credit_card=credit_card, car_number=car_number
        )

        db.session.add(new_client)
        db.session.commit()
        return "Ok", 201

    @app.route("/clients/<int:client_id>", methods=["GET"])
    def find_client_for_id(client_id: int) -> tuple[Response, int]:
        """
        Возвращает клиента по идентификатору.

        Args:
            client_id: Уникальный идентификатор клиента.

        Returns:
            Данные клиента и HTTP-статус 200.
        """
        client = (db.session.query(Client).where(Client.id == client_id)).first()

        if client is None:
            return jsonify({"message": "Такого id не существует"}), 404

        return jsonify(client.to_json()), 200

    @app.route("/parkings", methods=["POST"])
    def create_new_parking_lot() -> tuple[str, int]:
        """
        Создаёт новую парковку.

        Ожидает данные формы:

        - ``address`` — адрес парковки;
        - ``opened`` — признак открытой парковки;
        - ``count_places`` — общее количество мест;
        - ``count_available_places`` — количество свободных мест.

        Если ``count_available_places`` не передано,
        используется значение ``count_places``.

        Returns:
            ``Ok`` и HTTP-статус 201.
        """
        address = request.form.get("address", type=str)
        opened = request.form.get("opened", type=bool, default=False)
        count_places = request.form.get("count_places", type=int)
        count_available_places = request.form.get(
            "count_available_places",
            type=int,
            default=count_places,
        )

        if address is None or count_places is None or count_available_places is None:
            return ("Не указан адресс, колличество доступных или общих мест", 400)

        new_parking_lot = Parking(
            address=address,
            opened=opened,
            count_places=count_places,
            count_available_places=count_available_places,
        )

        db.session.add(new_parking_lot)
        db.session.commit()
        return "Ok", 201

    @app.route("/client_parkings", methods=["POST"])
    def client_come_parking() -> tuple[str | Response, int]:
        """
        Регистрирует въезд клиента на парковку.

        Ожидает данные формы:

        - ``client_id`` — идентификатор клиента;
        - ``parking_id`` — идентификатор парковки.

        Условия успешного въезда:

        - парковка существует;
        - парковка открыта;
        - на парковке есть свободные места;
        - клиент существует.

        При успешном въезде уменьшается количество свободных мест,
        а в таблицу связей добавляется время въезда.

        Returns:
            ``ok`` и HTTP-статус 201 при успехе.

        Errors:
            404 — парковка или клиент не найдены;
            400 — парковка закрыта
                или свободных мест нет.
        """
        client_id = request.form.get("client_id", type=int)
        parking_id = request.form.get("parking_id", type=int)

        if client_id is None or parking_id is None:
            return (jsonify({"message": "Не указан id клиента и/или парковки"}), 400)

        parking_lot = (
            db.session.query(Parking).where(Parking.id == parking_id)
        ).first()

        if parking_lot is None:
            return jsonify({"message": "id парковки не найден."}), 404
        elif not parking_lot.opened:
            return jsonify({"message": "Парковка закрыта"}), 400
        elif parking_lot.count_available_places <= 0:
            return jsonify({"message": "На парковке нет мест"}), 400

        client = (db.session.query(Client).where(Client.id == client_id)).first()

        if client is None:
            return jsonify({"message": "id клиента не найден"}), 404

        client_parking = ClientParking(
            client_id=client_id, parking_id=parking_id, time_in=datetime.now()
        )
        db.session.add(client_parking)

        db.session.execute(
            update(Parking)
            .where(Parking.id == parking_id)
            .values(count_available_places=Parking.count_available_places - 1)
        )

        db.session.commit()
        return "ok", 201

    @app.route("/client_parkings", methods=["DELETE"])
    def client_out_parking() -> tuple[str | Response, int]:
        """
        Регистрирует выезд клиента с парковки.

        Ожидает данные формы:

        - ``client_id`` — идентификатор клиента;
        - ``parking_id`` — идентификатор парковки.

        Для успешного выезда у клиента должна быть привязана
        кредитная карта.

        Returns:
            ``ok`` и HTTP-статус 200 при успехе.

        Errors:
            404 — связка клиента и парковки не найдена;
            400 — у клиента нет кредитной карты.
        """
        client_id = request.form.get("client_id", type=int)
        parking_id = request.form.get("parking_id", type=int)

        is_client_parking = (
            db.session.query(ClientParking).where(
                ClientParking.client_id == client_id,
                ClientParking.parking_id == parking_id,
            )
        ).first()

        if is_client_parking is None:
            return (
                jsonify({"message": "Связка client_id и parking_id не найдена"}),
                404,
            )

        this_client = (db.session.query(Client).where(Client.id == client_id)).first()
        if this_client is None:
            return jsonify({"message": "Клиент не найден"}), 400
        if this_client.credit_card is None or this_client.credit_card == "":
            return (jsonify({"message": "У клиента не привязана кредитная карта"}), 400)

        db.session.execute(
            update(Parking)
            .where(Parking.id == parking_id)
            .values(count_available_places=Parking.count_available_places + 1)
        )
        is_client_parking.time_out = datetime.now()
        db.session.commit()

        return "ok", 200

    return app

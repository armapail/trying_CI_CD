import pytest

from app import create_app, db


@pytest.fixture()
def app():
    """
    Создаёт тестовый экземпляр Flask-приложения.

    Для тестов используется отдельная SQLite-база данных,
    расположенная в оперативной памяти.

    Yields:
        Flask: Настроенный экземпляр тестового приложения.

    Cleanup:
        После завершения теста удаляет SQLAlchemy-сессию
        и все таблицы тестовой базы данных.
    """
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
    })

    with app.app_context():
        db.drop_all()
        db.create_all()

    yield app

    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    """
    Создаёт тестовый HTTP-клиент Flask.

    Клиент позволяет выполнять запросы к приложению
    без запуска реального веб-сервера.

    Args:
        app: Тестовый экземпляр Flask-приложения.

    Returns:
        FlaskClient: Клиент для GET, POST, DELETE и других
        HTTP-запросов.

    """
    return app.test_client()


@pytest.fixture()
def db_session(app):
    """
    Предоставляет SQLAlchemy-сессию для теста.

    Фикстура работает внутри application context Flask,
    который необходим для Flask-SQLAlchemy.

    Yields:
        scoped_session: Текущая SQLAlchemy-сессия.

    Cleanup:
        При завершении теста выполняет rollback и удаляет
        сессию из scoped_session.
    """
    with app.app_context():
        yield db.session

        db.session.rollback()
        db.session.remove()

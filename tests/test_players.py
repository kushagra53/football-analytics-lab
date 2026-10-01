from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_get_players():
    response = client.get("/players?limit=10&offset=0")

    assert response.status_code == 200
    assert len(response.json()) == 10


def test_players_pagination():
    response_1 = client.get("/players?limit=10&offset=0")
    response_2 = client.get("/players?limit=10&offset=10")

    assert response_1.status_code == 200
    assert response_2.status_code == 200

    players_1 = response_1.json()
    players_2 = response_2.json()

    assert players_1 != players_2


def test_players_filter():
    response = client.get("/players?league=Premier%20League&limit=10")

    assert response.status_code == 200

    players = response.json()

    assert len(players) <= 10

    for player in players:
        assert player["league"] == "Premier League"


def test_player_not_found():
    response = client.get("/players/999999999")

    assert response.status_code == 404
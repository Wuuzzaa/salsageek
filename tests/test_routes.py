import pytest
from flask import url_for

def test_all_get_routes(client, app):
    """
    Automatisierter Test, der alle registrierten GET-Routen der App durchläuft
    und prüft, ob sie den Statuscode 200 (OK) oder 302 (Redirect) zurückgeben.
    """
    with app.test_request_context():
        # Wir sammeln alle Regeln (Routen)
        rules = list(app.url_map.iter_rules())
        
        for rule in rules:
            # Wir testen nur GET-Routen
            if "GET" not in rule.methods:
                continue
            
            # Überspringe Routen, die Argumente erfordern (z.B. <element_id>)
            # Diese werden separat getestet oder brauchen Default-Werte
            if rule.arguments:
                continue
            
            # Statische Dateien überspringen
            if rule.endpoint == 'static':
                continue

            url = url_for(rule.endpoint)
            print(f"Testing {url} ...")
            response = client.get(url)
            
            # Wir akzeptieren 200 (OK) oder 302 (Redirect)
            assert response.status_code in [200, 302], f"Route {url} failed with status {response.status_code}"

def test_specific_routes_with_args(client, app):
    """
    Testet Routen, die Parameter erfordern, mit existierenden IDs.
    """
    # Test Element Detail (nehme eine ID, die wahrscheinlich existiert)
    element_url = "/element/basic"
    response = client.get(element_url)
    assert response.status_code in [200, 404] # 404 ist okay, wenn die ID nicht da ist, aber kein 500

    # Test Figure Detail
    figure_url = "/figure/1" # Annahme: ID 1 existiert
    response = client.get(figure_url)
    assert response.status_code in [200, 302, 404]

def test_builder_search(client):
    """
    Testet die Suchfunktion im Builder (AJAX/API).
    """
    response = client.get("/builder?search=basic")
    assert response.status_code == 200
    assert b"Basic" in response.data or b"basic" in response.data

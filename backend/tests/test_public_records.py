from tests.helpers import create_registration


def test_public_registry_lists_only_public_records(client, user_factory):
    creator = user_factory(display_name="Ada Lovelace")
    create_registration(client, creator["headers"], title="Published Engine", privacy="public")
    create_registration(client, creator["headers"], title="Confidential Engine", privacy="private")
    create_registration(
        client, creator["headers"], title="Fingerprint Only Engine", privacy="public_fingerprint"
    )

    response = client.get("/api/public/records")
    assert response.status_code == 200
    body = response.json()

    assert body["total"] == 1
    assert body["total_creators"] == 1
    item = body["items"][0]
    assert item["title"] == "Published Engine"
    assert item["creator_name"] == "Ada Lovelace"
    assert item["registration_reference"].startswith("AQ-")
    assert item["fingerprint"] and len(item["fingerprint"]) == 64
    assert item["verify_path"] == f"/verify/{item['registration_reference']}"


def test_public_registry_searches_creator_name_and_title(client, user_factory):
    ada = user_factory(display_name="Ada Lovelace")
    grace = user_factory(display_name="Grace Hopper")
    create_registration(client, ada["headers"], title="Analytical Engine", privacy="public")
    create_registration(client, grace["headers"], title="Compiler Design", privacy="public")

    by_name = client.get("/api/public/records", params={"q": "grace"})
    assert by_name.status_code == 200
    names = by_name.json()["items"]
    assert len(names) == 1
    assert names[0]["creator_name"] == "Grace Hopper"

    by_title = client.get("/api/public/records", params={"q": "analytical"})
    assert by_title.status_code == 200
    titles = by_title.json()["items"]
    assert len(titles) == 1
    assert titles[0]["title"] == "Analytical Engine"

    missing = client.get("/api/public/records", params={"q": "nobody-here"})
    assert missing.status_code == 200
    assert missing.json()["total"] == 0
    assert missing.json()["items"] == []


def test_public_registry_filters_by_asset_type_and_sorts(client, user_factory):
    creator = user_factory(display_name="Public Creator")
    create_registration(
        client, creator["headers"], title="Poster", privacy="public", asset_type="design"
    )
    create_registration(
        client, creator["headers"], title="Paper", privacy="public", asset_type="research"
    )

    filtered = client.get("/api/public/records", params={"asset_type": "design"})
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["asset_type"] == "design"

    sorted_items = client.get("/api/public/records", params={"sort": "title"})
    assert sorted_items.status_code == 200
    titles = [entry["title"] for entry in sorted_items.json()["items"]]
    assert titles == sorted(titles)

    facets = {entry["value"] for entry in sorted_items.json()["asset_types"]}
    assert facets == {"design", "research"}


def test_public_registry_never_leaks_private_fields(client, user_factory):
    creator = user_factory(display_name="Careful Creator")
    create_registration(client, creator["headers"], title="Safe Work", privacy="public")

    body = client.get("/api/public/records").json()
    item = body["items"][0]
    forbidden = {"email", "user_id", "owner_id", "storage_path", "secret", "organization_id", "id"}
    assert forbidden.isdisjoint(item.keys())
    assert "storage_path" not in item

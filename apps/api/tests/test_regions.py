from unittest.mock import MagicMock

import pytest

from app.errors import DomainError
from app.providers.regions import catalog, search_regions
from app.services.regions import RegionService


def test_search_disambiguates_city_district_and_pinyin() -> None:
    assert search_regions("南京")[0].id == "cn:3201"
    assert search_regions("nanjing")[0].id == "cn:3201"
    districts = search_regions("鼓楼")
    assert len({r.path for r in districts}) > 1
    assert all(r.name == "鼓楼区" for r in districts)
    assert search_regions("") == []
    assert search_regions("不存在的行政区") == []
    city = catalog()["cn:3201"]
    assert city.parent_id == "cn:32"
    assert city.boundary_file == "/maps/regions/32.geojson"
    assert city.country_code == "CN"
    assert city.timezone == "Asia/Shanghai"
    assert city.bbox[0] < city.longitude < city.bbox[2]
    assert city.bbox[1] < city.latitude < city.bbox[3]


def test_resolve_uses_stable_identity_and_database_conflict_guard() -> None:
    session = MagicMock()
    service = RegionService(session)
    service.resolve("cn:3201")
    first = session.execute.call_args.args[0].compile()
    service.resolve("cn:3201")
    second = session.execute.call_args.args[0].compile()
    assert first.params["id"] == second.params["id"]
    assert first.params["metadata"] == {"region_id": "cn:3201"}
    assert "ON CONFLICT (id) DO NOTHING" in str(first)
    assert first.params["canonical_name"] == "南京市"
    with pytest.raises(DomainError):
        service.resolve("cn:missing")

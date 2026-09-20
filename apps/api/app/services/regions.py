from uuid import NAMESPACE_URL, uuid5

from geoalchemy2.elements import WKTElement
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.errors import DomainError
from app.models import Place
from app.providers.regions import Region, catalog, search_regions


class RegionService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def search(self, query: str) -> list[Region]:
        return search_regions(query)

    def resolve(self, region_id: str) -> Place:
        region = catalog().get(region_id)
        if region is None:
            raise DomainError("REGION_NOT_FOUND", "Region boundary is not available", 404)
        # Stable identity plus ON CONFLICT protects repeat selection and concurrent requests.
        place_id = uuid5(NAMESPACE_URL, f"https://tovia.local/regions/{region.id}")
        self.session.execute(
            insert(Place)
            .values(
                id=place_id,
                canonical_name=region.name,
                country_code=region.country_code,
                admin1=region.admin1,
                city=region.city,
                timezone=region.timezone,
                location=WKTElement(f"POINT({region.longitude} {region.latitude})", srid=4326),
                metadata_={"region_id": region.id},
            )
            .on_conflict_do_nothing(index_elements=[Place.id])
        )
        self.session.commit()
        place = self.session.get(Place, place_id)
        assert place is not None
        return place

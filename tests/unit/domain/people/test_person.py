"""Unit tests for the Person domain entity."""

from __future__ import annotations

from datetime import date
from uuid import UUID, uuid4

import pytest

from clinic_management.domain.people.person import Person
from clinic_management.domain.shared.address import Address
from clinic_management.domain.shared.contact import ContactInfo
from clinic_management.domain.shared.errors import ValidationError


@pytest.fixture
def sample_contact() -> ContactInfo:
    """Fixture returning a valid ContactInfo."""
    return ContactInfo(phone="0550123456", email="ahmed.test@clinic.dz")


@pytest.fixture
def sample_address() -> Address:
    """Fixture returning a valid Address."""
    return Address(line1="123 Rue Didouche", city="Algiers", country_code="DZ")


class TestPersonConstruction:
    """Tests for Person entity construction and validation."""

    def test_valid_minimal_person(self, sample_contact: ContactInfo) -> None:
        """Person with required fields only (no birth_date or address)."""
        pid = uuid4()
        person = Person(
            id=pid,
            given_name="Ahmed",
            family_name="Ammiche",
            contact=sample_contact,
        )
        assert person.id == pid
        assert person.version == 0
        assert person.given_name == "Ahmed"
        assert person.family_name == "Ammiche"
        assert person.contact == sample_contact
        assert person.birth_date is None
        assert person.address is None

    def test_valid_full_person_with_accents(
        self, sample_contact: ContactInfo, sample_address: Address
    ) -> None:
        """Person with all fields, preserving accented characters."""
        pid = uuid4()
        person = Person(
            id=pid,
            version=1,
            given_name="  Éléonore  ",
            family_name="  Bouchaâba  ",
            birth_date=date(1992, 8, 25),
            contact=sample_contact,
            address=sample_address,
        )
        # Verify names are stripped but accents preserved
        assert person.given_name == "Éléonore"
        assert person.family_name == "Bouchaâba"
        assert person.full_name() == "Éléonore Bouchaâba"
        assert person.birth_date == date(1992, 8, 25)
        assert person.address == sample_address

    @pytest.mark.parametrize("invalid_id", [None, "not-a-uuid", 12345])
    def test_invalid_id_raises_validation_error(
        self, invalid_id: object, sample_contact: ContactInfo
    ) -> None:
        """Non-UUID id raises ValidationError."""
        with pytest.raises(ValidationError):
            Person(
                id=invalid_id,  # type: ignore[arg-type]
                given_name="Ahmed",
                family_name="Benali",
                contact=sample_contact,
            )

    @pytest.mark.parametrize("invalid_version", [-1, -100, 1.5, "0", True])
    def test_invalid_version_raises_validation_error(
        self, invalid_version: object, sample_contact: ContactInfo
    ) -> None:
        """Invalid version integer raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Person(
                id=uuid4(),
                version=invalid_version,  # type: ignore[arg-type]
                given_name="Ahmed",
                family_name="Benali",
                contact=sample_contact,
            )
        assert exc_info.value.code == "INVALID_VALUE"
        assert exc_info.value.safe_details["field"] == "version"

    @pytest.mark.parametrize("empty_name", ["", "   ", "\t\n"])
    def test_empty_given_name_rejected(self, empty_name: str, sample_contact: ContactInfo) -> None:
        """Empty or whitespace given_name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Person(
                id=uuid4(),
                given_name=empty_name,
                family_name="Benali",
                contact=sample_contact,
            )
        assert exc_info.value.code == "INVALID_VALUE"
        assert exc_info.value.safe_details["field"] == "given_name"

    @pytest.mark.parametrize("empty_name", ["", "   ", "\t\n"])
    def test_empty_family_name_rejected(
        self, empty_name: str, sample_contact: ContactInfo
    ) -> None:
        """Empty or whitespace family_name raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Person(
                id=uuid4(),
                given_name="Ahmed",
                family_name=empty_name,
                contact=sample_contact,
            )
        assert exc_info.value.code == "INVALID_VALUE"
        assert exc_info.value.safe_details["field"] == "family_name"

    def test_invalid_contact_type_rejected(self) -> None:
        """Non-ContactInfo contact raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Person(
                id=uuid4(),
                given_name="Ahmed",
                family_name="Benali",
                contact="phone@clinic.dz",  # type: ignore[arg-type]
            )
        assert exc_info.value.code == "INVALID_VALUE"
        assert exc_info.value.safe_details["field"] == "contact"

    @pytest.mark.parametrize("invalid_birth", ["1990-01-01", 19900101, True])
    def test_invalid_birth_date_type_rejected(
        self, invalid_birth: object, sample_contact: ContactInfo
    ) -> None:
        """Non-date birth_date raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Person(
                id=uuid4(),
                given_name="Ahmed",
                family_name="Benali",
                contact=sample_contact,
                birth_date=invalid_birth,  # type: ignore[arg-type]
            )
        assert exc_info.value.code == "INVALID_VALUE"
        assert exc_info.value.safe_details["field"] == "birth_date"

    def test_invalid_address_type_rejected(self, sample_contact: ContactInfo) -> None:
        """Non-Address address raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            Person(
                id=uuid4(),
                given_name="Ahmed",
                family_name="Benali",
                contact=sample_contact,
                address="123 Rue Didouche",  # type: ignore[arg-type]
            )
        assert exc_info.value.code == "INVALID_VALUE"
        assert exc_info.value.safe_details["field"] == "address"


class TestPersonBehavior:
    """Tests for Person methods and behavior."""

    def test_full_name(self, sample_contact: ContactInfo) -> None:
        """full_name combines given_name and family_name."""
        person = Person(
            id=uuid4(),
            given_name="Fatima",
            family_name="Zahra",
            contact=sample_contact,
        )
        assert person.full_name() == "Fatima Zahra"

    def test_age_on_with_known_birth_date(self, sample_contact: ContactInfo) -> None:
        """age_on delegates to date calculation when birth_date is set."""
        person = Person(
            id=uuid4(),
            given_name="Karim",
            family_name="Meziane",
            contact=sample_contact,
            birth_date=date(2000, 3, 15),
        )
        assert person.age_on(date(2026, 3, 14)) == 25
        assert person.age_on(date(2026, 3, 15)) == 26

    def test_age_on_with_unknown_birth_date_returns_none(
        self, sample_contact: ContactInfo
    ) -> None:
        """age_on returns None when birth_date is None."""
        person = Person(
            id=uuid4(),
            given_name="Karim",
            family_name="Meziane",
            contact=sample_contact,
            birth_date=None,
        )
        assert person.age_on(date(2026, 3, 15)) is None

    def test_update_contact(
        self, sample_contact: ContactInfo, sample_address: Address
    ) -> None:
        """update_contact replaces contact and address."""
        person = Person(
            id=uuid4(),
            given_name="Samir",
            family_name="Mansouri",
            contact=sample_contact,
            address=None,
        )
        new_contact = ContactInfo(phone="0661234567", email="samir@new.dz")
        person.update_contact(new_contact, sample_address)

        assert person.contact == new_contact
        assert person.address == sample_address

        # Clearing address
        person.update_contact(new_contact, None)
        assert person.address is None

    def test_update_contact_invalid_types(self, sample_contact: ContactInfo) -> None:
        """update_contact raises ValidationError if invalid contact or address passed."""
        person = Person(
            id=uuid4(),
            given_name="Samir",
            family_name="Mansouri",
            contact=sample_contact,
        )
        with pytest.raises(ValidationError):
            person.update_contact("invalid_contact", None)  # type: ignore[arg-type]

        with pytest.raises(ValidationError):
            person.update_contact(sample_contact, "invalid_address")  # type: ignore[arg-type]


class TestPersonEntityIdentity:
    """Tests verifying M1 Entity identity behavior for Person."""

    def test_same_id_equals_regardless_of_attributes(self, sample_contact: ContactInfo) -> None:
        """Two Person instances with same id evaluate equal (M1 Entity contract)."""
        pid = uuid4()
        p1 = Person(id=pid, given_name="Ahmed", family_name="Ali", contact=sample_contact)
        p2 = Person(id=pid, given_name="Different", family_name="Name", contact=sample_contact)
        assert p1 == p2
        assert p1.same_identity(p2) is True

    def test_different_id_not_equal(self, sample_contact: ContactInfo) -> None:
        """Two Person instances with different ids evaluate unequal."""
        p1 = Person(id=uuid4(), given_name="Ahmed", family_name="Ali", contact=sample_contact)
        p2 = Person(id=uuid4(), given_name="Ahmed", family_name="Ali", contact=sample_contact)
        assert p1 != p2

    def test_person_hash_disabled(self, sample_contact: ContactInfo) -> None:
        """Person entities cannot be hashed (M1 Entity contract)."""
        person = Person(id=uuid4(), given_name="Ahmed", family_name="Ali", contact=sample_contact)
        with pytest.raises(TypeError, match="unhashable"):
            hash(person)


from __future__ import annotations

import uuid
import pytest
from keylogix.identity import IdentityError, IdentityFactory, SequentialUUID


def test_identity_factory_generation():
    factory = IdentityFactory()
    id1 = factory.new_id()
    id2 = factory.new_id()
    assert id1 != id2
    assert factory.seen(id1) is True
    assert factory.seen(id2) is True
    assert factory.issued_count() == 2


def test_identity_factory_register():
    factory = IdentityFactory()
    custom_id = "custom-uuid-1234"
    assert factory.register(custom_id) == custom_id
    assert factory.seen(custom_id) is True

    # Registering duplicate must fail
    with pytest.raises(IdentityError, match="identifier collision"):
        factory.register(custom_id)


def test_sequential_uuid():
    seq = SequentialUUID()
    u1 = seq()
    u2 = seq()
    assert isinstance(u1, uuid.UUID)
    assert isinstance(u2, uuid.UUID)
    assert u1 != u2
    assert str(u1).endswith("000000000001")
    assert str(u2).endswith("000000000002")

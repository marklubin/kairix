"""Tests for prompts service."""

from sqlalchemy.ext.asyncio import AsyncSession

from kp3.services.prompts import (
    create_next_version,
    create_prompt,
    get_active_prompt,
    get_latest_version,
    get_prompt,
    get_prompt_by_version,
    list_prompts,
    set_active_prompt,
)


async def test_create_prompt(db_session: AsyncSession):
    """Create a new prompt."""
    prompt = await create_prompt(
        db_session,
        name="test_prompt",
        version=1,
        system_prompt="You are a helpful assistant.",
        user_prompt_template="Analyze: {passage}",
        field_descriptions={"field1": "description1"},
    )

    assert prompt.id is not None
    assert prompt.name == "test_prompt"
    assert prompt.version == 1
    assert prompt.system_prompt == "You are a helpful assistant."
    assert prompt.user_prompt_template == "Analyze: {passage}"
    assert prompt.field_descriptions == {"field1": "description1"}
    assert prompt.is_active is False


async def test_create_active_prompt(db_session: AsyncSession):
    """Create an active prompt."""
    prompt = await create_prompt(
        db_session,
        name="active_test",
        version=1,
        system_prompt="System",
        user_prompt_template="User",
        field_descriptions={},
        is_active=True,
    )

    assert prompt.is_active is True


async def test_get_prompt(db_session: AsyncSession):
    """Get prompt by ID."""
    created = await create_prompt(
        db_session,
        name="get_test",
        version=1,
        system_prompt="System",
        user_prompt_template="User",
        field_descriptions={},
    )
    await db_session.commit()

    found = await get_prompt(db_session, created.id)
    assert found is not None
    assert found.id == created.id


async def test_get_prompt_by_version(db_session: AsyncSession):
    """Get specific version of a prompt."""
    await create_prompt(
        db_session,
        name="versioned",
        version=1,
        system_prompt="V1",
        user_prompt_template="V1",
        field_descriptions={},
    )
    await create_prompt(
        db_session,
        name="versioned",
        version=2,
        system_prompt="V2",
        user_prompt_template="V2",
        field_descriptions={},
    )
    await db_session.commit()

    v1 = await get_prompt_by_version(db_session, "versioned", 1)
    v2 = await get_prompt_by_version(db_session, "versioned", 2)

    assert v1 is not None
    assert v1.system_prompt == "V1"
    assert v2 is not None
    assert v2.system_prompt == "V2"


async def test_get_active_prompt(db_session: AsyncSession):
    """Get the active prompt for a name."""
    await create_prompt(
        db_session,
        name="active_lookup",
        version=1,
        system_prompt="V1",
        user_prompt_template="V1",
        field_descriptions={},
        is_active=False,
    )
    await create_prompt(
        db_session,
        name="active_lookup",
        version=2,
        system_prompt="V2",
        user_prompt_template="V2",
        field_descriptions={},
        is_active=True,
    )
    await db_session.commit()

    active = await get_active_prompt(db_session, "active_lookup")
    assert active is not None
    assert active.version == 2
    assert active.system_prompt == "V2"


async def test_get_active_prompt_none(db_session: AsyncSession):
    """Return None when no active prompt exists."""
    active = await get_active_prompt(db_session, "nonexistent")
    assert active is None


async def test_set_active_prompt(db_session: AsyncSession):
    """Setting active prompt deactivates others."""
    p1 = await create_prompt(
        db_session,
        name="switch_active",
        version=1,
        system_prompt="V1",
        user_prompt_template="V1",
        field_descriptions={},
        is_active=True,
    )
    p2 = await create_prompt(
        db_session,
        name="switch_active",
        version=2,
        system_prompt="V2",
        user_prompt_template="V2",
        field_descriptions={},
        is_active=False,
    )
    await db_session.commit()

    # p1 should be active
    active = await get_active_prompt(db_session, "switch_active")
    assert active.version == 1

    # Set p2 as active
    await set_active_prompt(db_session, p2.id)
    await db_session.commit()

    # Now p2 should be active
    active = await get_active_prompt(db_session, "switch_active")
    assert active.version == 2

    # p1 should be deactivated
    await db_session.refresh(p1)
    assert p1.is_active is False


async def test_list_prompts(db_session: AsyncSession):
    """List all prompts."""
    await create_prompt(
        db_session,
        name="list_test_a",
        version=1,
        system_prompt="A1",
        user_prompt_template="A1",
        field_descriptions={},
    )
    await create_prompt(
        db_session,
        name="list_test_b",
        version=1,
        system_prompt="B1",
        user_prompt_template="B1",
        field_descriptions={},
    )
    await db_session.commit()

    prompts = await list_prompts(db_session)
    assert len(prompts) >= 2

    names = {p.name for p in prompts}
    assert "list_test_a" in names
    assert "list_test_b" in names


async def test_list_prompts_by_name(db_session: AsyncSession):
    """List prompts filtered by name."""
    await create_prompt(
        db_session,
        name="filter_test",
        version=1,
        system_prompt="V1",
        user_prompt_template="V1",
        field_descriptions={},
    )
    await create_prompt(
        db_session,
        name="filter_test",
        version=2,
        system_prompt="V2",
        user_prompt_template="V2",
        field_descriptions={},
    )
    await create_prompt(
        db_session,
        name="other_prompt",
        version=1,
        system_prompt="O1",
        user_prompt_template="O1",
        field_descriptions={},
    )
    await db_session.commit()

    prompts = await list_prompts(db_session, name="filter_test")
    assert len(prompts) == 2
    assert all(p.name == "filter_test" for p in prompts)


async def test_get_latest_version(db_session: AsyncSession):
    """Get the latest version number for a prompt name."""
    await create_prompt(
        db_session,
        name="version_test",
        version=1,
        system_prompt="V1",
        user_prompt_template="V1",
        field_descriptions={},
    )
    await create_prompt(
        db_session,
        name="version_test",
        version=5,
        system_prompt="V5",
        user_prompt_template="V5",
        field_descriptions={},
    )
    await db_session.commit()

    latest = await get_latest_version(db_session, "version_test")
    assert latest == 5


async def test_get_latest_version_none(db_session: AsyncSession):
    """Return 0 for non-existent prompt name."""
    latest = await get_latest_version(db_session, "nonexistent_prompt")
    assert latest == 0


async def test_create_next_version(db_session: AsyncSession):
    """Create next version auto-increments."""
    await create_prompt(
        db_session,
        name="auto_version",
        version=1,
        system_prompt="V1",
        user_prompt_template="V1",
        field_descriptions={},
    )
    await db_session.commit()

    p2 = await create_next_version(
        db_session,
        name="auto_version",
        system_prompt="V2",
        user_prompt_template="V2",
        field_descriptions={},
    )

    assert p2.version == 2


async def test_create_next_version_new_prompt(db_session: AsyncSession):
    """Create next version starts at 1 for new prompts."""
    p1 = await create_next_version(
        db_session,
        name="brand_new_prompt",
        system_prompt="V1",
        user_prompt_template="V1",
        field_descriptions={},
    )

    assert p1.version == 1

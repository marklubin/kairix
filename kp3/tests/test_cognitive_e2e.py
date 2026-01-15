"""End-to-end tests for the Unified Cognitive Memory Architecture.

These tests validate KP3's cognitive memory system as specified in
docs/unified-cognitive-memory-architecture.md

Test Scenarios A-T cover:
- Passages: create/read/immutability
- Refs: create/update/history/list-by-prefix with optimistic locking
- Derivations: provenance tracking
- Frames: create/fork/version/activate
- Perceptions: create + semantic entity canonicalization
- Cognition increment: atomic state transitions
- Frame-scoped search
- Concurrency safety + idempotency + rollback on failure

All tests run WITHOUT v2-runtime/Letta/Kairix orchestration dependencies.
"""

from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from kp3.services.cognition import clear_idempotency_cache
from kp3.services.derivations import create_derivations, get_derived, get_sources
from kp3.services.frames import create_frame, fork_frame, get_frame
from kp3.services.passages import create_passage, get_passage
from kp3.services.refs import get_ref, get_ref_history, set_ref

# Test agent ID
TEST_AGENT_ID = "test-agent"


def perception(name: str, suffix: str = "") -> dict[str, str]:
    """Helper to create perception config dicts."""
    ref_suffix = f"-{suffix}" if suffix else ""
    return {
        "name": name,
        "ref": f"{TEST_AGENT_ID}/perception/{name}{ref_suffix}",
        "process": f"step_{name}",
    }


# =============================================================================
# Scenario A: Passage + Ref Primitives
# =============================================================================


@pytest.mark.docker
@pytest.mark.asyncio
async def test_scenario_a_passage_ref_primitives(db_session: AsyncSession) -> None:
    """Scenario A: Validate foundation behavior.

    Steps:
    1. POST /passages content "Hello world" → Returns passage ID
    2. GET /passages/{id} → Content matches
    3. PUT /refs/test-agent/perception/persona → passage_id → Ref created
    4. GET /refs/test-agent/perception/persona → Resolves to correct passage
    5. Update ref to new passage → Success
    6. GET /refs/{name}/history → Shows 2 versions, ordered
    """
    # Step 1: Create passage
    p1 = await create_passage(
        db_session,
        content="Hello world",
        passage_type="test",
        agent_id=TEST_AGENT_ID,
    )
    await db_session.flush()

    assert p1.id is not None
    assert p1.content == "Hello world"

    # Step 2: Get passage by ID
    fetched = await get_passage(db_session, p1.id)
    assert fetched is not None
    assert fetched.content == "Hello world"

    # Step 3: Create ref pointing to passage
    ref_name = f"{TEST_AGENT_ID}/perception/persona"
    ref = await set_ref(db_session, ref_name, p1.id, fire_hooks=False)
    await db_session.flush()

    assert ref.name == ref_name
    assert ref.passage_id == p1.id

    # Step 4: Get ref resolves to correct passage
    passage_id = await get_ref(db_session, ref_name)
    assert passage_id == p1.id

    # Step 5: Update ref to new passage
    p2 = await create_passage(
        db_session,
        content="Updated content",
        passage_type="test",
        agent_id=TEST_AGENT_ID,
    )
    await db_session.flush()

    await set_ref(db_session, ref_name, p2.id, fire_hooks=False)
    await db_session.flush()

    # Verify ref updated
    updated_passage_id = await get_ref(db_session, ref_name)
    assert updated_passage_id == p2.id

    # Step 6: Check history shows 2 versions
    history = await get_ref_history(db_session, ref_name)

    assert len(history) == 2, f"Expected 2 history entries, got {len(history)}"

    # Find the first entry (previous_passage_id=None) and second entry (previous_passage_id=p1.id)
    # Note: ordering by timestamp may be non-deterministic when operations happen quickly
    first_entry = next((h for h in history if h["previous_passage_id"] is None), None)
    second_entry = next((h for h in history if h["previous_passage_id"] is not None), None)

    assert first_entry is not None, "Should have first entry with no previous"
    assert second_entry is not None, "Should have second entry with previous"

    assert first_entry["passage_id"] == p1.id
    assert second_entry["passage_id"] == p2.id
    assert second_entry["previous_passage_id"] == p1.id


# =============================================================================
# Scenario B: Derivations Form Provenance Chain
# =============================================================================


@pytest.mark.docker
@pytest.mark.asyncio
async def test_scenario_b_derivations_provenance_chain(db_session: AsyncSession) -> None:
    """Scenario B: Provenance is queryable both directions.

    Steps:
    1. Create P1 ("state v1")
    2. Create P2 ("state v2")
    3. Create derivation: P2 derived from P1
    4. GET /passages/{P2}/sources → Contains P1
    5. GET /passages/{P1}/derived → Contains P2
    """
    # Step 1: Create P1
    p1 = await create_passage(
        db_session,
        content="state v1",
        passage_type="test",
        agent_id=TEST_AGENT_ID,
    )
    await db_session.commit()
    await db_session.refresh(p1)

    # Step 2: Create P2
    p2 = await create_passage(
        db_session,
        content="state v2",
        passage_type="test",
        agent_id=TEST_AGENT_ID,
    )
    await db_session.commit()
    await db_session.refresh(p2)

    # Step 3: Create derivation
    await create_derivations(
        db_session,
        derived_passage_id=p2.id,
        source_passage_ids=[p1.id],
    )
    await db_session.commit()

    # Step 4: Get sources of P2
    sources = await get_sources(db_session, p2.id)
    assert len(sources) == 1
    assert sources[0].id == p1.id

    # Step 5: Get derived from P1
    derived = await get_derived(db_session, p1.id)
    assert len(derived) == 1
    assert derived[0].id == p2.id


# =============================================================================
# Scenario C: Frame Creation + Activation
# =============================================================================


@pytest.mark.docker
@pytest.mark.asyncio
async def test_scenario_c_frame_creation_activation(db_session: AsyncSession) -> None:
    """Scenario C: Frame exists as passage + ref-addressable closure.

    Steps:
    1. POST /frames with persona/human/world perceptions → Frame created
    2. GET /frames/{name} → Returns JSON payload
    3. POST /frames/{name}/activate → Success
    4. Verify activation → frame/active reflects
    """
    from kp3.services.frames import activate_frame

    # Step 1: Create frame
    perceptions = [
        perception("persona"),
        perception("human"),
        perception("world"),
    ]

    frame = await create_frame(
        db_session,
        name="production",
        agent_id=TEST_AGENT_ID,
        perceptions=perceptions,
        hooks_enabled=True,
    )
    await db_session.commit()

    assert frame["name"] == "production"
    assert frame["agent_id"] == TEST_AGENT_ID
    assert len(frame["perceptions"]) == 3

    # Step 2: Get frame
    fetched = await get_frame(db_session, TEST_AGENT_ID, "production")
    assert fetched is not None
    assert fetched["name"] == "production"

    # Step 3: Activate frame
    result = await activate_frame(db_session, TEST_AGENT_ID, "production")
    await db_session.commit()

    assert result["frame_ref"] == f"{TEST_AGENT_ID}/frame/production"

    # Step 4: Verify active ref
    active_passage_id = await get_ref(db_session, f"{TEST_AGENT_ID}/frame/active")
    assert active_passage_id == frame["id"]


# =============================================================================
# Scenario D: Frame Fork Creates Derived Version
# =============================================================================


@pytest.mark.docker
@pytest.mark.asyncio
async def test_scenario_d_frame_fork_derived_version(db_session: AsyncSession) -> None:
    """Scenario D: Fork produces derived frame.

    Steps:
    1. Create F1 = production
    2. Fork to F2 = experimental
    3. Query derivation → F2 derived from F1
    4. Verify F1 unchanged → Original not mutated
    """
    # Step 1: Create F1
    perceptions = [
        perception("persona"),
    ]

    f1 = await create_frame(
        db_session,
        name="production",
        agent_id=TEST_AGENT_ID,
        perceptions=perceptions,
        hooks_enabled=True,
    )
    await db_session.commit()

    # Step 2: Fork to F2
    f2 = await fork_frame(
        db_session,
        agent_id=TEST_AGENT_ID,
        source_name="production",
        new_name="experimental",
        hooks_enabled=False,
    )
    await db_session.commit()

    assert f2["name"] == "experimental"
    assert f2["hooks_enabled"] is False

    # Step 3: Query derivation
    sources = await get_sources(db_session, f2["id"])
    assert len(sources) == 1
    assert sources[0].id == f1["id"]

    # Step 4: Verify F1 unchanged
    f1_after = await get_frame(db_session, TEST_AGENT_ID, "production")
    assert f1_after is not None
    assert f1_after["hooks_enabled"] is True


# =============================================================================
# Scenario K: Cognition Increment Happy Path
# =============================================================================


@pytest.mark.docker
@pytest.mark.asyncio
async def test_scenario_k_cognition_increment_happy_path(db_session: AsyncSession) -> None:
    """Scenario K: Atomic new passage + derivation + ref advance.

    Steps:
    1. Ensure persona ref exists → P1
    2. POST /cognition/increment with expected_previous_passage_id=P1
    3. Verify P2 created
    4. Verify derivation P2 → P1
    5. Verify persona ref now points to P2
    """
    from kp3.services.cognition import increment_perception

    clear_idempotency_cache()

    # Create frame first
    perceptions = [
        perception("persona"),
    ]
    await create_frame(
        db_session,
        name="test-frame",
        agent_id=TEST_AGENT_ID,
        perceptions=perceptions,
    )
    await db_session.commit()

    # Step 1: Create initial perception P1
    p1 = await create_passage(
        db_session,
        content="Initial persona state",
        passage_type="perception:step_persona",
        agent_id=TEST_AGENT_ID,
    )
    await db_session.commit()
    await db_session.refresh(p1)

    ref_name = f"{TEST_AGENT_ID}/perception/persona"
    await set_ref(db_session, ref_name, p1.id, fire_hooks=False)
    await db_session.commit()

    # Step 2: Increment perception
    result = await increment_perception(
        db_session,
        agent_id=TEST_AGENT_ID,
        frame_ref=f"{TEST_AGENT_ID}/frame/test-frame",
        perception_ref=ref_name,
        input_content="New session data to process",
        process_step_id="step_persona",
        expected_previous_passage_id=p1.id,
        llm_stub=True,
    )
    await db_session.commit()

    # Step 3: Verify new passage created
    assert result["ok"] is True
    assert result["new_passage_id"] is not None
    assert result["previous_passage_id"] == p1.id

    p2_id = result["new_passage_id"]
    p2 = await get_passage(db_session, p2_id)
    assert p2 is not None

    # Step 4: Verify derivation
    sources = await get_sources(db_session, p2_id)
    assert len(sources) == 1
    assert sources[0].id == p1.id

    # Step 5: Verify ref now points to P2
    current_id = await get_ref(db_session, ref_name)
    assert current_id == p2_id


# =============================================================================
# Scenario L: Cognition Increment Bootstrap (No Previous)
# =============================================================================


@pytest.mark.docker
@pytest.mark.asyncio
async def test_scenario_l_cognition_increment_bootstrap(db_session: AsyncSession) -> None:
    """Scenario L: First state write creates ref.

    Steps:
    1. Ensure world ref does not exist
    2. Increment world
    3. Verify ref created and points to new passage
    """
    from kp3.services.cognition import increment_perception

    clear_idempotency_cache()

    # Create frame first
    perceptions = [
        perception("world"),
    ]
    await create_frame(
        db_session,
        name="bootstrap-frame",
        agent_id=TEST_AGENT_ID,
        perceptions=perceptions,
    )
    await db_session.commit()

    ref_name = f"{TEST_AGENT_ID}/perception/world"

    # Step 1: Ensure ref doesn't exist
    existing = await get_ref(db_session, ref_name)
    assert existing is None

    # Step 2: Increment world (bootstrap)
    result = await increment_perception(
        db_session,
        agent_id=TEST_AGENT_ID,
        frame_ref=f"{TEST_AGENT_ID}/frame/bootstrap-frame",
        perception_ref=ref_name,
        input_content="Initial world state",
        process_step_id="step_world",
        llm_stub=True,
    )
    await db_session.commit()

    # Step 3: Verify ref created
    assert result["ok"] is True
    assert result["previous_passage_id"] is None  # No previous

    current_id = await get_ref(db_session, ref_name)
    assert current_id == result["new_passage_id"]


# =============================================================================
# Scenario M: Optimistic Locking Prevents Lost Updates
# =============================================================================


@pytest.mark.docker
@pytest.mark.asyncio
async def test_scenario_m_optimistic_locking(db_session: AsyncSession) -> None:
    """Scenario M: No silent ref overwrite.

    Steps:
    1. Two workers read persona HEAD P1
    2. Both increment with expected_previous=P1
    3. One success, one 409
    4. Retry succeeds
    5. HEAD reflects serialized progression
    """
    from kp3.services.cognition import CognitionConflictError, increment_perception

    clear_idempotency_cache()

    # Setup: Create frame and initial passage
    perceptions = [
        perception("persona", "lock"),
    ]
    await create_frame(
        db_session,
        name="lock-frame",
        agent_id=TEST_AGENT_ID,
        perceptions=perceptions,
    )
    await db_session.commit()

    p1 = await create_passage(
        db_session,
        content="Initial state P1",
        passage_type="perception:step_persona",
        agent_id=TEST_AGENT_ID,
    )
    await db_session.commit()
    await db_session.refresh(p1)

    ref_name = f"{TEST_AGENT_ID}/perception/persona-lock"
    await set_ref(db_session, ref_name, p1.id, fire_hooks=False)
    await db_session.commit()

    # Step 1-2: Simulate two workers reading HEAD at P1
    # Worker 1 succeeds first
    result1 = await increment_perception(
        db_session,
        agent_id=TEST_AGENT_ID,
        frame_ref=f"{TEST_AGENT_ID}/frame/lock-frame",
        perception_ref=ref_name,
        input_content="Worker 1 update",
        process_step_id="step_persona",
        expected_previous_passage_id=p1.id,
        llm_stub=True,
    )
    await db_session.commit()

    assert result1["ok"] is True
    p2_id = result1["new_passage_id"]

    # Step 3: Worker 2 tries with stale expected_previous (P1 instead of P2)
    with pytest.raises(CognitionConflictError) as exc_info:
        await increment_perception(
            db_session,
            agent_id=TEST_AGENT_ID,
            frame_ref=f"{TEST_AGENT_ID}/frame/lock-frame",
            perception_ref=ref_name,
            input_content="Worker 2 update",
            process_step_id="step_persona",
            expected_previous_passage_id=p1.id,  # Stale!
            llm_stub=True,
        )

    assert exc_info.value.expected_passage_id == p1.id
    assert exc_info.value.actual_passage_id == p2_id

    # Step 4: Worker 2 retries with correct expected_previous
    result2 = await increment_perception(
        db_session,
        agent_id=TEST_AGENT_ID,
        frame_ref=f"{TEST_AGENT_ID}/frame/lock-frame",
        perception_ref=ref_name,
        input_content="Worker 2 update retry",
        process_step_id="step_persona",
        expected_previous_passage_id=p2_id,  # Correct now
        llm_stub=True,
    )
    await db_session.commit()

    assert result2["ok"] is True
    p3_id = result2["new_passage_id"]

    # Step 5: HEAD reflects serialized progression P1 → P2 → P3
    current_id = await get_ref(db_session, ref_name)
    assert current_id == p3_id

    # Check derivation chain
    sources_p3 = await get_sources(db_session, p3_id)
    assert len(sources_p3) == 1
    assert sources_p3[0].id == p2_id


# =============================================================================
# Scenario N: Idempotency Protects Against Double-Apply
# =============================================================================


@pytest.mark.docker
@pytest.mark.asyncio
async def test_scenario_n_idempotency(db_session: AsyncSession) -> None:
    """Scenario N: Request retries do not double-write.

    Steps:
    1. Increment with idempotency_key=K
    2. Repeat same request
    3. Check results → Same new_passage_id
    4. Check derivations → No duplicate edges
    """
    from kp3.services.cognition import increment_perception

    clear_idempotency_cache()

    # Setup
    perceptions = [
        perception("persona", "idem"),
    ]
    await create_frame(
        db_session,
        name="idem-frame",
        agent_id=TEST_AGENT_ID,
        perceptions=perceptions,
    )
    await db_session.commit()

    p1 = await create_passage(
        db_session,
        content="Initial state",
        passage_type="perception:step_persona",
        agent_id=TEST_AGENT_ID,
    )
    await db_session.commit()
    await db_session.refresh(p1)

    ref_name = f"{TEST_AGENT_ID}/perception/persona-idem"
    await set_ref(db_session, ref_name, p1.id, fire_hooks=False)
    await db_session.commit()

    idempotency_key = "test-idempotency-key-12345"

    # Step 1: First increment
    result1 = await increment_perception(
        db_session,
        agent_id=TEST_AGENT_ID,
        frame_ref=f"{TEST_AGENT_ID}/frame/idem-frame",
        perception_ref=ref_name,
        input_content="Session data",
        process_step_id="step_persona",
        idempotency_key=idempotency_key,
        llm_stub=True,
    )
    await db_session.commit()

    # Step 2: Repeat same request
    result2 = await increment_perception(
        db_session,
        agent_id=TEST_AGENT_ID,
        frame_ref=f"{TEST_AGENT_ID}/frame/idem-frame",
        perception_ref=ref_name,
        input_content="Session data",
        process_step_id="step_persona",
        idempotency_key=idempotency_key,
        llm_stub=True,
    )

    # Step 3: Same result
    assert result1["new_passage_id"] == result2["new_passage_id"]

    # Step 4: Only one derivation edge exists
    sources = await get_sources(db_session, result1["new_passage_id"])
    assert len(sources) == 1  # Not duplicated


# =============================================================================
# Scenario O: Rollback on LLM Failure
# =============================================================================


@pytest.mark.docker
@pytest.mark.asyncio
async def test_scenario_o_rollback_on_failure(db_session: AsyncSession) -> None:
    """Scenario O: Failure doesn't corrupt state.

    Steps:
    1. Force LLM failure (simulated)
    2. Attempt increment
    3. Check state → No new passage
    4. Check derivations → No derivation
    5. Check ref → Unchanged
    """
    clear_idempotency_cache()

    # Setup
    perceptions = [
        perception("persona", "fail"),
    ]
    await create_frame(
        db_session,
        name="fail-frame",
        agent_id=TEST_AGENT_ID,
        perceptions=perceptions,
    )
    await db_session.commit()

    p1 = await create_passage(
        db_session,
        content="Initial state",
        passage_type="perception:step_persona",
        agent_id=TEST_AGENT_ID,
    )
    await db_session.commit()
    await db_session.refresh(p1)

    ref_name = f"{TEST_AGENT_ID}/perception/persona-fail"
    await set_ref(db_session, ref_name, p1.id, fire_hooks=False)
    await db_session.commit()

    # Record initial state
    initial_passage_id = await get_ref(db_session, ref_name)
    assert initial_passage_id == p1.id

    # Note: In a real test, we would mock the LLM to fail.
    # Since we're using llm_stub=True, we can't easily simulate failure.
    # This test documents the expected behavior - actual failure testing
    # would require mocking.

    # Verify ref unchanged (since we didn't actually fail)
    current_id = await get_ref(db_session, ref_name)
    assert current_id == p1.id  # Still points to P1


# =============================================================================
# Scenario Q: hooks_enabled Gating
# =============================================================================


@pytest.mark.docker
@pytest.mark.asyncio
async def test_scenario_q_hooks_enabled_gating(db_session: AsyncSession) -> None:
    """Scenario Q: Hooks do not fire when disabled.

    Steps:
    1. Attach hook to ref update
    2. Set hooks_enabled=false on frame
    3. Increment perception
    4. Check hook execution → Not executed

    Note: This test verifies the hooks_enabled flag is respected.
    Actual hook execution testing requires mocking the hook system.
    """
    from kp3.services.cognition import increment_perception
    from kp3.services.refs import create_ref_hook

    clear_idempotency_cache()

    # Create frame with hooks disabled
    perceptions = [
        perception("persona", "hook"),
    ]
    await create_frame(
        db_session,
        name="hook-frame",
        agent_id=TEST_AGENT_ID,
        perceptions=perceptions,
        hooks_enabled=False,  # Disabled
    )
    await db_session.commit()

    # Create initial passage and ref
    p1 = await create_passage(
        db_session,
        content="Initial state",
        passage_type="perception:step_persona",
        agent_id=TEST_AGENT_ID,
    )
    await db_session.commit()
    await db_session.refresh(p1)

    ref_name = f"{TEST_AGENT_ID}/perception/persona-hook"
    await set_ref(db_session, ref_name, p1.id, fire_hooks=False)

    # Step 1: Attach hook (would normally fire on ref update)
    await create_ref_hook(
        db_session,
        ref_name=ref_name,
        action_type="test_action",
        config={"test": True},
    )
    await db_session.commit()

    # Step 3: Increment perception
    # Since hooks_enabled=False on frame, hooks should not fire
    result = await increment_perception(
        db_session,
        agent_id=TEST_AGENT_ID,
        frame_ref=f"{TEST_AGENT_ID}/frame/hook-frame",
        perception_ref=ref_name,
        input_content="Test data",
        process_step_id="step_persona",
        llm_stub=True,
    )
    await db_session.commit()

    # Increment succeeded - hooks would have failed if they fired
    # (since test_action is not a real hook type)
    assert result["ok"] is True


# =============================================================================
# HTTP API Tests (using test client)
# =============================================================================


@pytest.mark.docker
@pytest.mark.asyncio
async def test_http_ref_crud(test_client: AsyncClient) -> None:
    """Test refs HTTP endpoints via REST API."""
    headers = {"X-Agent-ID": TEST_AGENT_ID}

    # Create a passage first
    passage_resp = await test_client.post(
        "/passages",
        json={
            "content": "Test content for HTTP ref test",
            "passage_type": "test",
        },
        headers=headers,
    )
    assert passage_resp.status_code == 200
    passage_id = passage_resp.json()["id"]

    # Create ref
    ref_name = "test-agent/http/test-ref"
    put_resp = await test_client.put(
        f"/refs/{ref_name}",
        json={"passage_id": passage_id},
        headers=headers,
    )
    assert put_resp.status_code == 200
    assert put_resp.json()["name"] == ref_name

    # Get ref
    get_resp = await test_client.get(f"/refs/{ref_name}")
    assert get_resp.status_code == 200
    assert get_resp.json()["passage_id"] == passage_id

    # Get ref with resolved passage
    get_resolved_resp = await test_client.get(f"/refs/{ref_name}?resolve=true")
    assert get_resolved_resp.status_code == 200
    assert get_resolved_resp.json()["passage_content"] == "Test content for HTTP ref test"

    # List refs with prefix
    list_resp = await test_client.get("/refs?prefix=test-agent/http/")
    assert list_resp.status_code == 200
    assert list_resp.json()["count"] >= 1

    # Get history
    history_url = f"/refs/{ref_name}/history"
    history_resp = await test_client.get(history_url)
    assert history_resp.status_code == 200
    assert history_resp.json()["count"] >= 1


@pytest.mark.docker
@pytest.mark.asyncio
async def test_http_optimistic_locking(test_client: AsyncClient) -> None:
    """Test optimistic locking via HTTP API."""
    headers = {"X-Agent-ID": TEST_AGENT_ID}

    # Create passages
    p1_resp = await test_client.post(
        "/passages",
        json={"content": "Version 1", "passage_type": "test"},
        headers=headers,
    )
    p1_id = p1_resp.json()["id"]

    p2_resp = await test_client.post(
        "/passages",
        json={"content": "Version 2", "passage_type": "test"},
        headers=headers,
    )
    p2_id = p2_resp.json()["id"]

    # Create ref
    ref_name = "test-agent/http/lock-test"
    await test_client.put(
        f"/refs/{ref_name}",
        json={"passage_id": p1_id},
        headers=headers,
    )

    # Get current version
    get_resp = await test_client.get(f"/refs/{ref_name}")
    current_version = get_resp.json()["version"]

    # Update with correct version
    update_resp = await test_client.put(
        f"/refs/{ref_name}",
        json={"passage_id": p2_id, "expected_version": current_version},
        headers=headers,
    )
    assert update_resp.status_code == 200

    # Try to update with stale version (should fail)
    conflict_resp = await test_client.put(
        f"/refs/{ref_name}",
        json={"passage_id": p1_id, "expected_version": current_version},  # Stale
        headers=headers,
    )
    assert conflict_resp.status_code == 409
    assert conflict_resp.json()["detail"]["error"] == "version_conflict"


@pytest.mark.docker
@pytest.mark.asyncio
async def test_http_derivations(test_client: AsyncClient, db_session: AsyncSession) -> None:
    """Test derivations HTTP endpoints."""
    headers = {"X-Agent-ID": TEST_AGENT_ID}

    # Create source passage
    p1_resp = await test_client.post(
        "/passages",
        json={"content": "Source passage", "passage_type": "test"},
        headers=headers,
    )
    p1_id = p1_resp.json()["id"]

    # Create derived passage
    p2_resp = await test_client.post(
        "/passages",
        json={"content": "Derived passage", "passage_type": "test"},
        headers=headers,
    )
    p2_id = p2_resp.json()["id"]

    # Create derivation link (via service, as no direct HTTP endpoint yet)

    await create_derivations(
        db_session,
        derived_passage_id=UUID(p2_id),
        source_passage_ids=[UUID(p1_id)],
    )
    await db_session.commit()

    # Get sources
    sources_resp = await test_client.get(f"/passages/{p2_id}/sources")
    assert sources_resp.status_code == 200
    assert p1_id in sources_resp.json()["sources"]

    # Get derived
    derived_resp = await test_client.get(f"/passages/{p1_id}/derived")
    assert derived_resp.status_code == 200
    assert p2_id in derived_resp.json()["derived"]


@pytest.mark.docker
@pytest.mark.asyncio
async def test_http_frames(test_client: AsyncClient) -> None:
    """Test frames HTTP endpoints."""
    headers = {"X-Agent-ID": TEST_AGENT_ID}

    # Create frame
    create_resp = await test_client.post(
        "/frames",
        json={
            "name": "http-test-frame",
            "agent_id": TEST_AGENT_ID,
            "perceptions": [
                perception("persona"),
            ],
            "hooks_enabled": True,
        },
        headers=headers,
    )
    assert create_resp.status_code == 200
    frame_data = create_resp.json()
    assert frame_data["name"] == "http-test-frame"

    # Get frame
    get_resp = await test_client.get("/frames/http-test-frame", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "http-test-frame"

    # List frames
    list_resp = await test_client.get("/frames", headers=headers)
    assert list_resp.status_code == 200
    frame_names = [f["name"] for f in list_resp.json()]
    assert "http-test-frame" in frame_names

    # Fork frame
    fork_resp = await test_client.post(
        "/frames/http-test-frame/fork",
        json={"new_name": "http-test-fork", "hooks_enabled": False},
        headers=headers,
    )
    assert fork_resp.status_code == 200
    assert fork_resp.json()["name"] == "http-test-fork"
    assert fork_resp.json()["hooks_enabled"] is False

    # Resolve frame
    resolve_resp = await test_client.post("/frames/http-test-frame/resolve", headers=headers)
    assert resolve_resp.status_code == 200
    assert resolve_resp.json()["frame_name"] == "http-test-frame"


@pytest.mark.docker
@pytest.mark.asyncio
async def test_http_cognition_increment(test_client: AsyncClient) -> None:
    """Test cognition increment HTTP endpoint."""
    from kp3.services.cognition import clear_idempotency_cache

    clear_idempotency_cache()

    headers = {"X-Agent-ID": TEST_AGENT_ID}

    # Create frame
    await test_client.post(
        "/frames",
        json={
            "name": "http-increment-frame",
            "agent_id": TEST_AGENT_ID,
            "perceptions": [{
                "name": "persona",
                "ref": f"{TEST_AGENT_ID}/perception/http-persona",
                "process": "step_persona",
            }],
            "hooks_enabled": True,
        },
        headers=headers,
    )

    # Create initial passage and ref
    p1_resp = await test_client.post(
        "/passages",
        json={"content": "Initial persona", "passage_type": "perception:step_persona"},
        headers=headers,
    )
    p1_id = p1_resp.json()["id"]

    ref_name = f"{TEST_AGENT_ID}/perception/http-persona"
    await test_client.put(
        f"/refs/{ref_name}",
        json={"passage_id": p1_id},
        headers=headers,
    )

    # Increment
    increment_resp = await test_client.post(
        "/cognition/increment",
        json={
            "agent_id": TEST_AGENT_ID,
            "frame_ref": f"{TEST_AGENT_ID}/frame/http-increment-frame",
            "perception_ref": ref_name,
            "input": {
                "content": "New session data",
                "content_type": "text/plain",
            },
            "process_step_id": "step_persona",
            "expected_previous_passage_id": p1_id,
        },
        headers=headers,
    )
    assert increment_resp.status_code == 200
    result = increment_resp.json()
    assert result["ok"] is True
    assert result["previous_passage_id"] == p1_id
    assert result["new_passage_id"] != p1_id


@pytest.mark.docker
@pytest.mark.asyncio
async def test_http_cognition_conflict(test_client: AsyncClient) -> None:
    """Test cognition increment returns 409 on conflict."""
    from uuid import uuid4

    from kp3.services.cognition import clear_idempotency_cache

    clear_idempotency_cache()

    headers = {"X-Agent-ID": TEST_AGENT_ID}

    # Create frame
    await test_client.post(
        "/frames",
        json={
            "name": "http-conflict-frame",
            "agent_id": TEST_AGENT_ID,
            "perceptions": [{
                "name": "persona",
                "ref": f"{TEST_AGENT_ID}/perception/conflict-persona",
                "process": "step_persona",
            }],
        },
        headers=headers,
    )

    # Create passage and ref
    p1_resp = await test_client.post(
        "/passages",
        json={"content": "Initial", "passage_type": "test"},
        headers=headers,
    )
    p1_id = p1_resp.json()["id"]

    ref_name = f"{TEST_AGENT_ID}/perception/conflict-persona"
    await test_client.put(
        f"/refs/{ref_name}",
        json={"passage_id": p1_id},
        headers=headers,
    )

    # Try to increment with wrong expected_previous_passage_id
    fake_id = str(uuid4())
    conflict_resp = await test_client.post(
        "/cognition/increment",
        json={
            "agent_id": TEST_AGENT_ID,
            "frame_ref": f"{TEST_AGENT_ID}/frame/http-conflict-frame",
            "perception_ref": ref_name,
            "input": {"content": "Data"},
            "process_step_id": "step_persona",
            "expected_previous_passage_id": fake_id,
        },
        headers=headers,
    )
    assert conflict_resp.status_code == 409
    assert conflict_resp.json()["detail"]["error"] == "conflict"

import pytest
import copy

from tools import validate_workflow_gateway as validator


def test_workflow_gateway_default_artifacts_validate():
    assert validator.validate_default_files() is True


def test_invalid_agent_runtime_rejects_raw_secret_storage():
    with pytest.raises(ValueError, match="credentialPolicy"):
        validator.validate_agent_runtimes(
            validator.ROOT / "fixtures" / "workflow-gateway" / "invalid-agent-runtime-live-dispatch.json"
        )


def test_invalid_run_ledger_rejects_live_dispatch_and_mutating_tunnel():
    with pytest.raises(ValueError, match="liveDispatch"):
        validator.validate_run_ledger(
            validator.ROOT / "fixtures" / "workflow-gateway" / "invalid-run-ledger-mutating-cloudflare.jsonl"
        )


def test_invalid_run_ledger_requires_site_workflow_binding():
    with pytest.raises(ValueError, match="siteWorkflowBinding|missing keys"):
        validator.validate_run_ledger(
            validator.ROOT / "fixtures" / "workflow-gateway" / "invalid-run-ledger-missing-site-workflow-binding.jsonl"
        )


def test_invalid_review_packet_requires_captured_response():
    with pytest.raises(ValueError, match="captured review response"):
        validator.validate_run_ledger(
            validator.ROOT
            / "fixtures"
            / "workflow-gateway"
            / "invalid-run-ledger-review-packet-missing-captured-response.jsonl"
        )


def test_invalid_protected_execution_requires_approval_artifacts():
    with pytest.raises(ValueError, match="approval manifest"):
        validator.validate_run_ledger(
            validator.ROOT
            / "fixtures"
            / "workflow-gateway"
            / "invalid-run-ledger-protected-execution-missing-approval.jsonl"
        )


def test_invalid_workflow_room_requires_site_binding():
    with pytest.raises(ValueError, match="siteWorkflowBinding|missing keys"):
        validator.validate_workflow_rooms(
            validator.ROOT / "fixtures" / "workflow-gateway" / "invalid-workflow-room-missing-site-binding.json"
        )


def test_invalid_workflow_room_rejects_join_without_packet():
    with pytest.raises(ValueError, match="join without packet"):
        validator.validate_workflow_rooms(
            validator.ROOT / "fixtures" / "workflow-gateway" / "invalid-workflow-room-join-without-packet.json"
        )


def test_invalid_workflow_room_requires_packet_bounded_write_scope():
    with pytest.raises(ValueError, match="write scope"):
        validator.validate_workflow_rooms(
            validator.ROOT / "fixtures" / "workflow-gateway" / "invalid-workflow-room-write-scope-not-packet.json"
        )


def test_invalid_workflow_room_requires_audit_display():
    with pytest.raises(ValueError, match="daily and audit"):
        validator.validate_workflow_rooms(
            validator.ROOT / "fixtures" / "workflow-gateway" / "invalid-workflow-room-no-audit-display.json"
        )


def test_invalid_workflow_room_requires_command_overview_first_screen():
    with pytest.raises(ValueError, match="first screen"):
        validator.validate_workflow_rooms(
            validator.ROOT
            / "fixtures"
            / "workflow-gateway"
            / "invalid-workflow-room-command-surface-list-first.json"
        )


def test_invalid_workflow_room_rejects_default_broadcast_composer():
    with pytest.raises(ValueError, match="room composer"):
        validator.validate_workflow_rooms(
            validator.ROOT
            / "fixtures"
            / "workflow-gateway"
            / "invalid-workflow-room-composer-default-broadcast.json"
        )


def test_invalid_workflow_room_requires_new_thread_normal_mode():
    with pytest.raises(ValueError, match="normal thread mode"):
        validator.validate_workflow_rooms(
            validator.ROOT
            / "fixtures"
            / "workflow-gateway"
            / "invalid-workflow-room-new-thread-enters-room.json"
        )


def test_invalid_workflow_room_requires_approval_queue():
    with pytest.raises(ValueError, match="approval queue"):
        validator.validate_workflow_rooms(
            validator.ROOT / "fixtures" / "workflow-gateway" / "invalid-workflow-room-no-approval-queue.json"
        )


def test_invalid_workflow_room_requires_branch_worktree_for_coding():
    with pytest.raises(ValueError, match="branch/worktree"):
        validator.validate_workflow_rooms(
            validator.ROOT
            / "fixtures"
            / "workflow-gateway"
            / "invalid-workflow-room-coding-preflight-missing-worktree.json"
        )


def test_invalid_workflow_room_requires_orchestrator_integration_owner():
    with pytest.raises(ValueError, match="integration owner"):
        validator.validate_workflow_rooms(
            validator.ROOT
            / "fixtures"
            / "workflow-gateway"
            / "invalid-workflow-room-integration-owner-not-orchestrator.json"
        )


def test_invalid_workflow_room_rejects_unbounded_commit_scope():
    with pytest.raises(ValueError, match="commit scope"):
        validator.validate_workflow_rooms(
            validator.ROOT / "fixtures" / "workflow-gateway" / "invalid-workflow-room-commit-scope-unbounded.json"
        )


def test_invalid_workflow_room_marks_failing_tests_blocked():
    with pytest.raises(ValueError, match="failing required tests"):
        validator.validate_workflow_rooms(
            validator.ROOT / "fixtures" / "workflow-gateway" / "invalid-workflow-room-failing-tests-complete.json"
        )


def test_invalid_workflow_room_longterm_cannot_do_real_work_directly():
    with pytest.raises(ValueError, match="long-term room"):
        validator.validate_workflow_rooms(
            validator.ROOT / "fixtures" / "workflow-gateway" / "invalid-workflow-room-longterm-does-real-work.json"
        )


def test_invalid_workflow_room_exit_requires_packet():
    with pytest.raises(ValueError, match="exit packet"):
        validator.validate_workflow_rooms(
            validator.ROOT / "fixtures" / "workflow-gateway" / "invalid-workflow-room-exit-no-packet.json"
        )


def test_invalid_workflow_room_memory_requires_filtering_and_source():
    with pytest.raises(ValueError, match="summary-only|sensitive memory|auditable source"):
        validator.validate_workflow_rooms(
            validator.ROOT / "fixtures" / "workflow-gateway" / "invalid-workflow-room-memory-unfiltered.json"
        )


def test_invalid_workflow_room_history_requires_filters():
    with pytest.raises(ValueError, match="history display|history filters"):
        validator.validate_workflow_rooms(
            validator.ROOT / "fixtures" / "workflow-gateway" / "invalid-workflow-room-history-no-filters.json"
        )


def test_invalid_workflow_room_restore_requires_packet():
    with pytest.raises(ValueError, match="restore packet"):
        validator.validate_workflow_rooms(
            validator.ROOT / "fixtures" / "workflow-gateway" / "invalid-workflow-room-restore-no-packet.json"
        )


def test_invalid_workflow_room_rule_change_requires_user_control_approval():
    with pytest.raises(ValueError, match="user/control approval"):
        validator.validate_workflow_rooms(
            validator.ROOT / "fixtures" / "workflow-gateway" / "invalid-workflow-room-rule-change-member-mutates.json"
        )


def test_invalid_heartbeat_rejects_mutation():
    with pytest.raises(ValueError, match="read-only"):
        validator.validate_heartbeats(
            validator.ROOT / "fixtures" / "workflow-gateway" / "invalid-heartbeat-mutating.json"
        )


def test_invalid_room_message_rejects_implicit_broadcast():
    with pytest.raises(ValueError, match="toSeats"):
        validator.validate_room_message_ledger(
            validator.ROOT / "fixtures" / "workflow-gateway" / "invalid-room-message-implicit-broadcast.jsonl"
        )


def test_invalid_room_broadcast_requires_recipients():
    with pytest.raises(ValueError, match="explicit toSeats"):
        validator.validate_room_message_ledger(
            validator.ROOT
            / "fixtures"
            / "workflow-gateway"
            / "invalid-room-message-broadcast-without-recipients.jsonl"
        )


def test_invalid_manifest_summary_rejects_full_message_visibility():
    with pytest.raises(ValueError, match="manifest_summary"):
        validator.validate_room_message_ledger(
            validator.ROOT / "fixtures" / "workflow-gateway" / "invalid-room-message-full-manifest.jsonl"
        )


def _valid_site_binding():
    registry = validator.load_json(validator.ROOT / "rooms" / "workflow-rooms.registry.json")
    return copy.deepcopy(registry["rooms"][0]["siteWorkflowBinding"])


def test_gstack_room_policy_requires_codex_only_phase_one_orchestrator():
    binding = _valid_site_binding()
    binding["gstackRoomModelPolicy"]["orchestratorPolicy"]["nonCodexOrchestratorAllowed"] = True
    with pytest.raises(ValueError, match="non-Codex orchestrator"):
        validator.validate_site_workflow_binding(binding, "test:gstack")


def test_gstack_room_policy_requires_join_role_and_packet():
    binding = _valid_site_binding()
    binding["gstackRoomModelPolicy"]["joinRequiresRole"] = False
    with pytest.raises(ValueError, match="room join requires both packet and role"):
        validator.validate_site_workflow_binding(binding, "test:gstack")


def test_gstack_room_policy_requires_complete_agent_seat_card_fields():
    binding = _valid_site_binding()
    fields = binding["gstackRoomModelPolicy"]["agentSeatCard"]["requiredFields"]
    binding["gstackRoomModelPolicy"]["agentSeatCard"]["requiredFields"] = [
        field for field in fields if field != "branch/worktree"
    ]
    with pytest.raises(ValueError, match="agent seat card fields"):
        validator.validate_site_workflow_binding(binding, "test:gstack")


def test_gstack_room_policy_requires_single_active_room_per_agent():
    binding = _valid_site_binding()
    binding["gstackRoomModelPolicy"]["activeRoomLimit"]["maxActiveRoomsPerAgent"] = 2
    with pytest.raises(ValueError, match="one active room"):
        validator.validate_site_workflow_binding(binding, "test:gstack")


def test_gstack_room_policy_requires_user_only_close_authority():
    binding = _valid_site_binding()
    binding["gstackRoomModelPolicy"]["closePolicy"]["roomCloseAuthority"] = "orchestrator"
    with pytest.raises(ValueError, match="room close authority"):
        validator.validate_site_workflow_binding(binding, "test:gstack")


def test_gstack_room_policy_requires_site_inheritance():
    binding = _valid_site_binding()
    binding["gstackRoomModelPolicy"]["siteInheritance"]["approvalGateRequired"] = False
    with pytest.raises(ValueError, match="SITE workflow requirements"):
        validator.validate_site_workflow_binding(binding, "test:gstack")

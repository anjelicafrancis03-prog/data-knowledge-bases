import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def fail(message):
    raise ValueError(message)


def load_json(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_jsonl(path):
    entries = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError as exc:
                fail(f"{path}:{line_number}: invalid JSONL: {exc}")
    return entries


def require_keys(obj, keys, label):
    missing = [key for key in keys if key not in obj]
    if missing:
        fail(f"{label}: missing keys: {', '.join(missing)}")


def require_set_contains(values, required, label, noun):
    missing = sorted(set(required) - set(values or []))
    if missing:
        fail(f"{label}: {noun} missing: {', '.join(missing)}")


def validate_agent_runtimes(path):
    doc = load_json(path)
    require_keys(doc, ["schemaVersion", "updatedAt", "boundary", "runtimes"], str(path))
    if doc["schemaVersion"] != "agent-runtimes.registry/v0.1":
        fail(f"{path}: unexpected schemaVersion")
    seen = set()
    for runtime in doc["runtimes"]:
        require_keys(
            runtime,
            [
                "agentRuntimeId",
                "displayName",
                "kind",
                "normalMode",
                "roomMode",
                "agentRelation",
                "permissionClass",
                "status",
                "runtimeAuthority",
                "credentialPolicy",
                "allowedReads",
                "allowedWrites",
                "forbiddenActions",
                "healthCheck",
                "smokeCheck",
                "timeoutPolicy",
                "evidenceParser",
            ],
            f"{path}:runtime",
        )
        runtime_id = runtime["agentRuntimeId"]
        if runtime_id in seen:
            fail(f"{path}: duplicate runtime id {runtime_id}")
        seen.add(runtime_id)
        policy = runtime["credentialPolicy"]
        if policy.get("storesRawSecret") is not False or policy.get("pointerOnly") is not True:
            fail(f"{path}:{runtime_id}: credentialPolicy must be pointer-only and never store raw secrets")
        if runtime["status"] != "reference-only" and runtime["permissionClass"] == "blocked":
            fail(f"{path}:{runtime_id}: blocked runtimes must be reference-only or explicitly blocked")
        if "*" in runtime.get("allowedWrites", []):
            fail(f"{path}:{runtime_id}: wildcard writes are forbidden")
    return True


def validate_run_entry(entry, label):
    require_keys(
        entry,
        [
            "schemaVersion",
            "runId",
            "roomId",
            "status",
            "authorityLayer",
            "truthSource",
            "startedAt",
            "liveDispatch",
            "remoteExposure",
            "siteWorkflowBinding",
            "artifacts",
            "stopCondition",
        ],
        label,
    )
    if entry["schemaVersion"] != "workflow-run-ledger/v0.1":
        fail(f"{label}: unexpected schemaVersion")
    if entry["liveDispatch"] is not False:
        fail(f"{label}: liveDispatch must stay false in L1")
    exposure = entry["remoteExposure"]
    require_keys(exposure, ["cloudflareTunnel", "mutatingRoutesExposed", "authRequired"], label)
    if exposure["mutatingRoutesExposed"] is not False:
        fail(f"{label}: mutating routes must not be exposed through remote ingress")
    if exposure["authRequired"] is not True:
        fail(f"{label}: remote exposure requires auth")
    binding = entry["siteWorkflowBinding"]
    require_keys(
        binding,
        [
            "inheritsSiteWorkflowConsole",
            "normalThreadRulesPreserved",
            "siteDirectCliAllowed",
            "uiIsTruthSource",
            "evidenceLevel",
            "requiredArtifacts",
            "protectedActionPolicy",
        ],
        label,
    )
    if binding["inheritsSiteWorkflowConsole"] is not True:
        fail(f"{label}: room runs must inherit the Site Workflow Console contract")
    if binding["normalThreadRulesPreserved"] is not True:
        fail(f"{label}: room entry must preserve normal thread rules")
    if binding["siteDirectCliAllowed"] is not False:
        fail(f"{label}: site direct CLI must remain blocked")
    if binding["uiIsTruthSource"] is not False:
        fail(f"{label}: UI state cannot be the truth source")
    evidence_levels = {"light_readonly", "review_packet", "full_site_bundle", "protected_execution"}
    evidence_level = binding["evidenceLevel"]
    if evidence_level not in evidence_levels:
        fail(f"{label}: unexpected evidenceLevel")
    required_artifacts = set(binding["requiredArtifacts"])
    minimum_artifacts = {"task packet", "run manifest", "evidence index", "validator report"}
    missing_artifacts = sorted(minimum_artifacts - required_artifacts)
    if missing_artifacts:
        fail(f"{label}: Site workflow binding missing required artifacts: {', '.join(missing_artifacts)}")
    level_requirements = {
        "review_packet": {"review packet", "captured review response", "delivery log", "verification summary"},
        "full_site_bundle": {
            "verification summary",
            "bridge trace or explicit mock-only note",
            "run-id namespaced outputs",
            "protected-action ledger or explicit no-protected-action note",
        },
        "protected_execution": {
            "verification summary",
            "bridge trace or explicit mock-only note",
            "run-id namespaced outputs",
            "protected-action ledger",
            "exact human approval text",
            "approval manifest",
            "approval manifest SHA256 sidecar",
            "approval evidence",
            "hash-bound approved text",
            "changed-file hashes or explicit no-change proof",
        },
    }
    for strict_level, artifacts_for_level in level_requirements.items():
        if evidence_level == strict_level:
            missing_for_level = sorted(artifacts_for_level - required_artifacts)
            if missing_for_level:
                fail(
                    f"{label}: {evidence_level} missing Site workflow artifacts: "
                    + ", ".join(missing_for_level)
                )
    policy = binding["protectedActionPolicy"]
    require_keys(
        policy,
        [
            "approvalManifestRequiredForProtectedActions",
            "hashBoundApprovalRequired",
            "protectedActionLedgerRequired",
        ],
        label,
    )
    if policy["approvalManifestRequiredForProtectedActions"] is not True:
        fail(f"{label}: protected actions require an approval manifest")
    if policy["hashBoundApprovalRequired"] is not True:
        fail(f"{label}: protected actions require hash-bound approval evidence")
    if policy["protectedActionLedgerRequired"] is not True:
        fail(f"{label}: protected-action ledger is required")
    artifacts = entry["artifacts"]
    require_keys(artifacts, ["manifestPath", "evidenceIndexPath", "taskPacketPaths"], label)
    if not entry["stopCondition"]:
        fail(f"{label}: stopCondition is required")
    return True


def validate_run_ledger(path):
    entries = load_jsonl(path)
    if not entries:
        fail(f"{path}: ledger must contain at least one entry")
    for index, entry in enumerate(entries, 1):
        validate_run_entry(entry, f"{path}:entry:{index}")
    return True


def validate_site_workflow_binding(binding, label):
    require_keys(
        binding,
        [
            "status",
            "normalThreadRulesPreserved",
            "siteContractAppliesInRoom",
            "uiIsAuthority",
            "siteDirectCliAllowed",
            "packetGenerationPolicy",
            "roomPermissionPolicy",
            "evidenceDisplayPolicy",
            "commandSurfacePolicy",
            "multiAgentCodingPolicy",
            "roomLifecyclePolicy",
            "requiredRoomRunArtifacts",
            "protectedActionArtifacts",
        ],
        label,
    )
    if binding["status"] != "hard-required":
        fail(f"{label}: Site workflow binding must be hard-required")
    if binding["normalThreadRulesPreserved"] is not True:
        fail(f"{label}: normal thread rules must be preserved")
    if binding["siteContractAppliesInRoom"] is not True:
        fail(f"{label}: Site workflow contract must apply in room")
    if binding["uiIsAuthority"] is not False:
        fail(f"{label}: UI must not be authority")
    if binding["siteDirectCliAllowed"] is not False:
        fail(f"{label}: site direct CLI must remain blocked")
    packet_policy = binding["packetGenerationPolicy"]
    require_keys(
        packet_policy,
        ["mode", "controlValidationRequired", "joinedWithoutPacketAllowed"],
        label,
    )
    if packet_policy["mode"] != "inviter-drafts-control-validates":
        fail(f"{label}: packet generation must be inviter-drafts-control-validates")
    if packet_policy["controlValidationRequired"] is not True:
        fail(f"{label}: control validation is required before room join")
    if packet_policy["joinedWithoutPacketAllowed"] is not False:
        fail(f"{label}: room join without packet is forbidden")
    permission_policy = binding["roomPermissionPolicy"]
    require_keys(
        permission_policy,
        [
            "mode",
            "normalCapabilitiesPreserved",
            "writeScopeSource",
            "executionScopeSource",
            "roomPacketRequiredForWrites",
        ],
        label,
    )
    if permission_policy["mode"] != "normal-capabilities-preserved-room-packet-bounds-writes":
        fail(f"{label}: room permission mode must preserve normal capabilities and bound writes by packet")
    if permission_policy["normalCapabilitiesPreserved"] is not True:
        fail(f"{label}: normal capabilities must be preserved")
    if permission_policy["writeScopeSource"] != "room packet":
        fail(f"{label}: write scope must come from the room packet")
    if permission_policy["executionScopeSource"] != "room packet":
        fail(f"{label}: execution scope must come from the room packet")
    if permission_policy["roomPacketRequiredForWrites"] is not True:
        fail(f"{label}: room packet is required for writes")
    display_policy = binding["evidenceDisplayPolicy"]
    require_keys(
        display_policy,
        [
            "mode",
            "defaultView",
            "dailyShowsFinalConclusion",
            "auditViewRequired",
            "evidenceDrawerRequired",
            "finalConclusionMustLinkEvidence",
        ],
        label,
    )
    if display_policy["mode"] != "daily-and-audit-toggle":
        fail(f"{label}: evidence display must support daily and audit modes")
    if display_policy["defaultView"] != "daily":
        fail(f"{label}: default evidence display view must be daily")
    if display_policy["dailyShowsFinalConclusion"] is not True:
        fail(f"{label}: daily view must show final conclusion")
    if display_policy["auditViewRequired"] is not True:
        fail(f"{label}: audit view is required")
    if display_policy["evidenceDrawerRequired"] is not True:
        fail(f"{label}: evidence drawer is required")
    if display_policy["finalConclusionMustLinkEvidence"] is not True:
        fail(f"{label}: final conclusion must link evidence")
    command_policy = binding["commandSurfacePolicy"]
    has_gstack_policy = "gstackRoomModelPolicy" in binding
    require_keys(
        command_policy,
        [
            "firstScreen",
            "firstScreenPanels",
            "roomComposerDefault",
            "emptyToSeatsMeansNoDelivery",
            "broadcastRequiresExplicitVisibility",
            "threadCardFields",
            "newThreadDefaultMode",
            "roomJoinRequiresExplicitPacket",
            "approvalDisplay",
            "approvalQueueRequired",
        ],
        label,
    )
    if has_gstack_policy:
        if command_policy["firstScreen"] != "control-command-center":
            fail(f"{label}: first screen must be control command center")
        require_keys(command_policy, ["longChatDefault", "ccSeatsAssignTasks"], label)
        if command_policy["longChatDefault"] is not False:
            fail(f"{label}: long chat stream must not be the default first screen")
        if command_policy["ccSeatsAssignTasks"] is not False:
            fail(f"{label}: ccSeats must be visibility only, not task assignment")
        required_panels = {
            "room status",
            "agent seats",
            "current tasks",
            "pending approvals",
            "latest evidence",
            "command actions",
        }
        required_card_fields = {
            "name",
            "role",
            "status",
            "current task",
            "room membership",
            "model/provider",
            "branch/worktree",
            "last activity time",
            "latest evidence time",
        }
    else:
        if command_policy["firstScreen"] != "command-overview":
            fail(f"{label}: first screen must be command overview")
        required_panels = {"thread status", "active room", "pending approvals", "latest evidence"}
        required_card_fields = {
            "status",
            "current task",
            "room membership",
            "model/provider",
            "latest evidence time",
        }
    require_set_contains(command_policy["firstScreenPanels"], required_panels, label, "first screen panels")
    if command_policy["roomComposerDefault"] != "no-recipient-until-selected":
        fail(f"{label}: room composer must default to no recipient until selected")
    if command_policy["emptyToSeatsMeansNoDelivery"] is not True:
        fail(f"{label}: empty toSeats must mean no delivery")
    if command_policy["broadcastRequiresExplicitVisibility"] is not True:
        fail(f"{label}: broadcast requires explicit room_broadcast visibility")
    require_set_contains(command_policy["threadCardFields"], required_card_fields, label, "seat card fields")
    if command_policy["newThreadDefaultMode"] != "normal-thread":
        fail(f"{label}: new threads must start in normal thread mode")
    if command_policy["roomJoinRequiresExplicitPacket"] is not True:
        fail(f"{label}: room join requires an explicit packet")
    if command_policy["approvalDisplay"] != "chat-context-and-approval-queue":
        fail(f"{label}: approvals must appear in chat context and approval queue")
    if command_policy["approvalQueueRequired"] is not True:
        fail(f"{label}: approval queue is required")
    coding_policy = binding["multiAgentCodingPolicy"]
    require_keys(
        coding_policy,
        [
            "orchestratorDefault",
            "userCanDesignateOrchestrator",
            "codingPreflightRequired",
            "integrationOwner",
            "finalMergeAuthority",
            "conflictResolution",
            "commitScope",
            "extraFilesPolicy",
            "failedRequiredTestsStatus",
            "failureEvidenceRequired",
        ],
        label,
    )
    if coding_policy["orchestratorDefault"] != "codex-control":
        fail(f"{label}: orchestrator default must be codex-control")
    if coding_policy["userCanDesignateOrchestrator"] is not True:
        fail(f"{label}: user must be able to designate orchestrator")
    required_coding_preflight = {"task packet", "branch/worktree", "allowed files", "tests to run", "evidence level"}
    missing_preflight = sorted(required_coding_preflight - set(coding_policy["codingPreflightRequired"]))
    if missing_preflight:
        fail(f"{label}: coding preflight missing: {', '.join(missing_preflight)}")
    if coding_policy["integrationOwner"] != "orchestrator":
        fail(f"{label}: integration owner must be orchestrator")
    merge_authority = set(coding_policy["finalMergeAuthority"])
    if not {"user", "control"}.issubset(merge_authority):
        fail(f"{label}: final merge authority must include user and control")
    if has_gstack_policy:
        require_keys(coding_policy, ["agentBranchPattern", "integrationBranchPattern", "agentCanCommitOwnBranch", "agentCannot"], label)
        if coding_policy["agentBranchPattern"] != "room/<room_id>/<agent_id>/<task_slug>":
            fail(f"{label}: agent branch pattern must be room/<room_id>/<agent_id>/<task_slug>")
        if coding_policy["integrationBranchPattern"] != "integration/<room_id>/<task_slug>":
            fail(f"{label}: integration branch pattern must be integration/<room_id>/<task_slug>")
        if coding_policy["agentCanCommitOwnBranch"] is not True:
            fail(f"{label}: coding agents may commit only to their own branch after required checks")
        required_agent_cannot = {
            "merge",
            "push_main",
            "close_mr",
            "close_pr",
            "mark_complete_without_required_evidence",
        }
        require_set_contains(coding_policy["agentCannot"], required_agent_cannot, label, "agent forbidden actions")
    if coding_policy["conflictResolution"] != "authority-layer-then-user-product-then-recorded-technical-decision":
        fail(f"{label}: conflict resolution must follow authority layer")
    if coding_policy["commitScope"] != "packet-allowed-files-only":
        fail(f"{label}: commit scope must be packet-allowed-files-only")
    if coding_policy["extraFilesPolicy"] != "patch-proposal-only":
        fail(f"{label}: extra files must be patch proposal only")
    if coding_policy["failedRequiredTestsStatus"] != "blocked":
        fail(f"{label}: failing required tests must mark task blocked")
    required_failure_evidence = {"failure log", "attempted fixes", "next-step recommendation"}
    missing_failure_evidence = sorted(required_failure_evidence - set(coding_policy["failureEvidenceRequired"]))
    if missing_failure_evidence:
        fail(f"{label}: failure evidence missing: {', '.join(missing_failure_evidence)}")
    lifecycle_policy = binding["roomLifecyclePolicy"]
    require_keys(
        lifecycle_policy,
        [
            "longTermRoomPurpose",
            "realWorkRequiresRunOrTaskPacket",
            "exitPolicy",
            "exitPacketOptions",
            "memoryAccessPolicy",
            "historyDisplay",
            "archiveRestorePolicy",
            "ruleChangePolicy",
        ],
        label,
    )
    if lifecycle_policy["longTermRoomPurpose"] != "members-history-standing-rules-only":
        fail(f"{label}: long-term room must store only members, history, and standing rules")
    if lifecycle_policy["realWorkRequiresRunOrTaskPacket"] is not True:
        fail(f"{label}: real work requires run or task packet")
    if lifecycle_policy["exitPolicy"] != "exit-packet-required":
        fail(f"{label}: room exit requires exit packet")
    required_exit_options = {"resume normal task", "archive", "detached handoff"}
    missing_exit_options = sorted(required_exit_options - set(lifecycle_policy["exitPacketOptions"]))
    if missing_exit_options:
        fail(f"{label}: exit packet options missing: {', '.join(missing_exit_options)}")
    memory_policy = lifecycle_policy["memoryAccessPolicy"]
    require_keys(
        memory_policy,
        [
            "ordinaryMember",
            "orchestrator",
            "control",
            "sensitiveMemoryFilteringRequired",
            "memoryRequiresAuditableSource",
        ],
        label,
    )
    if memory_policy["ordinaryMember"] != "summary-only":
        fail(f"{label}: ordinary member memory access must be summary-only")
    if memory_policy["orchestrator"] != "full-source-chain-with-permission":
        fail(f"{label}: orchestrator memory access requires permissioned full source chain")
    if memory_policy["control"] != "full-source-chain-with-permission":
        fail(f"{label}: control memory access requires permissioned full source chain")
    if memory_policy["sensitiveMemoryFilteringRequired"] is not True:
        fail(f"{label}: sensitive memory filtering is required")
    if memory_policy["memoryRequiresAuditableSource"] is not True:
        fail(f"{label}: memory requires auditable source")
    if has_gstack_policy:
        require_keys(memory_policy, ["authorizedReviewer", "allowedSources"], label)
        if memory_policy["authorizedReviewer"] != "full-source-chain-with-permission":
            fail(f"{label}: authorized reviewer memory access requires permissioned full source chain")
        required_memory_sources = {
            "user_decision",
            "system_rule",
            "task_result",
            "review_verdict",
            "evidence_summary",
            "inferred_note",
        }
        require_set_contains(memory_policy["allowedSources"], required_memory_sources, label, "memory sources")
    history_display = lifecycle_policy["historyDisplay"]
    require_keys(history_display, ["defaultMode", "filtersRequired"], label)
    if history_display["defaultMode"] != "complete-flow-with-filters":
        fail(f"{label}: history display must be complete flow with filters")
    if has_gstack_policy:
        required_history_filters = {"direct", "cc", "broadcast", "approval", "evidence", "task", "system"}
    else:
        required_history_filters = {"direct", "cc", "broadcast", "evidence", "approval"}
    require_set_contains(history_display["filtersRequired"], required_history_filters, label, "history filters")
    restore_policy = lifecycle_policy["archiveRestorePolicy"]
    require_keys(restore_policy, ["restorePacketRequired", "restorePacketFields"], label)
    if restore_policy["restorePacketRequired"] is not True:
        fail(f"{label}: archived room restore requires restore packet")
    required_restore_fields = {"restore reason", "history scope", "current target"}
    missing_restore_fields = sorted(required_restore_fields - set(restore_policy["restorePacketFields"]))
    if missing_restore_fields:
        fail(f"{label}: restore packet fields missing: {', '.join(missing_restore_fields)}")
    rule_policy = lifecycle_policy["ruleChangePolicy"]
    require_keys(rule_policy, ["memberCanPropose", "registryMutationRequiresApprovalBy"], label)
    if rule_policy["memberCanPropose"] is not True:
        fail(f"{label}: members must be able to propose rule changes")
    if not {"user", "control"}.issubset(set(rule_policy["registryMutationRequiresApprovalBy"])):
        fail(f"{label}: registry or contract mutation requires user/control approval")
    room_artifacts = set(binding["requiredRoomRunArtifacts"])
    room_minimum = {
        "room entry packet",
        "task packet",
        "run manifest",
        "evidence index",
        "validator report",
        "verification summary",
        "protected-action ledger",
    }
    missing_room_artifacts = sorted(room_minimum - room_artifacts)
    if missing_room_artifacts:
        fail(f"{label}: missing required Site room artifacts: {', '.join(missing_room_artifacts)}")
    protected_artifacts = set(binding["protectedActionArtifacts"])
    protected_minimum = {
        "exact human approval text",
        "approval manifest",
        "approval manifest SHA256 sidecar",
        "approval evidence",
        "hash-bound approved text",
    }
    missing_protected_artifacts = sorted(protected_minimum - protected_artifacts)
    if missing_protected_artifacts:
        fail(f"{label}: missing protected action artifacts: {', '.join(missing_protected_artifacts)}")
    if not has_gstack_policy:
        fail(f"{label}: gStack room model policy is required")
    validate_gstack_room_model_policy(binding["gstackRoomModelPolicy"], label)
    return True


def validate_gstack_room_model_policy(policy, label):
    require_keys(
        policy,
        [
            "phase",
            "roomFirstScreen",
            "longChatDefault",
            "chatLikeJoinUi",
            "joinIsControlLayerAction",
            "joinAllowedBy",
            "joinRequiresPacket",
            "joinRequiresRole",
            "allowedJoinRoles",
            "dualMode",
            "agentSeatCard",
            "messageDelivery",
            "activeRoomLimit",
            "orchestratorPolicy",
            "domainLeadPolicy",
            "branchPolicy",
            "commitPolicy",
            "testPolicy",
            "clarificationPolicy",
            "permissionPolicy",
            "evidencePolicy",
            "closePolicy",
            "memoryPolicy",
            "chatLogPolicy",
            "siteInheritance",
            "commandButtons",
        ],
        label,
    )
    if policy["phase"] != "phase-1":
        fail(f"{label}: gStack room model phase must be phase-1")
    if policy["roomFirstScreen"] != "control-command-center":
        fail(f"{label}: gStack room first screen must be control command center")
    if policy["longChatDefault"] is not False:
        fail(f"{label}: gStack long chat must not be first-screen default")
    if policy["chatLikeJoinUi"] is not True or policy["joinIsControlLayerAction"] is not True:
        fail(f"{label}: room join must be chat-simple in UI but control-layer in authority")
    require_set_contains(policy["joinAllowedBy"], {"control", "orchestrator"}, label, "join authorities")
    if policy["joinRequiresPacket"] is not True or policy["joinRequiresRole"] is not True:
        fail(f"{label}: room join requires both packet and role")
    require_set_contains(
        policy["allowedJoinRoles"],
        {"orchestrator", "coder", "reviewer", "browser", "search", "ops", "context", "tools", "observer"},
        label,
        "join roles",
    )
    dual_mode = policy["dualMode"]
    require_keys(
        dual_mode,
        [
            "normalThreadRulesPreserved",
            "roomModeRequiresJoinPacket",
            "roomTaskRequiresSeparateTaskPacket",
            "exitRequiresExitPacket",
        ],
        label,
    )
    if any(dual_mode[key] is not True for key in dual_mode):
        fail(f"{label}: dual-mode transition must preserve normal rules and require packets")
    seat_card = policy["agentSeatCard"]
    require_keys(seat_card, ["requiredFields", "allowedStatuses"], label)
    require_set_contains(
        seat_card["requiredFields"],
        {
            "name",
            "role",
            "provider/model",
            "status",
            "current task",
            "branch/worktree",
            "last activity time",
            "latest evidence",
        },
        label,
        "agent seat card fields",
    )
    required_statuses = {"available", "busy", "waiting_user", "blocked", "archived", "offline"}
    if set(seat_card["allowedStatuses"]) != required_statuses:
        fail(f"{label}: agent statuses must be available/busy/waiting_user/blocked/archived/offline")
    delivery = policy["messageDelivery"]
    require_keys(delivery, ["emptyToSeats", "broadcast", "ccSeats", "messageWithoutToSeats"], label)
    if delivery["emptyToSeats"] != "no_delivery":
        fail(f"{label}: empty toSeats must mean no delivery")
    if delivery["broadcast"] != "explicit_room_broadcast_only":
        fail(f"{label}: broadcast must be explicit room_broadcast only")
    if delivery["ccSeats"] != "visibility_only_not_assignment":
        fail(f"{label}: ccSeats must be visibility only")
    if delivery["messageWithoutToSeats"] != "draft_or_log_only":
        fail(f"{label}: message without toSeats must be draft or log only")
    active_limit = policy["activeRoomLimit"]
    require_keys(active_limit, ["maxActiveRoomsPerAgent", "roomChangeRequiresExitPacket", "exitPacketOptions"], label)
    if int(active_limit["maxActiveRoomsPerAgent"]) != 1:
        fail(f"{label}: one agent can be in only one active room")
    if active_limit["roomChangeRequiresExitPacket"] is not True:
        fail(f"{label}: room changes require exit packet")
    require_set_contains(active_limit["exitPacketOptions"], {"resume_normal", "archive", "detached_handoff"}, label, "exit packet options")
    orchestrator = policy["orchestratorPolicy"]
    require_keys(
        orchestrator,
        [
            "phaseOneUpgradeProvider",
            "defaultOrchestrator",
            "userCanDesignateCodexOrchestrator",
            "nonCodexOrchestratorAllowed",
        ],
        label,
    )
    if orchestrator["phaseOneUpgradeProvider"] != "codex_only":
        fail(f"{label}: phase 1 orchestrator upgrade must be Codex-only")
    if orchestrator["defaultOrchestrator"] != "codex-control":
        fail(f"{label}: default orchestrator must be codex-control")
    if orchestrator["userCanDesignateCodexOrchestrator"] is not True:
        fail(f"{label}: user must be able to designate Codex orchestrator")
    if orchestrator["nonCodexOrchestratorAllowed"] is not False:
        fail(f"{label}: non-Codex orchestrator is not allowed in phase 1")
    domain_lead = policy["domainLeadPolicy"]
    require_keys(domain_lead, ["allowed", "underOrchestrator", "cannot"], label)
    if domain_lead["allowed"] is not True or domain_lead["underOrchestrator"] is not True:
        fail(f"{label}: domain lead must be allowed only under orchestrator")
    require_set_contains(domain_lead["cannot"], {"change_authority", "merge", "close_room", "override_packet"}, label, "domain lead forbidden actions")
    branch = policy["branchPolicy"]
    require_keys(
        branch,
        [
            "codingAgentRequiresOwnBranchWorktree",
            "agentBranchPattern",
            "integrationBranchPattern",
            "defaultMrSource",
        ],
        label,
    )
    if branch["codingAgentRequiresOwnBranchWorktree"] is not True:
        fail(f"{label}: coding agents require own branch/worktree")
    if branch["agentBranchPattern"] != "room/<room_id>/<agent_id>/<task_slug>":
        fail(f"{label}: agent branch pattern must be room/<room_id>/<agent_id>/<task_slug>")
    if branch["integrationBranchPattern"] != "integration/<room_id>/<task_slug>":
        fail(f"{label}: integration branch pattern must be integration/<room_id>/<task_slug>")
    if branch["defaultMrSource"] != "integration_branch":
        fail(f"{label}: default MR source must be integration branch")
    commit = policy["commitPolicy"]
    require_keys(commit, ["codingAgentCanCommitOwnBranch", "cannot", "commitRequires"], label)
    if commit["codingAgentCanCommitOwnBranch"] is not True:
        fail(f"{label}: coding agents may commit own branch after required checks")
    require_set_contains(
        commit["cannot"],
        {"merge", "push_main", "close_mr", "close_pr", "mark_complete_without_required_evidence"},
        label,
        "commit forbidden actions",
    )
    require_set_contains(
        commit["commitRequires"],
        {"task_packet.tests_required", "task_packet.evidence_required", "allowed_files_scope"},
        label,
        "commit requirements",
    )
    tests = policy["testPolicy"]
    require_keys(tests, ["agentLevel", "orchestratorLevel", "reviewEvidenceSummaryRequired"], label)
    if tests["agentLevel"] != "task_packet_required_tests":
        fail(f"{label}: agent-level tests must come from the task packet")
    require_set_contains(
        tests["orchestratorLevel"],
        {"integration_tests", "validators", "lint_or_build_when_applicable"},
        label,
        "orchestrator tests",
    )
    if tests["reviewEvidenceSummaryRequired"] is not True:
        fail(f"{label}: review evidence summary is required")
    clarification = policy["clarificationPolicy"]
    require_keys(clarification, ["clarificationTargetPriority", "defaults"], label)
    if clarification["clarificationTargetPriority"] is not True:
        fail(f"{label}: clarificationTarget must take priority")
    required_defaults = {
        "product_decision": "user",
        "permission_security_fact_conflict": "control",
        "technical_implementation": "orchestrator",
        "domain_specific": "domain_lead",
    }
    if clarification["defaults"] != required_defaults:
        fail(f"{label}: clarification defaults must route user/control/orchestrator/domain_lead")
    permission = policy["permissionPolicy"]
    require_keys(permission, ["permissionRequestRequired", "readonlyPatchProposalAllowed", "waitingUserStatus", "blockedStatus"], label)
    if permission["permissionRequestRequired"] is not True:
        fail(f"{label}: permission request is required when authority is missing")
    if permission["readonlyPatchProposalAllowed"] is not True:
        fail(f"{label}: readonly patch proposal must remain allowed")
    if permission["waitingUserStatus"] != "waiting_user" or permission["blockedStatus"] != "blocked":
        fail(f"{label}: permission waiting statuses must be waiting_user/blocked")
    evidence = policy["evidencePolicy"]
    require_keys(evidence, ["defaultView", "auditView", "finalClaimRequiresEvidenceLinks"], label)
    if evidence["defaultView"] != "summary_with_links":
        fail(f"{label}: default evidence view must be summary with links")
    if evidence["auditView"] != "full_chain":
        fail(f"{label}: audit evidence view must be full chain")
    if evidence["finalClaimRequiresEvidenceLinks"] is not True:
        fail(f"{label}: final claim requires evidence links")
    close = policy["closePolicy"]
    require_keys(close, ["roomCloseAuthority", "orchestratorMayRequestClose", "closeRequestRequiredFields"], label)
    if close["roomCloseAuthority"] != "user_only":
        fail(f"{label}: room close authority must be user only")
    if close["orchestratorMayRequestClose"] is not True:
        fail(f"{label}: orchestrator must be able to request close")
    require_set_contains(
        close["closeRequestRequiredFields"],
        {"final_verdict", "completed_items", "open_items", "test_evidence_summary", "remaining_risks", "handoff_archive_path"},
        label,
        "close request fields",
    )
    memory = policy["memoryPolicy"]
    require_keys(memory, ["roomMemoryAllowed", "memberMemoryDefault", "fullMemoryAccess", "sensitiveFilterRequired", "sourceRequired", "allowedSources"], label)
    if memory["roomMemoryAllowed"] is not True or memory["memberMemoryDefault"] != "summary_only":
        fail(f"{label}: room memory must default to summary-only for members")
    require_set_contains(memory["fullMemoryAccess"], {"control", "orchestrator", "authorized_reviewer"}, label, "full memory access")
    if memory["sensitiveFilterRequired"] is not True or memory["sourceRequired"] is not True:
        fail(f"{label}: room memory requires sensitive filtering and source")
    require_set_contains(memory["allowedSources"], {"user_decision", "system_rule", "task_result", "review_verdict", "evidence_summary", "inferred_note"}, label, "memory sources")
    chat_log = policy["chatLogPolicy"]
    require_keys(chat_log, ["mode", "requiredMessageFields", "filters"], label)
    if chat_log["mode"] != "complete_structured":
        fail(f"{label}: room chat log must be complete_structured")
    require_set_contains(
        chat_log["requiredMessageFields"],
        {"fromSeat", "toSeats", "ccSeats", "visibility", "messageType", "taskPacketId", "roomPacketId", "timestamp", "evidenceLinks"},
        label,
        "chat message fields",
    )
    require_set_contains(chat_log["filters"], {"direct", "cc", "broadcast", "approval", "evidence", "task", "system"}, label, "chat filters")
    inheritance = policy["siteInheritance"]
    require_keys(
        inheritance,
        [
            "siteWorkflowContractRequired",
            "protectedZonesRequired",
            "authorityLayerRequired",
            "taskPacketRequired",
            "evidenceManifestRequired",
            "reviewPacketRequiredForReview",
            "approvalGateRequired",
            "handoffCheckpointRequired",
        ],
        label,
    )
    if any(inheritance[key] is not True for key in inheritance):
        fail(f"{label}: room must inherit all SITE workflow requirements")
    buttons = policy["commandButtons"]
    require_keys(buttons, ["status", "firstScreenCommandAreaReserved"], label)
    if buttons["status"] != "deferred-for-next-design-pass":
        fail(f"{label}: command buttons must remain deferred until the button design pass")
    if buttons["firstScreenCommandAreaReserved"] is not True:
        fail(f"{label}: first screen command area must be reserved")
    return True


def validate_workflow_rooms(path):
    doc = load_json(path)
    require_keys(doc, ["schemaVersion", "updatedAt", "boundary", "rooms"], str(path))
    if doc["schemaVersion"] != "workflow-rooms.registry/v0.1":
        fail(f"{path}: unexpected schemaVersion")
    if not doc["rooms"]:
        fail(f"{path}: rooms registry must contain at least one room")
    seen = set()
    for room in doc["rooms"]:
        require_keys(
            room,
            [
                "id",
                "authorityLayer",
                "truthSource",
                "workflowContract",
                "siteWorkflowBinding",
                "entryRules",
                "forbiddenActions",
            ],
            f"{path}:room",
        )
        room_id = room["id"]
        if room_id in seen:
            fail(f"{path}: duplicate room id {room_id}")
        seen.add(room_id)
        if room["authorityLayer"] != "Harness files":
            fail(f"{path}:{room_id}: Harness files must remain authority")
        if "run-manifest" not in room["truthSource"] or "evidence-index" not in room["truthSource"]:
            fail(f"{path}:{room_id}: truthSource must include run-manifest and evidence-index")
        validate_site_workflow_binding(room["siteWorkflowBinding"], f"{path}:{room_id}:siteWorkflowBinding")
        validate_room_members(room.get("members") or [], f"{path}:{room_id}:members")
    return True


def validate_room_members(members, label):
    allowed_statuses = {"available", "busy", "waiting_user", "blocked", "archived", "offline"}
    allowed_roles = {"control", "orchestrator", "coder", "reviewer", "browser", "search", "ops", "context", "tools", "observer"}
    required_fields = [
        "seatId",
        "name",
        "role",
        "providerModel",
        "status",
        "currentTask",
        "branchWorktree",
        "lastActivityAt",
        "latestEvidence",
    ]
    seen = set()
    for index, member in enumerate(members, 1):
        require_keys(member, required_fields, f"{label}:member:{index}")
        seat_id = member["seatId"]
        if seat_id in seen:
            fail(f"{label}: duplicate seat id {seat_id}")
        seen.add(seat_id)
        if member["status"] not in allowed_statuses:
            fail(f"{label}:{seat_id}: status must be one of {', '.join(sorted(allowed_statuses))}")
        if member["role"] not in allowed_roles:
            fail(f"{label}:{seat_id}: role must be an allowed room role")
        if not member["latestEvidence"]:
            fail(f"{label}:{seat_id}: latest evidence link is required")
    return True


def validate_heartbeats(path):
    doc = load_json(path)
    require_keys(doc, ["schemaVersion", "updatedAt", "boundary", "heartbeats"], str(path))
    if doc["schemaVersion"] != "workflow-heartbeats.registry/v0.1":
        fail(f"{path}: unexpected schemaVersion")
    seen = set()
    for heartbeat in doc["heartbeats"]:
        require_keys(
            heartbeat,
            [
                "heartbeatId",
                "target",
                "status",
                "schedule",
                "maxRuns",
                "maxRuntimeMinutes",
                "mutatesState",
                "evidencePath",
                "stopCondition",
            ],
            f"{path}:heartbeat",
        )
        heartbeat_id = heartbeat["heartbeatId"]
        if heartbeat_id in seen:
            fail(f"{path}: duplicate heartbeat id {heartbeat_id}")
        seen.add(heartbeat_id)
        if heartbeat["mutatesState"] is not False:
            fail(f"{path}:{heartbeat_id}: heartbeats must be read-only in L1")
        if int(heartbeat["maxRuns"]) < 1 or int(heartbeat["maxRuntimeMinutes"]) < 1:
            fail(f"{path}:{heartbeat_id}: bounded maxRuns and maxRuntimeMinutes are required")
        if not heartbeat["evidencePath"] or not heartbeat["stopCondition"]:
            fail(f"{path}:{heartbeat_id}: evidencePath and stopCondition are required")
    return True


def validate_room_message_entry(entry, label):
    require_keys(
        entry,
        [
            "schemaVersion",
            "messageId",
            "roomId",
            "createdAt",
            "fromSeat",
            "visibility",
            "messageType",
            "summary",
            "manifestVisibility",
            "requiresAck",
        ],
        label,
    )
    if entry["schemaVersion"] != "room-message-ledger/v0.1":
        fail(f"{label}: unexpected schemaVersion")
    visibility = entry["visibility"]
    to_seats = entry.get("toSeats") or []
    cc_seats = entry.get("ccSeats") or []
    if visibility in {"direct", "cc", "room_broadcast"} and not to_seats:
        fail(f"{label}: room messages must name explicit toSeats; there is no implicit broadcast")
    if visibility == "cc" and not cc_seats:
        fail(f"{label}: cc visibility requires ccSeats")
    if visibility == "room_broadcast" and entry.get("manifestVisibility") != "summary_only":
        fail(f"{label}: broadcasts still enter the manifest as summary_only")
    if visibility == "manifest_summary" and entry.get("manifestVisibility") != "summary_only":
        fail(f"{label}: manifest_summary cannot expose full message content")
    if "toSeats" not in entry:
        fail(f"{label}: room messages must include toSeats; empty toSeats means no delivery")
    if "ccSeats" not in entry:
        fail(f"{label}: room messages must include ccSeats for visibility audit")
    if "createdAt" not in entry:
        fail(f"{label}: room messages require timestamp")
    if "packetRef" not in entry:
        fail(f"{label}: room messages require packetRef for taskPacketId/roomPacketId trace")
    if entry["fromSeat"] in to_seats and visibility != "room_broadcast":
        fail(f"{label}: direct messages should not address the sender unless explicitly broadcasting")
    if entry["requiresAck"] and not to_seats:
        fail(f"{label}: ack-required messages need explicit recipients")
    if not entry["summary"]:
        fail(f"{label}: summary is required")
    if entry["messageType"] in {"evidence", "review", "decision", "handoff"} and "evidencePath" not in entry:
        fail(f"{label}: evidenceLinks/evidencePath required for evidence-bearing room messages")
    return True


def validate_room_message_ledger(path):
    entries = load_jsonl(path)
    if not entries:
        fail(f"{path}: room message ledger must contain at least one entry")
    seen = set()
    for index, entry in enumerate(entries, 1):
        message_id = entry.get("messageId")
        if message_id in seen:
            fail(f"{path}: duplicate message id {message_id}")
        seen.add(message_id)
        validate_room_message_entry(entry, f"{path}:entry:{index}")
    return True


def validate_default_files(root=ROOT):
    validate_agent_runtimes(root / "agents" / "agent-runtimes.registry.json")
    validate_workflow_rooms(root / "rooms" / "workflow-rooms.registry.json")
    validate_run_ledger(root / "runs" / "workflow-run-ledger.jsonl")
    validate_heartbeats(root / "runs" / "workflow-heartbeats.registry.json")
    validate_room_message_ledger(root / "rooms" / "room-message-ledger.jsonl")
    return True


def main(argv=None):
    argv = argv or sys.argv[1:]
    try:
        if not argv:
            validate_default_files()
        else:
            for raw_path in argv:
                path = Path(raw_path)
                name = path.name
                if name == "agent-runtimes.registry.json" or "agent-runtime" in name:
                    validate_agent_runtimes(path)
                elif name.endswith(".jsonl") or "run-ledger" in name:
                    validate_run_ledger(path)
                elif "workflow-room" in name:
                    validate_workflow_rooms(path)
                elif "heartbeat" in name:
                    validate_heartbeats(path)
                elif "room-message" in name:
                    validate_room_message_ledger(path)
                else:
                    fail(f"{path}: unknown workflow gateway artifact type")
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print("workflow gateway validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

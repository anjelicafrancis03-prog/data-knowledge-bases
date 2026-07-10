import hashlib
import json
import os
import secrets
import socket
import subprocess
import sys
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parent
CONFIG_PATH = Path(os.environ.get("FUSION_WORKBENCH_CONFIG", ROOT / "config.local.json"))


def load_local_config():
    if not CONFIG_PATH.exists():
        return {}
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        return {"_configError": str(exc)}


CONFIG = load_local_config()
CONFIG_PATHS = CONFIG.get("paths") if isinstance(CONFIG.get("paths"), dict) else {}
CONFIG_URLS = CONFIG.get("urls") if isinstance(CONFIG.get("urls"), dict) else {}
CONFIG_FEATURES = CONFIG.get("features") if isinstance(CONFIG.get("features"), dict) else {}


def config_int(name, default):
    raw = os.environ.get(f"FUSION_WORKBENCH_{name.upper()}", CONFIG.get(name))
    if raw is None:
        return default
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


def config_bool(name, default=False):
    raw = os.environ.get(f"FUSION_WORKBENCH_{name.upper()}", CONFIG_FEATURES.get(name))
    if raw is None:
        return default
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def config_path(name, default_relative):
    raw = CONFIG_PATHS.get(name)
    if raw:
        path = Path(os.path.expandvars(str(raw))).expanduser()
        return path if path.is_absolute() else ROOT / path
    return ROOT / default_relative


def config_url(name, default):
    return str(CONFIG_URLS.get(name) or default)


HOST = str(os.environ.get("FUSION_WORKBENCH_HOST", CONFIG.get("host") or "127.0.0.1"))
PORT = config_int("port", 8766)
SIT_PORT = config_int("sitPort", 5173)
KANWAS_PORT = config_int("kanwasPort", 5174)
STAGE10D_GATEWAY_PORT = config_int("stage10dGatewayPort", 18081)
SIT_ROOT = config_path("sitRoot", Path("external") / "sit-root")
KANWAS_ROOT = config_path("kanwasRoot", Path("external") / "kanwas-root")
LOG_DIR = ROOT / "logs"
TASK_DIR = ROOT / "tasks"
TASKS_PATH = ROOT / "tasks.json"
ROOM_DIR = ROOT / "rooms"
ROOMS_REGISTRY_PATH = ROOM_DIR / "workflow-rooms.registry.json"
ACTION_LEDGER_PATH = LOG_DIR / "controller-actions.jsonl"
ACTION_EVIDENCE_PATH = LOG_DIR / "controller-action-evidence.jsonl"
ADAPTER_REGISTRY_PATH = ROOT / "adapters" / "adapter-registry.json"
RUN_MANIFEST_DIR = config_path("runManifestDir", Path("evidence") / "run-manifest")
ADAPTER_DRY_RUN_DIR = RUN_MANIFEST_DIR / "adapter-dry-runs"
ROUTE_REGISTRY_PATH = config_path("routeRegistryPath", Path("external") / "routes.registry.json")
PACKET_VALIDATOR_PATH = config_path("packetValidatorPath", Path("external") / "validate-external-agent-packet.ps1")
REGISTRY_CONTRACT_PATH = config_path("registryContractPath", Path("external") / "fusion-adapter-registry-contract-v0.1.md")
REGISTRY_VALIDATOR_PATH = config_path("registryValidatorPath", Path("external") / "validate-fusion-adapter-registry.ps1")
REGISTRY_VALIDATION_PATH = ADAPTER_DRY_RUN_DIR / "fusion-adapter-registry.validation.json"
DISPATCH_DRAFT_PATH = ADAPTER_DRY_RUN_DIR / "fusion-phase1-o-review-dispatch.draft.v0.1.json"
DISPATCH_VALIDATION_PATH = ADAPTER_DRY_RUN_DIR / "fusion-phase1-o-review-dispatch.validation.json"
DISPATCH_PREP_PATH = ADAPTER_DRY_RUN_DIR / "fusion-phase1-o-review-dispatch-prep-20260614.md"
DISPATCH_SYNTHESIS_PLACEHOLDER_PATH = ADAPTER_DRY_RUN_DIR / "fusion-phase1-o-review-synthesis.placeholder.md"
JCODE_GATE_BRIEF_PATH = ADAPTER_DRY_RUN_DIR / "jcode-canonical-seat-gate-brief-20260614.md"
EVIDENCE_PACK_PATH = config_path("evidencePack", Path("evidence") / "site-multiagent-config-and-evidence-pack.md")
EVIDENCE_INDEX_PATH = config_path("evidenceIndex", Path("evidence") / "evidence-index.md")
HANDOFF_PATH = config_path("handoff", Path("evidence") / "handoff.md")
STAGE10D_RESULT_PATH = config_path("stage10dResult", Path("evidence") / "stage10d-result.json")
STAGE10D_WORKER_PATH = config_path("stage10dWorker", Path("evidence") / "stage10d-worker-output.md")
REPORT_ROOT = config_path("reportRoot", Path("reports"))
STAGE10D_ROOT = config_path("stage10dRoot", Path("evidence") / "stage10d")
EXTERNAL_AGENT_SEATS_REGISTRY_PATH = config_path("externalAgentSeatsRegistry", Path("external") / "external-agent-seats.registry.json")
EXTERNAL_AGENT_PACKET_SCHEMA_PATH = config_path("externalAgentPacketSchema", Path("external") / "external-agent-task-packet.schema.json")
JCODE_DRY_RUN_EVIDENCE_DIR = config_path("jcodeDryRunEvidenceDir", Path("evidence") / "jcode_l1_plan")
ADAPTER_INPUT_PATHS = [
    config_path("agentFusionConsensus", Path("inputs") / "agent-fusion-three-thread-consensus.md"),
    config_path("workbenchComparison", Path("inputs") / "workbench-vs-site-kanwas-jcode-comparison.md"),
    config_path("jcodeReviewBrief", Path("inputs") / "jcode-agent-review-brief.md"),
    HANDOFF_PATH,
]
FEATURE_FLAGS = {
    "strictOrigin": config_bool("strictOrigin", True),
    "openTargets": config_bool("openTargets", False),
    "processActions": config_bool("processActions", False),
    "dockerActions": config_bool("dockerActions", False),
    "taskWrites": config_bool("taskWrites", True),
    "adapterDryRun": config_bool("adapterDryRun", True),
    "roomWrites": config_bool("roomWrites", False),
}
SESSION_TOKEN = secrets.token_urlsafe(32)
SESSION_COOKIE_NAME = "fusion_workbench_session"
ALLOWED_ORIGINS = {
    f"http://{HOST}:{PORT}",
    f"http://localhost:{PORT}",
}

TASK_TEMPLATES = {
    "evidence_closeout": {
        "title": "证据收口检查",
        "ownerSeat": "Harness / SIT",
        "description": "核对最新证据、哈希、交接与索引是否一致，补齐缺口后再进入下一阶段。",
        "nextAction": "确认最新证据索引、补写手工验收记录，并标记仍待完成的条目。",
        "evidenceRoots": [
            str(HANDOFF_PATH),
            str(EVIDENCE_INDEX_PATH),
        ],
        "checklist": [
            "确认证据索引与交接卡一致",
            "核对关键文件 SHA 是否与看板一致",
            "把缺口写成下一步而不是口头备注",
        ],
    },
    "kanwas_projection": {
        "title": "Kanwas 只读投影任务",
        "ownerSeat": "Kanwas",
        "description": "把 SIT 状态、Stage10D 结果和证据入口整理成可扫读的投影稿，给人看懂上下文。",
        "nextAction": "收集当前状态、截图和开放路径，写出一页式投影说明。",
        "evidenceRoots": [
            str(ROOT / "index.html"),
            str(ROOT / "verification.json"),
        ],
        "checklist": [
            "保留原始路径和哈希",
            "把要点压缩成可快速扫描的条目",
            "区分只读投影与真实执行",
        ],
    },
    "review_packet": {
        "title": "O1/O3 review packet",
        "ownerSeat": "O1 / O3",
        "description": "生成闭包审查材料包，让外部 reviewer 先看证据、再看判断，避免跑偏。",
        "nextAction": "整理当前计划、变更点和风险清单，附上需要审查的具体结论。",
        "evidenceRoots": [
            str(HANDOFF_PATH),
            str(ROOT / "controller.py"),
        ],
        "checklist": [
            "列出本轮真正改了什么",
            "标记哪些动作只是本地派工",
            "写清楚 reviewer 需要回答的 3 个问题",
        ],
    },
    "stage10d_next_gate": {
        "title": "Stage10D 下一阶段 gate",
        "ownerSeat": "Stage10D",
        "description": "把 Stage10D v0.5 的通过结果收束成下一道门槛，避免直接跳到 L3 实时执行。",
        "nextAction": "确认下一阶段是材料包、审查包还是受控 worker，而不是越权到真实 provider 执行。",
        "evidenceRoots": [
            str(STAGE10D_RESULT_PATH),
            str(STAGE10D_WORKER_PATH),
        ],
        "checklist": [
            "引用 v0.5 通过证据",
            "保持审批边界不变",
            "把下一步写成 gate，不写成幻想",
        ],
    },
}

TASK_TEMPLATES.update({
    "o_review_dispatch_prep": {
        "title": "Fusion Phase 1 O-review dispatch prep",
        "ownerSeat": "Harness / O3 review lane",
        "description": "Prepare the existing schema-valid O-review L1 packet for a closed-report manual review dispatch. This task does not approve or send the review call.",
        "nextAction": "Confirm the dispatch draft, registry contract, validation files, and approval boundary; request exact approval only if the user wants the real O-review dispatch.",
        "evidenceRoots": [
            str(REGISTRY_CONTRACT_PATH),
            str(REGISTRY_VALIDATION_PATH),
            str(DISPATCH_DRAFT_PATH),
            str(DISPATCH_VALIDATION_PATH),
            str(DISPATCH_PREP_PATH),
            str(HANDOFF_PATH),
        ],
        "checklist": [
            "Verify registry validation remains ok=true.",
            "Verify dispatch draft states are created and validated only.",
            "Verify sentManually=false and reviewOutputsCount=0.",
            "Confirm required approval phrase is APPROVE_FUSION_PHASE1_O_REVIEW_DISPATCH.",
            "Do not call O1/O2/O3, provider APIs, or Claude launchers from this task.",
            "After approval, save raw review output, clean review, dispatch log, synthesis, and evidence-index update.",
        ],
        "boundary": [
            "This task is approval-prep only.",
            "It does not dispatch O reviewers, call providers, read credentials, launch jcode, mutate Docker, or edit Codex/MCP/browser/startup state.",
        ],
    },
    "jcode_seat_schema_review": {
        "title": "jcode canonical seat/schema review",
        "ownerSeat": "Harness / code-dev-review",
        "description": "Review whether jcode may become a canonical external-agent target seat, starting from the non-canonical jcode planning adapter and gate brief.",
        "nextAction": "Review the gate brief, propose a bounded L0/L1-only seat contract, and list exact registry/schema/fixture changes required before any canonical packet can be emitted.",
        "evidenceRoots": [
            str(JCODE_GATE_BRIEF_PATH),
            str(ADAPTER_REGISTRY_PATH),
            str(EXTERNAL_AGENT_SEATS_REGISTRY_PATH),
            str(EXTERNAL_AGENT_PACKET_SCHEMA_PATH),
            str(JCODE_DRY_RUN_EVIDENCE_DIR),
        ],
        "checklist": [
            "Keep jcode_l1_plan non-canonical until seat registry and packet schema are deliberately changed.",
            "Define initial allowed levels as L0/L1 only; block L2/L3/L4.",
            "Require positive and negative validator fixtures before schema adoption.",
            "Keep the user's normal jcode profile untouched.",
            "Do not launch jcode, WSL workers, provider calls, or credential reads from this task.",
            "Record any proposed registry/schema changes in evidence index and checkpoint before implementation.",
        ],
        "boundary": [
            "This task is a review/design packet only.",
            "It does not add jcode to the schema, launch jcode, create WSL sandboxes, read credentials, or grant runtime authority.",
        ],
    },
})

PATHS = {
    "dashboard": ROOT / "index.html",
    "evidence_pack": EVIDENCE_PACK_PATH,
    "evidence_index": EVIDENCE_INDEX_PATH,
    "handoff": HANDOFF_PATH,
    "stage10d_result": STAGE10D_RESULT_PATH,
    "stage10d_worker": STAGE10D_WORKER_PATH,
    "dashboard_dir": ROOT,
    "report_root": REPORT_ROOT,
    "stage10d_root": STAGE10D_ROOT,
    "adapter_dry_runs": ADAPTER_DRY_RUN_DIR,
    "adapter_registry_contract": REGISTRY_CONTRACT_PATH,
    "adapter_registry_validation": REGISTRY_VALIDATION_PATH,
    "workflow_rooms_registry": ROOMS_REGISTRY_PATH,
    "workflow_room_doc": ROOT / "docs" / "workflow-room-v0.1.md",
    "o_review_dispatch_draft": DISPATCH_DRAFT_PATH,
    "o_review_dispatch_validation": DISPATCH_VALIDATION_PATH,
    "o_review_dispatch_prep": DISPATCH_PREP_PATH,
    "jcode_gate_brief": JCODE_GATE_BRIEF_PATH,
    "sit_root": SIT_ROOT,
    "kanwas_root": KANWAS_ROOT,
}

URLS = {
    "dashboard": f"http://{HOST}:{PORT}/index.html",
    "sit": config_url("sit", f"http://127.0.0.1:{SIT_PORT}/"),
    "kanwas": config_url("kanwas", f"http://127.0.0.1:{KANWAS_PORT}/"),
    "stage10dGateway": config_url("stage10dGateway", f"http://127.0.0.1:{STAGE10D_GATEWAY_PORT}/"),
}


def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.25)
        return s.connect_ex((HOST, port)) == 0


def ensure_log_dir():
    LOG_DIR.mkdir(exist_ok=True)


def append_event(action, result, request=None):
    ensure_log_dir()
    ok = bool(isinstance(result, dict) and result.get("ok"))
    event = {
        "createdAt": now_iso(),
        "action": action,
        "ok": ok,
        "request": request or {},
        "result": result,
    }
    with ACTION_LEDGER_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")
    evidence = {
        "createdAt": event["createdAt"],
        "action": action,
        "ok": ok,
        "evidenceType": "operator-action",
        "ledgerPath": str(ACTION_LEDGER_PATH),
    }
    if isinstance(result, dict):
        for key in (
            "adapterId",
            "runId",
            "runDir",
            "taskId",
            "packetPath",
            "validationPath",
            "summaryPath",
            "planPath",
            "riskPath",
            "cleanupPath",
            "opened",
            "stdout",
            "stderr",
            "exitCode",
            "stoppedPid",
        ):
            if key in result:
                evidence[key] = result[key]
        if "task" in result and isinstance(result["task"], dict):
            evidence["taskId"] = result["task"].get("id")
            evidence["packetPath"] = result.get("packetPath") or result["task"].get("packetPath")
    with ACTION_EVIDENCE_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(evidence, ensure_ascii=False) + "\n")


def ensure_task_dir():
    TASK_DIR.mkdir(parents=True, exist_ok=True)


def ensure_room_dir():
    ROOM_DIR.mkdir(parents=True, exist_ok=True)


def empty_task_store():
    return {"version": 1, "updatedAt": now_iso(), "tasks": []}


def read_task_store():
    if not TASKS_PATH.exists():
        return empty_task_store()
    data = read_json(TASKS_PATH)
    if not isinstance(data, dict):
        return empty_task_store()
    tasks = data.get("tasks")
    if not isinstance(tasks, list):
        tasks = []
    return {
        "version": data.get("version", 1),
        "updatedAt": data.get("updatedAt", now_iso()),
        "tasks": [task for task in tasks if isinstance(task, dict)],
    }


def write_json_atomic(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp_path.replace(path)


DEFAULT_WORKFLOW_ROOMS = {'schemaVersion': 'workflow-rooms.registry/v0.1',
 'updatedAt': '2026-06-15T18:45:00+08:00',
 'boundary': 'Room v0.1 is a coordination and packet layer only. It records members, roles, '
             'workflow contracts, and evidence requirements. It does not dispatch live agents, '
             'call providers, read credentials, mutate browser state, or grant runtime authority.',
 'rooms': [{'id': 'sit-kanwas-fusion-room',
            'title': 'SIT / Kanwas Fusion Room',
            'mode': 'L1-packet-room',
            'status': 'draft-active',
            'authorityLayer': 'Harness files',
            'truthSource': 'run-manifest + evidence-index + task packets',
            'workflowContract': 'Thread-as-Agent, Room-as-Workflow v0.1',
            'siteWorkflowBinding': {'status': 'hard-required',
                                    'source': 'Harness Site Workflow Console Phase 3a-3d contract',
                                    'normalThreadRulesPreserved': True,
                                    'siteContractAppliesInRoom': True,
                                    'uiIsAuthority': False,
                                    'siteDirectCliAllowed': False,
                                    'packetGenerationPolicy': {'mode': 'inviter-drafts-control-validates',
                                                               'draftAllowedBy': ['inviter',
                                                                                  'orchestrator',
                                                                                  'control'],
                                                               'controlValidationRequired': True,
                                                               'joinedWithoutPacketAllowed': False},
                                    'roomPermissionPolicy': {'mode': 'normal-capabilities-preserved-room-packet-bounds-writes',
                                                             'normalCapabilitiesPreserved': True,
                                                             'writeScopeSource': 'room packet',
                                                             'executionScopeSource': 'room packet',
                                                             'roomPacketRequiredForWrites': True},
                                    'evidenceDisplayPolicy': {'mode': 'daily-and-audit-toggle',
                                                              'defaultView': 'daily',
                                                              'dailyShowsFinalConclusion': True,
                                                              'auditViewRequired': True,
                                                              'evidenceDrawerRequired': True,
                                                              'finalConclusionMustLinkEvidence': True},
                                    'commandSurfacePolicy': {'firstScreen': 'control-command-center',
                                                             'longChatDefault': False,
                                                             'firstScreenPanels': ['room status',
                                                                                   'agent seats',
                                                                                   'current tasks',
                                                                                   'pending '
                                                                                   'approvals',
                                                                                   'latest '
                                                                                   'evidence',
                                                                                   'command '
                                                                                   'actions'],
                                                             'roomComposerDefault': 'no-recipient-until-selected',
                                                             'emptyToSeatsMeansNoDelivery': True,
                                                             'broadcastRequiresExplicitVisibility': True,
                                                             'ccSeatsAssignTasks': False,
                                                             'threadCardFields': ['name',
                                                                                  'role',
                                                                                  'status',
                                                                                  'current task',
                                                                                  'room membership',
                                                                                  'model/provider',
                                                                                  'branch/worktree',
                                                                                  'last activity '
                                                                                  'time',
                                                                                  'latest evidence '
                                                                                  'time'],
                                                             'newThreadDefaultMode': 'normal-thread',
                                                             'roomJoinRequiresExplicitPacket': True,
                                                             'approvalDisplay': 'chat-context-and-approval-queue',
                                                             'approvalQueueRequired': True},
                                    'gstackRoomModelPolicy': {'phase': 'phase-1',
                                                              'roomFirstScreen': 'control-command-center',
                                                              'longChatDefault': False,
                                                              'chatLikeJoinUi': True,
                                                              'joinIsControlLayerAction': True,
                                                              'joinAllowedBy': ['control',
                                                                                'orchestrator'],
                                                              'joinRequiresPacket': True,
                                                              'joinRequiresRole': True,
                                                              'allowedJoinRoles': ['orchestrator',
                                                                                   'coder',
                                                                                   'reviewer',
                                                                                   'browser',
                                                                                   'search',
                                                                                   'ops',
                                                                                   'context',
                                                                                   'tools',
                                                                                   'observer'],
                                                              'dualMode': {'normalThreadRulesPreserved': True,
                                                                           'roomModeRequiresJoinPacket': True,
                                                                           'roomTaskRequiresSeparateTaskPacket': True,
                                                                           'exitRequiresExitPacket': True},
                                                              'agentSeatCard': {'requiredFields': ['name',
                                                                                                   'role',
                                                                                                   'provider/model',
                                                                                                   'status',
                                                                                                   'current '
                                                                                                   'task',
                                                                                                   'branch/worktree',
                                                                                                   'last '
                                                                                                   'activity '
                                                                                                   'time',
                                                                                                   'latest '
                                                                                                   'evidence'],
                                                                                'allowedStatuses': ['available',
                                                                                                    'busy',
                                                                                                    'waiting_user',
                                                                                                    'blocked',
                                                                                                    'archived',
                                                                                                    'offline']},
                                                              'messageDelivery': {'emptyToSeats': 'no_delivery',
                                                                                  'broadcast': 'explicit_room_broadcast_only',
                                                                                  'ccSeats': 'visibility_only_not_assignment',
                                                                                  'messageWithoutToSeats': 'draft_or_log_only'},
                                                              'activeRoomLimit': {'maxActiveRoomsPerAgent': 1,
                                                                                  'roomChangeRequiresExitPacket': True,
                                                                                  'exitPacketOptions': ['resume_normal',
                                                                                                        'archive',
                                                                                                        'detached_handoff']},
                                                              'orchestratorPolicy': {'phaseOneUpgradeProvider': 'codex_only',
                                                                                     'defaultOrchestrator': 'codex-control',
                                                                                     'userCanDesignateCodexOrchestrator': True,
                                                                                     'nonCodexOrchestratorAllowed': False},
                                                              'domainLeadPolicy': {'allowed': True,
                                                                                   'underOrchestrator': True,
                                                                                   'cannot': ['change_authority',
                                                                                              'merge',
                                                                                              'close_room',
                                                                                              'override_packet']},
                                                              'branchPolicy': {'codingAgentRequiresOwnBranchWorktree': True,
                                                                               'agentBranchPattern': 'room/<room_id>/<agent_id>/<task_slug>',
                                                                               'integrationBranchPattern': 'integration/<room_id>/<task_slug>',
                                                                               'defaultMrSource': 'integration_branch'},
                                                              'commitPolicy': {'codingAgentCanCommitOwnBranch': True,
                                                                               'cannot': ['merge',
                                                                                          'push_main',
                                                                                          'close_mr',
                                                                                          'close_pr',
                                                                                          'mark_complete_without_required_evidence'],
                                                                               'commitRequires': ['task_packet.tests_required',
                                                                                                  'task_packet.evidence_required',
                                                                                                  'allowed_files_scope']},
                                                              'testPolicy': {'agentLevel': 'task_packet_required_tests',
                                                                             'orchestratorLevel': ['integration_tests',
                                                                                                   'validators',
                                                                                                   'lint_or_build_when_applicable'],
                                                                             'reviewEvidenceSummaryRequired': True},
                                                              'clarificationPolicy': {'clarificationTargetPriority': True,
                                                                                      'defaults': {'product_decision': 'user',
                                                                                                   'permission_security_fact_conflict': 'control',
                                                                                                   'technical_implementation': 'orchestrator',
                                                                                                   'domain_specific': 'domain_lead'}},
                                                              'permissionPolicy': {'permissionRequestRequired': True,
                                                                                   'readonlyPatchProposalAllowed': True,
                                                                                   'waitingUserStatus': 'waiting_user',
                                                                                   'blockedStatus': 'blocked'},
                                                              'evidencePolicy': {'defaultView': 'summary_with_links',
                                                                                 'auditView': 'full_chain',
                                                                                 'finalClaimRequiresEvidenceLinks': True},
                                                              'closePolicy': {'roomCloseAuthority': 'user_only',
                                                                              'orchestratorMayRequestClose': True,
                                                                              'closeRequestRequiredFields': ['final_verdict',
                                                                                                             'completed_items',
                                                                                                             'open_items',
                                                                                                             'test_evidence_summary',
                                                                                                             'remaining_risks',
                                                                                                             'handoff_archive_path']},
                                                              'memoryPolicy': {'roomMemoryAllowed': True,
                                                                               'memberMemoryDefault': 'summary_only',
                                                                               'fullMemoryAccess': ['control',
                                                                                                    'orchestrator',
                                                                                                    'authorized_reviewer'],
                                                                               'sensitiveFilterRequired': True,
                                                                               'sourceRequired': True,
                                                                               'allowedSources': ['user_decision',
                                                                                                  'system_rule',
                                                                                                  'task_result',
                                                                                                  'review_verdict',
                                                                                                  'evidence_summary',
                                                                                                  'inferred_note']},
                                                              'chatLogPolicy': {'mode': 'complete_structured',
                                                                                'requiredMessageFields': ['fromSeat',
                                                                                                          'toSeats',
                                                                                                          'ccSeats',
                                                                                                          'visibility',
                                                                                                          'messageType',
                                                                                                          'taskPacketId',
                                                                                                          'roomPacketId',
                                                                                                          'timestamp',
                                                                                                          'evidenceLinks'],
                                                                                'filters': ['direct',
                                                                                            'cc',
                                                                                            'broadcast',
                                                                                            'approval',
                                                                                            'evidence',
                                                                                            'task',
                                                                                            'system']},
                                                              'siteInheritance': {'siteWorkflowContractRequired': True,
                                                                                  'protectedZonesRequired': True,
                                                                                  'authorityLayerRequired': True,
                                                                                  'taskPacketRequired': True,
                                                                                  'evidenceManifestRequired': True,
                                                                                  'reviewPacketRequiredForReview': True,
                                                                                  'approvalGateRequired': True,
                                                                                  'handoffCheckpointRequired': True},
                                                              'commandButtons': {'status': 'deferred-for-next-design-pass',
                                                                                 'firstScreenCommandAreaReserved': True}},
                                    'multiAgentCodingPolicy': {'orchestratorDefault': 'codex-control',
                                                               'userCanDesignateOrchestrator': True,
                                                               'codingPreflightRequired': ['task '
                                                                                           'packet',
                                                                                           'branch/worktree',
                                                                                           'allowed '
                                                                                           'files',
                                                                                           'tests '
                                                                                           'to run',
                                                                                           'evidence '
                                                                                           'level'],
                                                               'integrationOwner': 'orchestrator',
                                                               'finalMergeAuthority': ['user',
                                                                                       'control'],
                                                               'agentBranchPattern': 'room/<room_id>/<agent_id>/<task_slug>',
                                                               'integrationBranchPattern': 'integration/<room_id>/<task_slug>',
                                                               'agentCanCommitOwnBranch': True,
                                                               'agentCannot': ['merge',
                                                                               'push_main',
                                                                               'close_mr',
                                                                               'close_pr',
                                                                               'mark_complete_without_required_evidence'],
                                                               'conflictResolution': 'authority-layer-then-user-product-then-recorded-technical-decision',
                                                               'commitScope': 'packet-allowed-files-only',
                                                               'extraFilesPolicy': 'patch-proposal-only',
                                                               'failedRequiredTestsStatus': 'blocked',
                                                               'failureEvidenceRequired': ['failure '
                                                                                           'log',
                                                                                           'attempted '
                                                                                           'fixes',
                                                                                           'next-step '
                                                                                           'recommendation']},
                                    'roomLifecyclePolicy': {'longTermRoomPurpose': 'members-history-standing-rules-only',
                                                            'realWorkRequiresRunOrTaskPacket': True,
                                                            'exitPolicy': 'exit-packet-required',
                                                            'exitPacketOptions': ['resume normal '
                                                                                  'task',
                                                                                  'archive',
                                                                                  'detached '
                                                                                  'handoff'],
                                                            'memoryAccessPolicy': {'ordinaryMember': 'summary-only',
                                                                                   'orchestrator': 'full-source-chain-with-permission',
                                                                                   'control': 'full-source-chain-with-permission',
                                                                                   'authorizedReviewer': 'full-source-chain-with-permission',
                                                                                   'sensitiveMemoryFilteringRequired': True,
                                                                                   'memoryRequiresAuditableSource': True,
                                                                                   'allowedSources': ['user_decision',
                                                                                                      'system_rule',
                                                                                                      'task_result',
                                                                                                      'review_verdict',
                                                                                                      'evidence_summary',
                                                                                                      'inferred_note']},
                                                            'historyDisplay': {'defaultMode': 'complete-flow-with-filters',
                                                                               'filtersRequired': ['direct',
                                                                                                   'cc',
                                                                                                   'broadcast',
                                                                                                   'evidence',
                                                                                                   'approval',
                                                                                                   'task',
                                                                                                   'system']},
                                                            'archiveRestorePolicy': {'restorePacketRequired': True,
                                                                                     'restorePacketFields': ['restore '
                                                                                                             'reason',
                                                                                                             'history '
                                                                                                             'scope',
                                                                                                             'current '
                                                                                                             'target']},
                                                            'ruleChangePolicy': {'memberCanPropose': True,
                                                                                 'registryMutationRequiresApprovalBy': ['user',
                                                                                                                        'control']}},
                                    'defaultEvidenceLevels': {'readOnly': 'light_readonly',
                                                              'review': 'review_packet',
                                                              'writeOrExecution': 'full_site_bundle',
                                                              'protectedAction': 'protected_execution'},
                                    'requiredRoomRunArtifacts': ['room entry packet',
                                                                 'task packet',
                                                                 'run manifest',
                                                                 'evidence index',
                                                                 'validator report',
                                                                 'verification summary',
                                                                 'bridge trace or explicit '
                                                                 'mock-only note',
                                                                 'run-id namespaced outputs',
                                                                 'protected-action ledger'],
                                    'protectedActionArtifacts': ['exact human approval text',
                                                                 'approval manifest',
                                                                 'approval manifest SHA256 sidecar',
                                                                 'approval evidence',
                                                                 'hash-bound approved text',
                                                                 'changed-file hashes or explicit '
                                                                 'no-change proof']},
            'purpose': 'Coordinate SIT, Kanwas, external review seats, and future CLI adapters '
                       'without replacing Harness authority.',
            'members': [{'seatId': 'codex-control',
                         'name': 'Codex control thread',
                         'label': 'Codex control thread',
                         'role': 'control',
                         'providerModel': 'Codex / GPT-5',
                         'kind': 'codex-thread',
                         'normalMode': 'ordinary Codex thread rules',
                         'roomMode': 'room controller and evidence owner',
                         'permissionClass': 'report-write',
                         'status': 'available',
                         'currentTask': 'Own room policy landing, evidence, validation, and '
                                        'integration.',
                         'branchWorktree': 'harden-controller-boundary / '
                                           'C:\\html\\sit-kanwas-fusion-dashboard',
                         'lastActivityAt': '2026-06-15T18:45:00+08:00',
                         'latestEvidence': 'docs/gstack-room-operating-decisions.md'},
                        {'seatId': 'browser-lane',
                         'name': 'Browser lane',
                         'label': 'Browser lane',
                         'role': 'browser',
                         'providerModel': 'Fixed Chrome / CDP',
                         'kind': 'browser-thread',
                         'normalMode': 'local browser verification',
                         'roomMode': 'screenshot and UI evidence capture',
                         'permissionClass': 'read-only',
                         'status': 'available',
                         'currentTask': 'Capture browser evidence only when assigned by packet.',
                         'branchWorktree': 'none / browser evidence lane',
                         'lastActivityAt': '2026-06-15T18:03:00+08:00',
                         'latestEvidence': 'C:/html/evidence/browser-capture'},
                        {'seatId': 'o3-review',
                         'name': 'O3 / Opus review lane',
                         'label': 'O3 / Opus review lane',
                         'role': 'reviewer',
                         'providerModel': 'Opus 4.8 / O3 review lane',
                         'kind': 'external-review-seat',
                         'normalMode': 'independent reviewer',
                         'roomMode': 'closed-report review from bounded packet',
                         'permissionClass': 'report-write',
                         'status': 'available',
                         'currentTask': 'Review bounded packets from GitLab MR or saved review '
                                        'package.',
                         'branchWorktree': 'none / review-only',
                         'lastActivityAt': '2026-06-15T15:19:00+08:00',
                         'latestEvidence': 'F:/codex/reports/polynoia-kanwas-strategy-opus-review-20260615/opus-4.8-gitlab-duo-paseo-response-20260615-1519.md'},
                        {'seatId': 'jcode-candidate',
                         'name': 'jcode candidate lane',
                         'label': 'jcode candidate lane',
                         'role': 'observer',
                         'providerModel': 'jcode / candidate adapter',
                         'kind': 'future-cli-adapter',
                         'normalMode': 'not canonical',
                         'roomMode': 'review-only design candidate',
                         'permissionClass': 'report-write',
                         'status': 'blocked',
                         'currentTask': 'Remain review-only until L2 adapter gate is approved.',
                         'branchWorktree': 'none / noncanonical',
                         'lastActivityAt': '2026-06-14T00:00:00+08:00',
                         'latestEvidence': 'F:/codex/reports/jcode-agent-review-package-20260614/review-brief.md'}],
            'entryRules': ['A standalone thread follows its normal platform rules until it is '
                           'named in a room packet.',
                           'Joining the room means accepting the room workflow contract, assigned '
                           'role, allowed reads/writes, evidence requirements, and stop '
                           'conditions.',
                           'Joining the room also activates the Site Workflow Console hard '
                           'requirements for manifest, evidence, validation, protected-action '
                           'ledger, and approval-bound execution.',
                           'L1 room packets are manual and evidence-based; runtime enforcement is '
                           'false.',
                           'Every result must return to a task packet, run manifest, evidence '
                           'index, or review output path.'],
            'forbiddenActions': ['No live provider call from the room registry.',
                                 'No direct launch of jcode or other CLI adapters from Room v0.1.',
                                 'No credential-store, browser-profile, MCP, Codex config, '
                                 'startup-task, deployment, merge, or publish mutation.',
                                 'No UI state may become durable truth.'],
            'nextSafeActions': ['Generate a room kickoff task packet.',
                                'Ask Opus 4.8 to review the room contract and missing L2 gates.',
                                'Promote individual CLI adapters only after registry, fixture, and '
                                'sandbox review.']}]}

def read_rooms_registry():
    if not ROOMS_REGISTRY_PATH.exists():
        return DEFAULT_WORKFLOW_ROOMS
    data = read_json(ROOMS_REGISTRY_PATH)
    if not isinstance(data, dict):
        fallback = dict(DEFAULT_WORKFLOW_ROOMS)
        fallback["error"] = str(data)
        return fallback
    rooms = data.get("rooms")
    if not isinstance(rooms, list):
        data["rooms"] = []
    return data


def room_by_id(room_id):
    registry = read_rooms_registry()
    for room in registry.get("rooms", []):
        if isinstance(room, dict) and room.get("id") == room_id:
            return room
    return None


def room_summary(registry):
    rooms = registry.get("rooms", [])
    counts = {}
    member_count = 0
    for room in rooms:
        if not isinstance(room, dict):
            continue
        status = room.get("status", "unknown")
        counts[status] = counts.get(status, 0) + 1
        members = room.get("members")
        if isinstance(members, list):
            member_count += len(members)
    return {
        "count": len([room for room in rooms if isinstance(room, dict)]),
        "memberCount": member_count,
        "statusCounts": counts,
    }


def read_adapter_registry():
    if not ADAPTER_REGISTRY_PATH.exists():
        return {
            "schemaVersion": "fusion-adapter-registry/v0.1",
            "updatedAt": now_iso(),
            "boundary": "adapter registry missing",
            "adapters": [],
        }
    data = read_json(ADAPTER_REGISTRY_PATH)
    if not isinstance(data, dict):
        return {
            "schemaVersion": "fusion-adapter-registry/v0.1",
            "updatedAt": now_iso(),
            "boundary": "adapter registry unreadable",
            "adapters": [],
            "error": str(data),
        }
    adapters = data.get("adapters")
    if not isinstance(adapters, list):
        data["adapters"] = []
    return data


def adapter_by_id(adapter_id):
    registry = read_adapter_registry()
    for adapter in registry.get("adapters", []):
        if isinstance(adapter, dict) and adapter.get("id") == adapter_id:
            return adapter
    return None


def artifact_hash(path, role):
    return {
        "path": str(path),
        "sha256": sha256(path),
        "role": role,
    }


def ensure_adapter_run_dir(adapter_id):
    run_id = f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-{adapter_id}"
    run_dir = ADAPTER_DRY_RUN_DIR / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_id, run_dir


def protected_zone_flags():
    return [
        "codex-config",
        "mcp-registration",
        "startup-tasks",
        "credential-store",
        "raw-secrets",
        "fixed-browser-state",
        "browser-session-material",
        "external-publish-or-send",
        "destructive-operation",
    ]


def validate_external_packet(packet_path, output_path):
    if not PACKET_VALIDATOR_PATH.exists():
        return {
            "ok": False,
            "error": "packet validator missing",
            "validatorPath": str(PACKET_VALIDATOR_PATH),
        }
    try:
        packet_path = assert_within_root(packet_path, ADAPTER_DRY_RUN_DIR, "packet")
        output_path = assert_within_root(output_path, ADAPTER_DRY_RUN_DIR, "validation output")
    except ValueError as exc:
        return {"ok": False, "error": str(exc)}
    completed = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(PACKET_VALIDATOR_PATH),
            "-PacketPath",
            str(packet_path),
            "-OutputPath",
            str(output_path),
            "-NoExitCode",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    result = {
        "exitCode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }
    validation = read_json(output_path) if output_path.exists() else {}
    return {
        "ok": bool(isinstance(validation, dict) and validation.get("ok")),
        "exitCode": result["exitCode"],
        "stdoutHint": result["stdout"][:500],
        "stderrHint": result["stderr"][:500],
        "validationPath": str(output_path),
        "validation": validation,
    }


def adapter_input_paths():
    return ADAPTER_INPUT_PATHS


def build_o_review_packet(adapter, run_dir, run_id):
    return_path = run_dir / "o-review-return-placeholder.md"
    packet_path = run_dir / "o-review-l1.packet.json"
    validation_path = run_dir / "o-review-l1.validation.json"
    summary_path = run_dir / "adapter-dry-run-summary.json"
    input_paths = [path for path in adapter_input_paths() if path.exists()]
    artifact_hashes = [
        artifact_hash(ROUTE_REGISTRY_PATH, "route-registry"),
        artifact_hash(RUN_MANIFEST_DIR / "manifest.md", "run-manifest"),
        artifact_hash(PATHS["evidence_index"], "evidence-index"),
        artifact_hash(PATHS["handoff"], "checkpoint"),
    ]
    for input_path in input_paths:
        artifact_hashes.append(artifact_hash(input_path, "input"))
    packet = {
        "packetVersion": "external-agent-task/v0.1",
        "taskId": f"fusion-phase1-{run_id}",
        "createdAt": now_iso(),
        "createdBy": "sit-kanwas-fusion-workbench-controller",
        "accessLevel": "L1",
        "routeId": adapter.get("routeId", "model-ai-api"),
        "ownerModules": ["harness-control", "mcp-skills-integration"],
        "permissionClass": adapter.get("permissionClass", "report-write"),
        "targetSeat": adapter.get("targetSeat", "o3"),
        "goal": "Closed-report review of Fusion Phase 1 packet-gated operator console and next adapter steps.",
        "inputs": [str(path) for path in input_paths],
        "inputDeliveryMethod": "prompt-file-stdin",
        "allowedReads": [str(path) for path in input_paths],
        "allowedWrites": [],
        "forbiddenActions": [
            "Do not use tools.",
            "Do not access filesystem independently.",
            "Do not read credentials, cookies, browser state, login state, or raw secrets.",
            "Do not edit Codex config, MCP registration, startup tasks, or protected zones.",
            "Do not call providers or perform external publish/send/merge/push/payment actions.",
        ],
        "protectedZoneFlags": protected_zone_flags(),
        "expectedOutputs": [
            "Review report saved by controller at the declared return path.",
            "Verdict, blocking findings, non-blocking findings, and adapter readiness recommendation.",
        ],
        "evidenceRequired": [
            "Validated packet path",
            "Validator output path",
            "Dry-run summary path",
            "No provider call / no worker launch statement",
        ],
        "returnPath": str(return_path),
        "manifestPath": str(RUN_MANIFEST_DIR / "manifest.md"),
        "evidenceIndexPath": str(PATHS["evidence_index"]),
        "checkpointPath": str(PATHS["handoff"]),
        "routeRegistryPath": str(ROUTE_REGISTRY_PATH),
        "evidenceArtifactHashes": artifact_hashes,
        "requiredEcho": {
            "fields": ["packetVersion", "taskId", "inputDeliveryMethod", "targetSeat", "routeId"],
            "minHashEchoes": 2,
        },
        "returnFormat": "external-agent-review-output/v0.1",
        "timeoutPolicy": "dry-run packet only; no dispatch performed",
        "costPolicy": "zero provider spend in this dry-run",
        "humanApprovalRequiredFor": [
            "provider call",
            "O1/O2/O3 invocation",
            "L2 controlled worker",
            "L3 live backend",
            "config-write",
            "credential-write",
            "browser-state-write",
            "external-action",
            "destructive",
        ],
        "runtimeEnforcement": False,
    }
    write_json_atomic(packet_path, packet)
    validation = validate_external_packet(packet_path, validation_path)
    summary = {
        "schemaVersion": "fusion-adapter-dry-run/v0.1",
        "createdAt": now_iso(),
        "adapterId": adapter.get("id"),
        "runId": run_id,
        "mode": "dry-run",
        "providerCall": False,
        "workerLaunch": False,
        "credentialRead": False,
        "canonicalPacket": True,
        "packetPath": str(packet_path),
        "validationPath": str(validation_path),
        "validationOk": validation.get("ok"),
        "returnPath": str(return_path),
        "blockedActions": adapter.get("blockedActions", []),
        "outputs": [str(packet_path), str(validation_path), str(summary_path)],
    }
    write_json_atomic(summary_path, summary)
    return {
        "ok": bool(validation.get("ok")),
        "adapterId": adapter.get("id"),
        "runId": run_id,
        "runDir": str(run_dir),
        "packetPath": str(packet_path),
        "validationPath": str(validation_path),
        "summaryPath": str(summary_path),
        "providerCall": False,
        "workerLaunch": False,
        "credentialRead": False,
        "validationOk": validation.get("ok"),
        "validationRejectReason": (validation.get("validation") or {}).get("rejectReason"),
    }


def build_jcode_plan(adapter, run_dir, run_id):
    plan_path = run_dir / "jcode-execution-plan.json"
    risk_path = run_dir / "risk-review.md"
    cleanup_path = run_dir / "cleanup-plan.md"
    summary_path = run_dir / "adapter-dry-run-summary.json"
    plan = {
        "schemaVersion": "jcode-l1-dry-run-plan/v0.1",
        "createdAt": now_iso(),
        "adapterId": adapter.get("id"),
        "runId": run_id,
        "mode": "dry-run",
        "canonicalPacket": False,
        "canonicalBlocker": adapter.get("canonicalBlocker"),
        "jcodeMode": "dry-run",
        "wslDistro": "not-selected",
        "sandboxRoot": "not-created",
        "sandboxHome": "not-created",
        "workingDirectory": "not-selected",
        "providerProfile": "none",
        "model": "none",
        "providerBaseUrl": "none",
        "providerAuthMode": "none",
        "embeddingPolicy": "disabled",
        "serverMode": "forbidden",
        "resumeMode": "forbidden",
        "timeoutSeconds": 0,
        "cleanupKillPattern": "none; no process launched",
        "rawLogPolicy": "quarantine-only",
        "sanitizedReturnPath": str(run_dir / "jcode-sanitized-return-placeholder.md"),
        "blockedActions": adapter.get("blockedActions", []),
        "inputs": [str(path) for path in adapter_input_paths() if path.exists()],
    }
    write_json_atomic(plan_path, plan)
    risk_path.write_text(
        "\n".join([
            "# jcode L1 Dry-Run Risk Review",
            "",
            "- Verdict: not executable yet.",
            "- Reason: `jcode` is not in the canonical external-agent seat registry or packet schema targetSeat enum.",
            "- Windows normal-profile jcode use remains forbidden for integration tests.",
            "- Next safe step is schema/registry review plus WSL/ext4 dry-run sandbox design; no worker launch occurred.",
            "- No provider call, credential read, daemon/resume mode, or raw log publication occurred.",
            "",
        ]),
        encoding="utf-8",
    )
    cleanup_path.write_text(
        "\n".join([
            "# jcode L1 Dry-Run Cleanup Plan",
            "",
            "- No cleanup required for this run: no jcode process was launched.",
            "- Future L2 candidate must define WSL process kill pattern, sandbox directory removal, raw-log quarantine, and post-run protected-zone diff.",
            "- Do not touch the user's normal jcode profile during integration tests.",
            "",
        ]),
        encoding="utf-8",
    )
    summary = {
        "schemaVersion": "fusion-adapter-dry-run/v0.1",
        "createdAt": now_iso(),
        "adapterId": adapter.get("id"),
        "runId": run_id,
        "mode": "dry-run",
        "providerCall": False,
        "workerLaunch": False,
        "credentialRead": False,
        "canonicalPacket": False,
        "canonicalBlocker": adapter.get("canonicalBlocker"),
        "planPath": str(plan_path),
        "riskPath": str(risk_path),
        "cleanupPath": str(cleanup_path),
        "outputs": [str(plan_path), str(risk_path), str(cleanup_path), str(summary_path)],
    }
    write_json_atomic(summary_path, summary)
    return {
        "ok": True,
        "adapterId": adapter.get("id"),
        "runId": run_id,
        "runDir": str(run_dir),
        "planPath": str(plan_path),
        "riskPath": str(risk_path),
        "cleanupPath": str(cleanup_path),
        "summaryPath": str(summary_path),
        "providerCall": False,
        "workerLaunch": False,
        "credentialRead": False,
        "canonicalPacket": False,
        "canonicalBlocker": adapter.get("canonicalBlocker"),
    }


def run_adapter_dry_run(adapter_id):
    adapter = adapter_by_id(adapter_id)
    if not adapter:
        return {"ok": False, "error": "unknown adapter", "adapterId": adapter_id}
    if adapter.get("mode") != "dry-run":
        return {"ok": False, "error": "only dry-run adapters are enabled", "adapterId": adapter_id}
    run_id, run_dir = ensure_adapter_run_dir(adapter_id)
    if adapter_id == "o_review_l1_packet":
        return build_o_review_packet(adapter, run_dir, run_id)
    if adapter_id == "jcode_l1_plan":
        return build_jcode_plan(adapter, run_dir, run_id)
    return {"ok": False, "error": "adapter has no dry-run handler", "adapterId": adapter_id, "runDir": str(run_dir)}


def task_template(template_key):
    return TASK_TEMPLATES.get(template_key)


def task_packet_text(task, template):
    lines = [
        f"# {task['title']}",
        "",
        f"- Task ID: `{task['id']}`",
        f"- Template: `{task['template']}`",
        f"- Status: `{task['status']}`",
        f"- Owner seat: `{task['ownerSeat']}`",
        f"- Created at: `{task['createdAt']}`",
        f"- Updated at: `{task['updatedAt']}`",
        "",
        "## Goal",
        template["description"],
        "",
        "## Next action",
        template["nextAction"],
        "",
        "## Evidence roots",
    ]
    for root in template.get("evidenceRoots", []):
        lines.append(f"- {root}")
    lines.extend([
        "",
        "## Checklist",
    ])
    for item in template.get("checklist", []):
        lines.append(f"- [ ] {item}")
    lines.extend([
        "",
        "## Boundary",
    ])
    boundary_items = template.get("boundary") or [
        "Local-only packet. It does not read credentials, call providers, or mutate Harness config.",
        "Update the packet only through the controller-backed task API.",
    ]
    for item in boundary_items:
        lines.append(f"- {item}")
    room = task.get("roomSnapshot")
    if isinstance(room, dict):
        lines.extend([
            "",
            "## Workflow room",
            f"- Room ID: `{room.get('id', 'unknown')}`",
            f"- Mode: `{room.get('mode', 'unknown')}`",
            f"- Status: `{room.get('status', 'unknown')}`",
            f"- Authority layer: `{room.get('authorityLayer', 'unknown')}`",
            f"- Truth source: `{room.get('truthSource', 'unknown')}`",
            f"- Workflow contract: `{room.get('workflowContract', 'unknown')}`",
            "",
            "## Room members",
        ])
        for member in room.get("members", []):
            if not isinstance(member, dict):
                continue
            lines.append(
                "- "
                + f"`{member.get('seatId', 'unknown')}`"
                + f" / {member.get('label', 'n/a')}"
                + f" / kind={member.get('kind', 'n/a')}"
                + f" / roomMode={member.get('roomMode', 'n/a')}"
                + f" / permission={member.get('permissionClass', 'n/a')}"
                + f" / status={member.get('status', 'n/a')}"
            )
        lines.extend([
            "",
            "## Room entry rules",
        ])
        for item in room.get("entryRules", []):
            lines.append(f"- {item}")
        lines.extend([
            "",
            "## Room forbidden actions",
        ])
        for item in room.get("forbiddenActions", []):
            lines.append(f"- {item}")
        lines.extend([
            "",
            "## Room next safe actions",
        ])
        for item in room.get("nextSafeActions", []):
            lines.append(f"- {item}")
    history = task.get("history") or []
    if history:
        lines.extend([
            "",
            "## History",
        ])
        for entry in history:
            lines.append(f"- {entry.get('at', '')} :: {entry.get('status', '')} :: {entry.get('note', '')}")
    return "\n".join(lines) + "\n"


def create_task_from_template(template_key):
    template = task_template(template_key)
    if not template:
        return {"ok": False, "error": "unknown template"}
    ensure_task_dir()
    store = read_task_store()
    tasks = store["tasks"]
    stamp = now_iso()
    base_id = f"task-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{template_key.replace('_', '-')}"
    task_id = base_id
    suffix = 2
    existing_ids = {task.get("id") for task in tasks}
    while task_id in existing_ids:
        task_id = f"{base_id}-{suffix}"
        suffix += 1
    packet_path = TASK_DIR / f"{task_id}.md"
    task = {
        "id": task_id,
        "template": template_key,
        "title": template["title"],
        "ownerSeat": template["ownerSeat"],
        "status": "queued",
        "description": template["description"],
        "nextAction": template["nextAction"],
        "evidenceRoots": template.get("evidenceRoots", []),
        "checklist": template.get("checklist", []),
        "createdAt": stamp,
        "updatedAt": stamp,
        "history": [{"at": stamp, "status": "queued", "note": "created"}],
        "packetPath": str(packet_path),
    }
    packet_path.write_text(task_packet_text(task, template), encoding="utf-8")
    tasks.insert(0, task)
    write_json_atomic(TASKS_PATH, {"version": 1, "updatedAt": stamp, "tasks": tasks})
    append_event("task_create", {"template": template_key, "taskId": task_id, "packetPath": str(packet_path)})
    return {"ok": True, "task": task, "packetPath": str(packet_path)}


def create_room_kickoff_task(room_id):
    room = room_by_id(room_id)
    if not room:
        return {"ok": False, "error": "room not found"}
    ensure_task_dir()
    store = read_task_store()
    tasks = store["tasks"]
    stamp = now_iso()
    safe_room_id = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in room_id).strip("-") or "room"
    base_id = f"task-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{safe_room_id}-kickoff"
    task_id = base_id
    suffix = 2
    existing_ids = {task.get("id") for task in tasks}
    while task_id in existing_ids:
        task_id = f"{base_id}-{suffix}"
        suffix += 1
    packet_path = TASK_DIR / f"{task_id}.md"
    template = {
        "title": f"Workflow Room kickoff: {room.get('title') or room_id}",
        "ownerSeat": room.get("authorityLayer") or "Harness",
        "description": (
            "Create the first L1 workflow-room packet. This invites listed seats "
            "to operate under the room contract without granting live execution."
        ),
        "nextAction": (
            "Review room membership, contract, protected zones, and evidence duties; "
            "then ask Opus 4.8 whether this room contract is ready for L1 adoption."
        ),
        "evidenceRoots": [
            str(ROOMS_REGISTRY_PATH),
            str(ROOT / "docs" / "workflow-room-v0.1.md"),
            str(TASKS_PATH),
        ],
        "checklist": [
            "Confirm every member has a normalMode and roomMode.",
            "Confirm runtimeEnforcement remains false for L1.",
            "Confirm forbidden actions include credentials, browser state, config, startup, provider calls, and live CLI dispatch.",
            "Confirm returned work must land in task packets, manifests, evidence indexes, or review outputs.",
            "Do not dispatch live agents until a separate L2 gate exists.",
        ],
        "boundary": [
            "This kickoff writes a local task packet only.",
            "It does not start providers, CLIs, browsers, containers, or external dispatch.",
            "It does not grant write authority beyond the local task packet.",
        ],
    }
    task = {
        "id": task_id,
        "template": "workflow_room_kickoff",
        "title": template["title"],
        "ownerSeat": template["ownerSeat"],
        "status": "queued",
        "description": template["description"],
        "nextAction": template["nextAction"],
        "evidenceRoots": template.get("evidenceRoots", []),
        "checklist": template.get("checklist", []),
        "roomId": room_id,
        "roomSnapshot": room,
        "createdAt": stamp,
        "updatedAt": stamp,
        "history": [{"at": stamp, "status": "queued", "note": "room kickoff packet created"}],
        "packetPath": str(packet_path),
    }
    packet_path.write_text(task_packet_text(task, template), encoding="utf-8")
    tasks.insert(0, task)
    write_json_atomic(TASKS_PATH, {"version": 1, "updatedAt": stamp, "tasks": tasks})
    append_event("room_kickoff_task_create", {"roomId": room_id, "taskId": task_id, "packetPath": str(packet_path)})
    return {"ok": True, "roomId": room_id, "task": task, "packetPath": str(packet_path)}


def join_room_member(room_id, seat_id, role, task_packet_context):
    registry = read_rooms_registry()
    room = None
    for r in registry.get("rooms", []):
        if r.get("id") == room_id:
            room = r
            break
    if not room:
        return {"ok": False, "error": "room not found"}

    gstack_policy = room.get("siteWorkflowBinding", {}).get("gstackRoomModelPolicy", {})
    allowed_roles = gstack_policy.get("allowedJoinRoles", [])
    if role not in allowed_roles:
        return {"ok": False, "error": f"role {role} not allowed, must be one of {allowed_roles}"}

    member = None
    for m in room.get("members", []):
        if m.get("seatId") == seat_id:
            member = m
            break
    if not member:
        return {"ok": False, "error": "seat not found in room members"}

    stamp = now_iso()
    member["role"] = role
    member["status"] = "busy"
    member["currentTask"] = f"Joined room as {role}."
    member["lastActivityAt"] = stamp

    write_json_atomic(ROOMS_REGISTRY_PATH, registry)

    ledger_entry = {
        "schemaVersion": "workflow-run-ledger/v0.1",
        "runId": f"run-{datetime.now().strftime('%Y%m%d-%H%M%S')}-join-{seat_id}",
        "roomId": room_id,
        "status": "complete",
        "authorityLayer": room.get("authorityLayer") or "Harness files",
        "truthSource": room.get("truthSource") or "run-manifest + evidence-index",
        "startedAt": stamp,
        "endedAt": stamp,
        "liveDispatch": False,
        "remoteExposure": {
            "cloudflareTunnel": False,
            "mutatingRoutesExposed": False,
            "authRequired": True
        },
        "siteWorkflowBinding": {
            "inheritsSiteWorkflowConsole": True,
            "normalThreadRulesPreserved": True,
            "siteDirectCliAllowed": False,
            "uiIsTruthSource": False,
            "evidenceLevel": "review_packet",
            "requiredArtifacts": ["task packet", "run manifest", "evidence index", "validator report", "review packet", "captured review response", "delivery log", "verification summary"],
            "protectedActionPolicy": {
                "approvalManifestRequiredForProtectedActions": True,
                "hashBoundApprovalRequired": True,
                "protectedActionLedgerRequired": True
            }
        },
        "artifacts": {
            "manifestPath": "",
            "evidenceIndexPath": "",
            "taskPacketPaths": []
        },
        "stopCondition": f"Member {seat_id} joined as {role}."
    }

    RUN_LEDGER_PATH = Path("runs/workflow-run-ledger.jsonl")
    RUN_LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with RUN_LEDGER_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(ledger_entry, ensure_ascii=False) + "\n")

    return {"ok": True, "roomId": room_id, "seatId": seat_id, "role": role}


def assign_room_task(room_id, seat_id, title, description, allowed_files, test_commands):
    registry = read_rooms_registry()
    room = None
    for r in registry.get("rooms", []):
        if r.get("id") == room_id:
            room = r
            break
    if not room:
        return {"ok": False, "error": "room not found"}

    member = None
    for m in room.get("members", []):
        if m.get("seatId") == seat_id:
            member = m
            break
    if not member:
        return {"ok": False, "error": f"seat {seat_id} not found in room members"}

    stamp = now_iso()
    ensure_task_dir()
    store = read_task_store()
    tasks = store["tasks"]
    safe_title = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in title).strip("-") or "task"
    task_id = f"task-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{safe_title}"
    branch_name = f"room/{room_id}/{seat_id}/{safe_title.lower()}"
    packet_path = TASK_DIR / f"{task_id}.md"
    template = {
        "description": description,
        "nextAction": "Perform implementation, verify with test commands, and push evidence.",
        "evidenceRoots": [str(packet_path)] + [str(Path(f)) for f in allowed_files],
        "checklist": [f"Modify allowed files: {allowed_files}", f"Run test commands: {test_commands}"],
        "boundary": [
            f"Commit only to branch: {branch_name}",
            "Write operations are restricted to allowed files.",
            "Do not merge, push to main, or call external provider APIs."
        ]
    }

    task = {
        "id": task_id,
        "template": "assigned_room_task",
        "title": title,
        "ownerSeat": seat_id,
        "status": "in_progress",
        "description": description,
        "nextAction": template["nextAction"],
        "evidenceRoots": template["evidenceRoots"],
        "checklist": template["checklist"],
        "roomId": room_id,
        "roomSnapshot": room,
        "createdAt": stamp,
        "updatedAt": stamp,
        "history": [{"at": stamp, "status": "in_progress", "note": "task assigned in room"}],
        "packetPath": str(packet_path),
        "branch": branch_name,
        "allowedFiles": allowed_files,
        "testCommands": test_commands
    }

    member["status"] = "busy"
    member["currentTask"] = title
    member["branchWorktree"] = f"{branch_name} / C:\\html\\sit-kanwas-fusion-dashboard"
    member["lastActivityAt"] = stamp

    packet_path.write_text(task_packet_text(task, template), encoding="utf-8")
    tasks.insert(0, task)
    write_json_atomic(TASKS_PATH, {"version": 1, "updatedAt": stamp, "tasks": tasks})
    write_json_atomic(ROOMS_REGISTRY_PATH, registry)

    append_event("room_task_assigned", {"roomId": room_id, "seatId": seat_id, "taskId": task_id, "branch": branch_name})
    return {"ok": True, "task": task, "packetPath": str(packet_path)}


def push_task_evidence(task_id, evidence_path, test_logs):
    store = read_task_store()
    tasks = store["tasks"]
    task = None
    for item in tasks:
        if item.get("id") == task_id:
            task = item
            break
    if not task:
        return {"ok": False, "error": "task not found"}

    stamp = now_iso()
    sha256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    ev_file = Path(evidence_path)
    if ev_file.exists():
        try:
            hasher = hashlib.sha256()
            with ev_file.open("rb") as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)
            sha256 = hasher.hexdigest()
        except Exception:
            pass

    task["status"] = "complete"
    task["updatedAt"] = stamp
    task["completedAt"] = stamp
    task["evidencePath"] = evidence_path
    task["evidenceSha256"] = sha256
    task["testLogs"] = test_logs

    history = task.setdefault("history", [])
    history.append({"at": stamp, "status": "complete", "note": f"evidence pushed: {evidence_path}"})

    write_json_atomic(TASKS_PATH, {"version": 1, "updatedAt": stamp, "tasks": tasks})

    room_id = task.get("roomId")
    if room_id:
        registry = read_rooms_registry()
        for r in registry.get("rooms", []):
            if r.get("id") == room_id:
                for member in r.get("members", []):
                    if member.get("seatId") == task.get("ownerSeat"):
                        member["status"] = "available"
                        member["currentTask"] = f"Finished task: {task.get('title')}"
                        member["latestEvidence"] = evidence_path
                        member["lastActivityAt"] = stamp
                        break
        write_json_atomic(ROOMS_REGISTRY_PATH, registry)

    append_event("task_evidence_pushed", {"taskId": task_id, "evidencePath": evidence_path, "sha256": sha256})
    return {"ok": True, "taskId": task_id, "sha256": sha256}


def exit_room_member(room_id, seat_id, exit_type, exit_packet):
    registry = read_rooms_registry()
    room = None
    for r in registry.get("rooms", []):
        if r.get("id") == room_id:
            room = r
            break
    if not room:
        return {"ok": False, "error": "room not found"}

    member = None
    for m in room.get("members", []):
        if m.get("seatId") == seat_id:
            member = m
            break
    if not member:
        return {"ok": False, "error": "seat not found in room members"}

    stamp = now_iso()
    member["status"] = "available" if exit_type != "archive" else "archived"
    member["currentTask"] = f"Exited room via {exit_type}."
    member["lastActivityAt"] = stamp
    member["branchWorktree"] = ""

    write_json_atomic(ROOMS_REGISTRY_PATH, registry)

    ledger_entry = {
        "schemaVersion": "workflow-run-ledger/v0.1",
        "runId": f"run-{datetime.now().strftime('%Y%m%d-%H%M%S')}-exit-{seat_id}",
        "roomId": room_id,
        "status": "complete",
        "authorityLayer": room.get("authorityLayer") or "Harness files",
        "truthSource": room.get("truthSource") or "run-manifest + evidence-index",
        "startedAt": stamp,
        "endedAt": stamp,
        "liveDispatch": False,
        "remoteExposure": {
            "cloudflareTunnel": False,
            "mutatingRoutesExposed": False,
            "authRequired": True
        },
        "siteWorkflowBinding": {
            "inheritsSiteWorkflowConsole": True,
            "normalThreadRulesPreserved": True,
            "siteDirectCliAllowed": False,
            "uiIsTruthSource": False,
            "evidenceLevel": "review_packet",
            "requiredArtifacts": ["task packet", "run manifest", "evidence index", "validator report", "review packet", "captured review response", "delivery log", "verification summary"],
            "protectedActionPolicy": {
                "approvalManifestRequiredForProtectedActions": True,
                "hashBoundApprovalRequired": True,
                "protectedActionLedgerRequired": True
            }
        },
        "artifacts": {
            "manifestPath": "",
            "evidenceIndexPath": "",
            "taskPacketPaths": []
        },
        "stopCondition": f"Member {seat_id} exited: exitType={exit_type}."
    }

    RUN_LEDGER_PATH = Path("runs/workflow-run-ledger.jsonl")
    RUN_LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with RUN_LEDGER_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(ledger_entry, ensure_ascii=False) + "\n")

    append_event("room_member_exited", {"roomId": room_id, "seatId": seat_id, "exitType": exit_type})
    return {"ok": True, "roomId": room_id, "seatId": seat_id}


def propose_room_rule(room_id, proposed_rules, proposal_reason):
    registry = read_rooms_registry()
    room = None
    for r in registry.get("rooms", []):
        if r.get("id") == room_id:
            room = r
            break
    if not room:
        return {"ok": False, "error": "room not found"}

    stamp = now_iso()
    proposals = room.setdefault("ruleProposals", [])
    proposal = {
        "id": f"proposal-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        "proposedRules": proposed_rules,
        "proposalReason": proposal_reason,
        "createdAt": stamp,
        "status": "pending"
    }
    proposals.append(proposal)
    write_json_atomic(ROOMS_REGISTRY_PATH, registry)
    append_event("room_rule_proposed", {"roomId": room_id, "proposal": proposal})
    return {"ok": True, "roomId": room_id, "proposal": proposal}


def close_room_request(room_id, verdict, completed_items, open_items, handoff_path):
    registry = read_rooms_registry()
    room = None
    for r in registry.get("rooms", []):
        if r.get("id") == room_id:
            room = r
            break
    if not room:
        return {"ok": False, "error": "room not found"}

    stamp = now_iso()
    room["status"] = "waiting_user"
    room["closeRequest"] = {
        "verdict": verdict,
        "completedItems": completed_items,
        "openItems": open_items,
        "handoffPath": handoff_path,
        "requestedAt": stamp
    }

    write_json_atomic(ROOMS_REGISTRY_PATH, registry)

    ledger_entry = {
        "schemaVersion": "workflow-run-ledger/v0.1",
        "runId": f"run-{datetime.now().strftime('%Y%m%d-%H%M%S')}-close-{room_id}",
        "roomId": room_id,
        "status": "complete",
        "authorityLayer": room.get("authorityLayer") or "Harness files",
        "truthSource": room.get("truthSource") or "run-manifest + evidence-index",
        "startedAt": stamp,
        "endedAt": stamp,
        "liveDispatch": False,
        "remoteExposure": {
            "cloudflareTunnel": False,
            "mutatingRoutesExposed": False,
            "authRequired": True
        },
        "siteWorkflowBinding": {
            "inheritsSiteWorkflowConsole": True,
            "normalThreadRulesPreserved": True,
            "siteDirectCliAllowed": False,
            "uiIsTruthSource": False,
            "evidenceLevel": "review_packet",
            "requiredArtifacts": ["task packet", "run manifest", "evidence index", "validator report", "review packet", "captured review response", "delivery log", "verification summary"],
            "protectedActionPolicy": {
                "approvalManifestRequiredForProtectedActions": True,
                "hashBoundApprovalRequired": True,
                "protectedActionLedgerRequired": True
            }
        },
        "artifacts": {
            "manifestPath": handoff_path,
            "evidenceIndexPath": "",
            "taskPacketPaths": []
        },
        "stopCondition": f"Room close requested: verdict={verdict}."
    }

    RUN_LEDGER_PATH = Path("runs/workflow-run-ledger.jsonl")
    RUN_LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
    with RUN_LEDGER_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(ledger_entry, ensure_ascii=False) + "\n")

    append_event("room_close_requested", {"roomId": room_id, "verdict": verdict})
    return {"ok": True, "roomId": room_id}


def update_task_state(task_id, new_state):
    if new_state not in {"queued", "in_progress", "blocked", "complete"}:
        return {"ok": False, "error": "invalid task status"}
    store = read_task_store()
    tasks = store["tasks"]
    task = None
    for item in tasks:
        if item.get("id") == task_id:
            task = item
            break
    if not task:
        return {"ok": False, "error": "task not found"}
    stamp = now_iso()
    task["status"] = new_state
    task["updatedAt"] = stamp
    history = task.setdefault("history", [])
    history.append({"at": stamp, "status": new_state, "note": "state changed"})
    if new_state == "complete":
        task["completedAt"] = stamp
    else:
        task.pop("completedAt", None)
    if task.get("template") == "workflow_room_kickoff" and isinstance(task.get("roomSnapshot"), dict):
        template = {
            "title": task.get("title", "Workflow Room kickoff"),
            "ownerSeat": task.get("ownerSeat", "Harness"),
            "description": task.get("description", ""),
            "nextAction": task.get("nextAction", ""),
            "evidenceRoots": task.get("evidenceRoots", []),
            "checklist": task.get("checklist", []),
            "boundary": [
                "This kickoff writes a local task packet only.",
                "It does not start providers, CLIs, browsers, containers, or external dispatch.",
                "It does not grant write authority beyond the local task packet.",
            ],
        }
    else:
        template = task_template(task.get("template")) or TASK_TEMPLATES["evidence_closeout"]
    packet_path = Path(task.get("packetPath") or (TASK_DIR / f"{task_id}.md"))
    ensure_task_dir()
    packet_path.write_text(task_packet_text(task, template), encoding="utf-8")
    write_json_atomic(TASKS_PATH, {"version": 1, "updatedAt": stamp, "tasks": tasks})
    append_event("task_state", {"taskId": task_id, "status": new_state, "packetPath": str(packet_path)})
    return {"ok": True, "task": task, "packetPath": str(packet_path)}


def task_summary(tasks):
    counts = {"queued": 0, "in_progress": 0, "blocked": 0, "complete": 0}
    for task in tasks:
        status = task.get("status", "queued")
        if status in counts:
            counts[status] += 1
        else:
            counts["queued"] += 1
    return counts


def run_ps(script, timeout=15):
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    return {
        "exitCode": completed.returncode,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def assert_within_root(path, root, label):
    resolved_path = Path(path).resolve()
    resolved_root = Path(root).resolve()
    try:
        resolved_path.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f"{label} must stay within {resolved_root}") from exc
    return resolved_path


def assert_existing_root(path, label):
    resolved_path = Path(path).resolve()
    if not resolved_path.exists():
        raise FileNotFoundError(f"{label} root missing")
    return resolved_path


def port_owner_process(port):
    script = (
        f"$c = Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort {port} -State Listen -ErrorAction SilentlyContinue | "
        "Select-Object -First 1; "
        "if (-not $c) { '{}' } else { "
        "$p = Get-CimInstance Win32_Process -Filter \"ProcessId=$($c.OwningProcess)\"; "
        "[pscustomobject]@{ ProcessId=$p.ProcessId; Name=$p.Name; ExecutablePath=$p.ExecutablePath; CommandLine=$p.CommandLine } | ConvertTo-Json -Compress }"
    )
    result = run_ps(script)
    if result["exitCode"] != 0 or not result["stdout"] or result["stdout"] == "{}":
        return None
    try:
        return json.loads(result["stdout"])
    except Exception:
        return None


def safe_process_summary(process):
    if not process:
        return None
    command = process.get("CommandLine") or ""
    return {
        "processId": process.get("ProcessId"),
        "name": process.get("Name"),
        "executablePath": process.get("ExecutablePath"),
        "commandLineHint": command[:260],
    }


def public_process_summary(process):
    if not process:
        return None
    return {
        "processId": process.get("ProcessId"),
        "name": process.get("Name"),
    }


def run_command_background(name, command, cwd):
    ensure_log_dir()
    stdout_path = LOG_DIR / f"{name}.out.log"
    stderr_path = LOG_DIR / f"{name}.err.log"
    stdout = stdout_path.open("ab")
    stderr = stderr_path.open("ab")
    proc = subprocess.Popen(
        command,
        cwd=str(cwd),
        stdout=stdout,
        stderr=stderr,
        shell=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return {
        "pid": proc.pid,
        "stdout": str(stdout_path),
        "stderr": str(stderr_path),
    }


def docker_compose_status():
    if not KANWAS_ROOT.exists():
        return {"ok": False, "error": "kanwas root missing"}
    completed = subprocess.run(
        ["docker", "compose", "--profile", "app", "ps", "--all"],
        cwd=str(KANWAS_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=20,
    )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    return {
        "ok": completed.returncode == 0,
        "exitCode": completed.returncode,
        "summary": lines[:12],
        "stderrHint": completed.stderr.strip()[:500],
    }


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        try:
            return json.loads(path.read_text(encoding="utf-16"))
        except Exception as exc:
            return {"error": str(exc)}


def summarize_stage10d():
    result = read_json(PATHS["stage10d_result"])
    worker_text = ""
    try:
        worker_text = PATHS["stage10d_worker"].read_text(encoding="utf-8-sig")
    except Exception:
        worker_text = ""
    return {
        "status": result.get("status"),
        "workerExitCode": result.get("workerExitCode"),
        "providerModel": result.get("providerModel"),
        "gatewayBind": result.get("gatewayBind"),
        "returnSha256": result.get("returnSha256"),
        "leakHitCount": result.get("leakHitCount"),
        "gatewayHealth200": "gateway health | 200" in worker_text,
        "providerSmoke200": "provider smoke via gateway | 200" in worker_text,
        "providerOk": "providerOk=true" in worker_text,
        "contentMatchedExpected": "contentMatchedExpected=true" in worker_text,
    }


def file_summary(path):
    exists = path.exists()
    return {
        "path": str(path),
        "exists": exists,
        "sha256": sha256(path) if exists and path.is_file() else None,
    }


def public_file_summary(path):
    exists = path.exists()
    return {
        "name": path.name,
        "exists": exists,
        "sha256": sha256(path) if exists and path.is_file() else None,
    }


def gate_payload(include_sensitive=False):
    summarize_file = file_summary if include_sensitive else public_file_summary
    registry_validation = read_json(REGISTRY_VALIDATION_PATH) if REGISTRY_VALIDATION_PATH.exists() else {}
    dispatch_draft = read_json(DISPATCH_DRAFT_PATH) if DISPATCH_DRAFT_PATH.exists() else {}
    dispatch_validation = read_json(DISPATCH_VALIDATION_PATH) if DISPATCH_VALIDATION_PATH.exists() else {}
    dispatch_states = [item.get("state") for item in dispatch_draft.get("statusHistory", []) if isinstance(item, dict)]
    registry_ok = bool(registry_validation.get("ok"))
    dispatch_ok = bool(dispatch_validation.get("ok"))
    sent_manually = bool(dispatch_validation.get("sentManually"))
    review_outputs_count = int(dispatch_validation.get("reviewOutputsCount") or 0)
    jcode_canonical = False
    jcode_blocker = None
    for adapter in read_adapter_registry().get("adapters", []):
        if isinstance(adapter, dict) and adapter.get("id") == "jcode_l1_plan":
            jcode_canonical = bool(adapter.get("canonicalPacket"))
            jcode_blocker = adapter.get("canonicalBlocker")
            break
    return {
        "ok": True,
        "createdAt": now_iso(),
        "approvalPhrase": "APPROVE_FUSION_PHASE1_O_REVIEW_DISPATCH",
        "gates": {
            "registryContract": {
                "label": "Adapter registry contract",
                "status": "present" if REGISTRY_CONTRACT_PATH.exists() else "missing",
                "file": summarize_file(REGISTRY_CONTRACT_PATH),
            },
            "registryValidation": {
                "label": "Registry validation",
                "status": "passed" if registry_ok else "blocked",
                "ok": registry_ok,
                "rejectReason": registry_validation.get("rejectReason", []),
                "warning": registry_validation.get("warnings", []),
                "file": summarize_file(REGISTRY_VALIDATION_PATH),
            },
            "oReviewDispatch": {
                "label": "O-review dispatch",
                "status": "approval-ready-not-sent" if dispatch_ok and not sent_manually else "needs-review",
                "schemaValid": dispatch_ok,
                "states": dispatch_states,
                "sentManually": sent_manually,
                "reviewOutputsCount": review_outputs_count,
                "runtimeEnforcementGranted": bool(dispatch_validation.get("runtimeEnforcementGranted")),
                "providerCallMadeByThisValidation": bool(dispatch_validation.get("providerCallMadeByThisValidation")),
                "draft": summarize_file(DISPATCH_DRAFT_PATH),
                "validation": summarize_file(DISPATCH_VALIDATION_PATH),
                "prep": summarize_file(DISPATCH_PREP_PATH),
                "synthesisPlaceholder": summarize_file(DISPATCH_SYNTHESIS_PLACEHOLDER_PATH),
            },
            "jcodeSeat": {
                "label": "jcode canonical seat",
                "status": "blocked-noncanonical" if not jcode_canonical else "canonical",
                "canonicalPacket": jcode_canonical,
                "blocker": jcode_blocker,
                "brief": summarize_file(JCODE_GATE_BRIEF_PATH),
            },
        },
        "blockedActions": [
            "O1/O2/O3 provider call without exact approval phrase",
            "jcode launch",
            "write to the user's normal jcode profile",
            "Docker/container mutation outside explicit Kanwas buttons",
            "browser profile or login-state mutation",
            "Codex config, MCP registration, startup task, or credential-store mutation",
        ],
        "nextSafeActions": [
            "Read gate files from this panel",
            "Review/adopt adapter registry contract",
            "Approve closed-report O-review dispatch with the exact phrase if desired",
            "Review jcode seat brief before any schema or seat-registry promotion",
        ],
        "boundary": "Gate Center is read-only. It summarizes files and validation state; it does not dispatch O reviewers, launch jcode, call providers, read credentials, or grant runtime authority.",
    }


def status_payload(include_sensitive=False):
    store = read_task_store()
    tasks = store["tasks"]
    file_status = {}
    for key, path in PATHS.items():
        exists = path.exists()
        file_status[key] = public_file_summary(path)
        if include_sensitive:
            file_status[key].update({
                "path": str(path),
                "isDir": path.is_dir() if exists else False,
            })
    summarize_process = safe_process_summary if include_sensitive else public_process_summary
    return {
        "ok": True,
        "createdAt": now_iso(),
        "config": {
            "loaded": CONFIG_PATH.exists(),
            "error": CONFIG.get("_configError"),
            "featureFlags": FEATURE_FLAGS,
            "details": "full local paths are available only to same-origin workbench requests",
        },
        "ports": {
            "dashboard": {"url": URLS["dashboard"], "open": port_open(PORT)},
            "sit": {"url": URLS["sit"], "open": port_open(SIT_PORT), "owner": summarize_process(port_owner_process(SIT_PORT))},
            "kanwas": {"url": URLS["kanwas"], "open": port_open(KANWAS_PORT), "owner": summarize_process(port_owner_process(KANWAS_PORT))},
            "stage10dGateway": {"url": URLS["stage10dGateway"], "open": port_open(STAGE10D_GATEWAY_PORT)},
        },
        "kanwasCompose": docker_compose_status(),
        "stage10d": summarize_stage10d(),
        "gates": gate_payload(include_sensitive=include_sensitive),
        "taskQueue": {
            "path": str(TASKS_PATH),
            "count": len(tasks),
            "counts": task_summary(tasks),
            "templates": list(TASK_TEMPLATES.keys()),
        },
        "workflowRooms": room_summary(read_rooms_registry()),
        "adapters": {
            "registry": read_adapter_registry(),
        },
        "files": file_status,
        "actions": {
            "safe": [
                "refresh status",
                "kanwas_status",
                "tasks_list",
            ],
            "openTargets": ["open whitelisted URLs", "open whitelisted folders"] if FEATURE_FLAGS["openTargets"] else [],
            "processActions": ["start_sit", "stop_sit"] if FEATURE_FLAGS["processActions"] else [],
            "mutatingDocker": ["start_kanwas", "stop_kanwas"],
            "taskQueue": ["create_task", "task_state"],
            "workflowRooms": ["room_list", "room_kickoff_packet"],
            "adapterDryRun": ["o_review_l1_packet", "jcode_l1_plan"],
        },
        "boundary": "Controller v1. Fixed whitelist only. It never reads secrets, edits MCP/Codex config, mutates browser state, or starts provider calls. High-risk local actions are grouped behind local feature flags. Task queue writes local markdown packets and a local JSON store only.",
    }


def open_target(kind, name):
    if not FEATURE_FLAGS["openTargets"]:
        return {"ok": False, "error": "open target actions disabled by local feature flag"}
    if kind == "url":
        target = URLS.get(name)
        if not target:
            return {"ok": False, "error": "unknown url target"}
        subprocess.Popen(["cmd", "/c", "start", "", target], shell=False)
        return {"ok": True, "opened": target}
    if kind == "path":
        path = PATHS.get(name)
        if not path:
            return {"ok": False, "error": "unknown path target"}
        target = path if path.is_dir() else path.parent
        subprocess.Popen(["explorer.exe", str(target)], shell=False)
        return {"ok": True, "opened": str(target)}
    return {"ok": False, "error": "unknown open kind"}


def start_sit():
    if port_open(SIT_PORT):
        return {"ok": True, "alreadyRunning": True, "owner": safe_process_summary(port_owner_process(SIT_PORT))}
    try:
        sit_root = assert_existing_root(SIT_ROOT, "SIT")
    except (FileNotFoundError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}
    result = run_command_background(
        "sit-vite-dev",
        ["cmd.exe", "/c", "npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", str(SIT_PORT)],
        sit_root,
    )
    return {"ok": True, "started": "sit", **result}


def stop_sit():
    process = port_owner_process(SIT_PORT)
    if not process:
        return {"ok": True, "alreadyStopped": True}
    command = (process.get("CommandLine") or "").lower()
    executable = (process.get("ExecutablePath") or "").lower()
    if "vite" not in command and "node" not in executable:
        return {"ok": False, "error": f"port {SIT_PORT} owner does not look like SIT/Vite", "owner": safe_process_summary(process)}
    pid = process.get("ProcessId")
    result = run_ps(f"Stop-Process -Id {int(pid)} -Force", timeout=10)
    return {"ok": result["exitCode"] == 0, "stoppedPid": pid, "stderrHint": result["stderr"][:300]}


def run_docker_compose(action):
    try:
        kanwas_root = assert_existing_root(KANWAS_ROOT, "Kanwas")
    except (FileNotFoundError, ValueError) as exc:
        return {"ok": False, "error": str(exc)}
    ensure_log_dir()
    if action == "start_kanwas":
        command = ["docker", "compose", "--profile", "app", "up", "-d"]
        log_name = "kanwas-compose-up"
    elif action == "stop_kanwas":
        command = ["docker", "compose", "--profile", "app", "stop"]
        log_name = "kanwas-compose-stop"
    else:
        return {"ok": False, "error": "unknown docker action"}
    stdout_path = LOG_DIR / f"{log_name}.out.log"
    stderr_path = LOG_DIR / f"{log_name}.err.log"
    completed = subprocess.run(
        command,
        cwd=str(kanwas_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    stdout_path.write_text(completed.stdout, encoding="utf-8")
    stderr_path.write_text(completed.stderr, encoding="utf-8")
    return {
        "ok": completed.returncode == 0,
        "exitCode": completed.returncode,
        "stdout": str(stdout_path),
        "stderr": str(stderr_path),
        "summary": completed.stdout.strip().splitlines()[-12:],
        "stderrHint": completed.stderr.strip()[:500],
    }


def run_action(name):
    actions = {"kanwas_status": docker_compose_status}
    if FEATURE_FLAGS["processActions"]:
        actions.update({"start_sit": start_sit, "stop_sit": stop_sit})
    if FEATURE_FLAGS["dockerActions"]:
        actions.update({
            "start_kanwas": lambda: run_docker_compose("start_kanwas"),
            "stop_kanwas": lambda: run_docker_compose("stop_kanwas"),
        })
    func = actions.get(name)
    if not func:
        return {"ok": False, "error": "unknown action or disabled by local feature flag"}
    try:
        result = func()
    except subprocess.TimeoutExpired as exc:
        result = {"ok": False, "error": f"action timeout: {exc}"}
    except Exception as exc:
        result = {"ok": False, "error": str(exc)}
    append_event(name, result)
    return result


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        super().end_headers()

    def send_json(self, payload, status=200):
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_cookie(self):
        self.send_header(
            "Set-Cookie",
            f"{SESSION_COOKIE_NAME}={SESSION_TOKEN}; Path=/; HttpOnly; SameSite=Strict",
        )

    def send_json_with_cookie(self, payload, status=200):
        data = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_cookie()
        self.end_headers()
        self.wfile.write(data)

    def send_head(self):
        if urlparse(self.path).path == "/index.html":
            try:
                raw = (ROOT / "index.html").read_text(encoding="utf-8")
            except OSError:
                self.send_error(404, "File not found")
                return None
            bootstrap = (
                "<script>window.__FUSION_WORKBENCH_BOOTSTRAP__="
                + json.dumps({"hasSession": True}, ensure_ascii=False)
                + ";</script>"
            )
            body = raw.replace("<script>", bootstrap + "\n  <script>", 1)
            data = body.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_cookie()
            self.end_headers()
            import io

            return io.BytesIO(data)
        return super().send_head()

    def cookie_token(self):
        raw = self.headers.get("Cookie") or ""
        for part in raw.split(";"):
            name, _, value = part.strip().partition("=")
            if name == SESSION_COOKIE_NAME:
                return value
        return ""

    def is_workbench_request(self):
        origin = self.headers.get("Origin")
        referer = self.headers.get("Referer") or ""
        same_origin_referer = any(
            referer == allowed or referer.startswith(f"{allowed}/")
            for allowed in ALLOWED_ORIGINS
        )
        return (
            self.headers.get("X-Requested-With") == "fusion-workbench"
            and (not origin or origin in ALLOWED_ORIGINS)
            and same_origin_referer
        )

    def require_workbench_session(self):
        if not self.is_workbench_request():
            self.send_json({"ok": False, "error": "same-origin workbench request required"}, status=403)
            return False
        if not secrets.compare_digest(self.cookie_token(), SESSION_TOKEN):
            self.send_json({"ok": False, "error": "workbench session cookie required"}, status=403)
            return False
        return True

    def read_json_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        try:
            return json.loads(raw or "{}")
        except Exception:
            return None

    def require_mutating_workbench_request(self):
        origin = self.headers.get("Origin")
        if FEATURE_FLAGS["strictOrigin"] and (not origin or origin not in ALLOWED_ORIGINS):
            self.send_json({"ok": False, "error": "origin not allowed"}, status=403)
            return False
        if not self.require_workbench_session():
            return False
        return True

    def send_method_not_allowed(self, allowed):
        self.send_response(405)
        self.send_header("Allow", allowed)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        data = json.dumps({
            "ok": False,
            "error": f"use {allowed}",
            "boundary": "Mutating workbench routes are POST-only and require the same-origin workbench session cookie, workbench request header, and allowed Origin when strictOrigin is enabled.",
        }, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/session":
            self.send_json_with_cookie({
                "ok": True,
                "hasSession": True,
                "boundary": "HttpOnly same-origin workbench session cookie is set; no operator token is returned by this endpoint.",
            })
            return
        if parsed.path == "/api/status":
            self.send_json(status_payload(include_sensitive=self.is_workbench_request()))
            return
        if parsed.path == "/api/gates":
            self.send_json(gate_payload(include_sensitive=self.is_workbench_request()))
            return
        if parsed.path == "/api/tasks":
            if not self.require_workbench_session():
                return
            store = read_task_store()
            tasks = store["tasks"]
            self.send_json({
                "ok": True,
                "updatedAt": store["updatedAt"],
                "path": str(TASKS_PATH),
                "count": len(tasks),
                "counts": task_summary(tasks),
                "templates": TASK_TEMPLATES,
                "tasks": tasks,
            })
            return
        if parsed.path == "/api/rooms":
            if not self.require_workbench_session():
                return
            registry = read_rooms_registry()
            self.send_json({
                "ok": True,
                "registryPath": str(ROOMS_REGISTRY_PATH),
                "summary": room_summary(registry),
                "registry": registry,
            })
            return
        if parsed.path == "/api/adapters":
            if not self.require_workbench_session():
                return
            registry = read_adapter_registry()
            self.send_json({
                "ok": True,
                "registry": registry,
            })
            return
        if parsed.path.startswith("/api/task/create/"):
            self.send_method_not_allowed("POST")
            return
        if parsed.path.startswith("/api/task/") and parsed.path.endswith("/packet"):
            parts = parsed.path.strip("/").split("/")
            if len(parts) == 4:
                if not self.require_workbench_session():
                    return
                task_id = unquote(parts[2])
                store = read_task_store()
                task = next((item for item in store["tasks"] if item.get("id") == task_id), None)
                if not task:
                    self.send_json({"ok": False, "error": "task not found"}, status=404)
                    return
                try:
                    packet_path = assert_within_root(
                        task.get("packetPath") or (TASK_DIR / f"{task_id}.md"),
                        TASK_DIR,
                        "task packet",
                    )
                except ValueError as exc:
                    self.send_json({"ok": False, "error": str(exc)}, status=400)
                    return
                if not packet_path.exists():
                    self.send_json({"ok": False, "error": "packet missing"}, status=404)
                    return
                self.send_json({
                    "ok": True,
                    "taskId": task_id,
                    "packetPath": str(packet_path),
                    "content": packet_path.read_text(encoding="utf-8"),
                })
                return
            self.send_json({"ok": False, "error": "expected /api/task/<id>/packet"}, status=400)
            return
        if parsed.path.startswith("/api/action/"):
            self.send_method_not_allowed("POST")
            return
        if parsed.path.startswith("/api/open/"):
            self.send_method_not_allowed("POST")
            return
        if parsed.path.startswith("/api/adapter/"):
            self.send_method_not_allowed("POST")
            return
        if parsed.path.startswith("/api/room/"):
            self.send_method_not_allowed("POST")
            return
        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        if not self.require_mutating_workbench_request():
            return
        if parsed.path == "/api/tasks/create":
            if not FEATURE_FLAGS["taskWrites"]:
                self.send_json({"ok": False, "error": "task writes disabled by local feature flag"}, status=403)
                return
            body = self.read_json_body()
            if body is None:
                self.send_json({"ok": False, "error": "invalid JSON body"}, status=400)
                return
            template = (body.get("template") or "").strip()
            if not template:
                self.send_json({"ok": False, "error": "template required"}, status=400)
                return
            self.send_json(create_task_from_template(template))
            return
        if parsed.path.startswith("/api/task/") and parsed.path.endswith("/state"):
            if not FEATURE_FLAGS["taskWrites"]:
                self.send_json({"ok": False, "error": "task writes disabled by local feature flag"}, status=403)
                return
            parts = parsed.path.strip("/").split("/")
            if len(parts) == 4:
                task_id = unquote(parts[2])
                body = self.read_json_body()
                if body is None:
                    self.send_json({"ok": False, "error": "invalid JSON body"}, status=400)
                    return
                status_value = (body.get("status") or "").strip()
                result = update_task_state(task_id, status_value)
                self.send_json(result, status=200 if result.get("ok") else 400)
                return
            self.send_json({"ok": False, "error": "expected /api/task/<id>/state"}, status=400)
            return
        if parsed.path.startswith("/api/open/"):
            parts = parsed.path.strip("/").split("/")
            if len(parts) == 4:
                result = open_target(unquote(parts[2]), unquote(parts[3]))
                append_event("open_target", result, {"kind": unquote(parts[2]), "name": unquote(parts[3])})
                error = str(result.get("error") or "")
                status = 200 if result.get("ok") else 403 if "disabled" in error else 400
                self.send_json(result, status=status)
                return
            self.send_json({"ok": False, "error": "expected /api/open/<url|path>/<name>"}, status=400)
            return
        if parsed.path.startswith("/api/action/"):
            parts = parsed.path.strip("/").split("/")
            if len(parts) == 3:
                result = run_action(unquote(parts[2]))
                error = str(result.get("error") or "")
                status = 200 if result.get("ok") else 403 if "disabled" in error else 400
                self.send_json(result, status=status)
                return
            self.send_json({"ok": False, "error": "expected /api/action/<name>"}, status=400)
            return
        if parsed.path.startswith("/api/adapter/") and parsed.path.endswith("/dry-run"):
            if not FEATURE_FLAGS["adapterDryRun"]:
                self.send_json({"ok": False, "error": "adapter dry-run disabled by local feature flag"}, status=403)
                return
            parts = parsed.path.strip("/").split("/")
            if len(parts) == 4:
                adapter_id = unquote(parts[2])
                result = run_adapter_dry_run(adapter_id)
                append_event("adapter_dry_run", result, {"adapterId": adapter_id})
                self.send_json(result, status=200 if result.get("ok") else 400)
                return
            self.send_json({"ok": False, "error": "expected /api/adapter/<id>/dry-run"}, status=400)
            return
        if parsed.path.startswith("/api/room/") and parsed.path.endswith("/kickoff"):
            if not FEATURE_FLAGS["roomWrites"]:
                self.send_json({"ok": False, "error": "room writes disabled by local feature flag"}, status=403)
                return
            parts = parsed.path.strip("/").split("/")
            if len(parts) == 4:
                room_id = unquote(parts[2])
                result = create_room_kickoff_task(room_id)
                append_event("room_kickoff", result, {"roomId": room_id})
                self.send_json(result, status=200 if result.get("ok") else 400)
                return
            self.send_json({"ok": False, "error": "expected /api/room/<id>/kickoff"}, status=400)
            return
        if parsed.path.startswith("/api/room/") and parsed.path.endswith("/join"):
            if not FEATURE_FLAGS["roomWrites"]:
                self.send_json({"ok": False, "error": "room writes disabled by local feature flag"}, status=403)
                return
            parts = parsed.path.strip("/").split("/")
            if len(parts) == 4:
                room_id = unquote(parts[2])
                body = self.read_json_body()
                if body is None:
                    self.send_json({"ok": False, "error": "invalid JSON body"}, status=400)
                    return
                seat_id = body.get("seatId")
                role = body.get("role")
                task_packet_context = body.get("taskPacket")
                result = join_room_member(room_id, seat_id, role, task_packet_context)
                self.send_json(result, status=200 if result.get("ok") else 400)
                return
            self.send_json({"ok": False, "error": "expected /api/room/<id>/join"}, status=400)
            return
        if parsed.path.startswith("/api/room/") and parsed.path.endswith("/assign-task"):
            if not FEATURE_FLAGS["roomWrites"]:
                self.send_json({"ok": False, "error": "room writes disabled by local feature flag"}, status=403)
                return
            parts = parsed.path.strip("/").split("/")
            if len(parts) == 4:
                room_id = unquote(parts[2])
                body = self.read_json_body()
                if body is None:
                    self.send_json({"ok": False, "error": "invalid JSON body"}, status=400)
                    return
                seat_id = body.get("seatId")
                title = body.get("title")
                description = body.get("description")
                allowed_files = body.get("allowedFiles") or []
                test_commands = body.get("testCommands") or []
                result = assign_room_task(room_id, seat_id, title, description, allowed_files, test_commands)
                self.send_json(result, status=200 if result.get("ok") else 400)
                return
            self.send_json({"ok": False, "error": "expected /api/room/<id>/assign-task"}, status=400)
            return
        if parsed.path.startswith("/api/task/") and parsed.path.endswith("/evidence"):
            if not FEATURE_FLAGS["taskWrites"]:
                self.send_json({"ok": False, "error": "task writes disabled by local feature flag"}, status=403)
                return
            parts = parsed.path.strip("/").split("/")
            if len(parts) == 4:
                task_id = unquote(parts[2])
                body = self.read_json_body()
                if body is None:
                    self.send_json({"ok": False, "error": "invalid JSON body"}, status=400)
                    return
                evidence_path = body.get("evidencePath")
                test_logs = body.get("testLogs")
                result = push_task_evidence(task_id, evidence_path, test_logs)
                self.send_json(result, status=200 if result.get("ok") else 400)
                return
            self.send_json({"ok": False, "error": "expected /api/task/<id>/evidence"}, status=400)
            return
        if parsed.path.startswith("/api/room/") and parsed.path.endswith("/exit-seat"):
            if not FEATURE_FLAGS["roomWrites"]:
                self.send_json({"ok": False, "error": "room writes disabled by local feature flag"}, status=403)
                return
            parts = parsed.path.strip("/").split("/")
            if len(parts) == 4:
                room_id = unquote(parts[2])
                body = self.read_json_body()
                if body is None:
                    self.send_json({"ok": False, "error": "invalid JSON body"}, status=400)
                    return
                seat_id = body.get("seatId")
                exit_type = body.get("exitType")
                exit_packet = body.get("exitPacket")
                result = exit_room_member(room_id, seat_id, exit_type, exit_packet)
                self.send_json(result, status=200 if result.get("ok") else 400)
                return
            self.send_json({"ok": False, "error": "expected /api/room/<id>/exit-seat"}, status=400)
            return
        if parsed.path.startswith("/api/room/") and parsed.path.endswith("/propose-rule"):
            if not FEATURE_FLAGS["roomWrites"]:
                self.send_json({"ok": False, "error": "room writes disabled by local feature flag"}, status=403)
                return
            parts = parsed.path.strip("/").split("/")
            if len(parts) == 4:
                room_id = unquote(parts[2])
                body = self.read_json_body()
                if body is None:
                    self.send_json({"ok": False, "error": "invalid JSON body"}, status=400)
                    return
                proposed_rules = body.get("proposedRules")
                proposal_reason = body.get("proposalReason")
                result = propose_room_rule(room_id, proposed_rules, proposal_reason)
                self.send_json(result, status=200 if result.get("ok") else 400)
                return
            self.send_json({"ok": False, "error": "expected /api/room/<id>/propose-rule"}, status=400)
            return
        if parsed.path.startswith("/api/room/") and parsed.path.endswith("/close-request"):
            if not FEATURE_FLAGS["roomWrites"]:
                self.send_json({"ok": False, "error": "room writes disabled by local feature flag"}, status=403)
                return
            parts = parsed.path.strip("/").split("/")
            if len(parts) == 4:
                room_id = unquote(parts[2])
                body = self.read_json_body()
                if body is None:
                    self.send_json({"ok": False, "error": "invalid JSON body"}, status=400)
                    return
                verdict = body.get("verdict")
                completed_items = body.get("completedItems")
                open_items = body.get("openItems")
                handoff_path = body.get("handoffPath")
                result = close_room_request(room_id, verdict, completed_items, open_items, handoff_path)
                self.send_json(result, status=200 if result.get("ok") else 400)
                return
            self.send_json({"ok": False, "error": "expected /api/room/<id>/close-request"}, status=400)
            return
        self.send_json({"ok": False, "error": "unsupported POST route"}, status=404)

    def do_OPTIONS(self):
        self.send_method_not_allowed("GET, POST")


def main():
    os.chdir(ROOT)
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"controller listening on http://{HOST}:{PORT}/index.html", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)

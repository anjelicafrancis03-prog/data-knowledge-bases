import http.cookies
import json
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import controller


def serve_once():
    server = controller.ThreadingHTTPServer((controller.HOST, 0), controller.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, f"http://{controller.HOST}:{server.server_address[1]}"


def request_json(url, *, headers=None, data=None):
    body = None if data is None else json.dumps(data).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers=headers or {},
        method="GET" if body is None else "POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.status, response.headers, json.loads(response.read().decode("utf-8"))


def test_session_does_not_return_operator_token():
    server, base = serve_once()
    try:
        status, headers, payload = request_json(f"{base}/api/session")
    finally:
        server.shutdown()
    assert status == 200
    assert payload["ok"] is True
    assert "token" not in payload
    assert "tokenHeader" not in payload
    cookie = http.cookies.SimpleCookie(headers["Set-Cookie"])
    assert controller.SESSION_COOKIE_NAME in cookie
    assert cookie[controller.SESSION_COOKIE_NAME]["httponly"] is True


def test_public_status_strips_local_paths_and_command_lines(monkeypatch):
    monkeypatch.setattr(controller, "docker_compose_status", lambda: {"ok": True, "summary": []})
    monkeypatch.setattr(controller, "summarize_stage10d", lambda: {"status": "unknown"})
    monkeypatch.setattr(
        controller,
        "port_owner_process",
        lambda _port: {
            "ProcessId": 123,
            "Name": "node.exe",
            "ExecutablePath": "C:/secret/node.exe",
            "CommandLine": "node --secret local-path",
        },
    )
    server, base = serve_once()
    try:
        status, _, payload = request_json(f"{base}/api/status")
    finally:
        server.shutdown()
    assert status == 200
    assert "path" not in payload["config"]
    assert "registryPath" not in payload["adapters"]
    assert "dryRunRoot" not in payload["adapters"]
    assert all("path" not in item for item in payload["files"].values())
    assert "path" not in payload["gates"]["gates"]["registryContract"]["file"]
    for port in payload["ports"].values():
        owner = port.get("owner")
        if owner:
            assert "commandLineHint" not in owner
            assert "executablePath" not in owner


def test_public_gates_strip_local_paths():
    server, base = serve_once()
    try:
        status, _, payload = request_json(f"{base}/api/gates")
    finally:
        server.shutdown()
    assert status == 200
    assert payload["ok"] is True
    assert "path" not in payload["gates"]["registryContract"]["file"]
    assert "path" not in payload["gates"]["oReviewDispatch"]["draft"]


def test_workbench_read_routes_require_session_cookie():
    server, base = serve_once()
    try:
        request = urllib.request.Request(
            f"{base}/api/tasks",
            headers={
                "X-Requested-With": "fusion-workbench",
                "Referer": f"{base}/index.html",
            },
        )
        try:
            urllib.request.urlopen(request, timeout=10)
        except urllib.error.HTTPError as exc:
            assert exc.code == 403
        else:
            raise AssertionError("expected /api/tasks without cookie to be rejected")
    finally:
        server.shutdown()


def test_workbench_rooms_require_session_cookie():
    server, base = serve_once()
    try:
        request = urllib.request.Request(
            f"{base}/api/rooms",
            headers={
                "X-Requested-With": "fusion-workbench",
                "Referer": f"{base}/index.html",
            },
        )
        try:
            urllib.request.urlopen(request, timeout=10)
        except urllib.error.HTTPError as exc:
            assert exc.code == 403
        else:
            raise AssertionError("expected /api/rooms without cookie to be rejected")
    finally:
        server.shutdown()


def test_rooms_route_returns_registry_with_session(monkeypatch, tmp_path):
    rooms_dir = tmp_path / "rooms"
    rooms_dir.mkdir()
    rooms_registry = rooms_dir / "workflow-rooms.registry.json"
    rooms_registry.write_text(
        json.dumps({
            "schemaVersion": "workflow-rooms.registry/v0.1",
            "updatedAt": "test",
            "boundary": "test boundary",
            "rooms": [{
                "id": "test-room",
                "title": "Test Room",
                "status": "draft-active",
                "members": [{"seatId": "codex-control", "status": "available"}],
            }],
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(controller, "ROOMS_REGISTRY_PATH", rooms_registry)

    server, base = serve_once()
    try:
        monkeypatch.setattr(controller, "ALLOWED_ORIGINS", {base, f"http://localhost:{server.server_address[1]}"})
        _, session_headers, _ = request_json(f"{base}/api/session")
        cookie_header = session_headers["Set-Cookie"].split(";", 1)[0]
        status, _, payload = request_json(
            f"{base}/api/rooms",
            headers={
                "Cookie": cookie_header,
                "X-Requested-With": "fusion-workbench",
                "Referer": f"{base}/index.html",
            },
        )
    finally:
        server.shutdown()
    assert status == 200
    assert payload["ok"] is True
    assert payload["summary"]["count"] == 1
    assert payload["summary"]["memberCount"] == 1
    assert payload["registry"]["rooms"][0]["id"] == "test-room"


def test_room_kickoff_post_creates_task_packet(monkeypatch, tmp_path):
    task_dir = tmp_path / "tasks"
    task_store = tmp_path / "tasks.json"
    rooms_dir = tmp_path / "rooms"
    rooms_dir.mkdir()
    rooms_registry = rooms_dir / "workflow-rooms.registry.json"
    rooms_registry.write_text(
        json.dumps({
            "schemaVersion": "workflow-rooms.registry/v0.1",
            "updatedAt": "test",
            "boundary": "test boundary",
            "rooms": [{
                "id": "test-room",
                "title": "Test Room",
                "mode": "L1-packet-room",
                "status": "draft-active",
                "authorityLayer": "Harness files",
                "truthSource": "manifest",
                "workflowContract": "Thread-as-Agent, Room-as-Workflow v0.1",
                "members": [{"seatId": "codex-control", "label": "Codex", "roomMode": "control"}],
                "entryRules": ["enter by packet"],
                "forbiddenActions": ["no provider call"],
                "nextSafeActions": ["review"],
            }],
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(controller, "TASK_DIR", task_dir)
    monkeypatch.setattr(controller, "TASKS_PATH", task_store)
    monkeypatch.setattr(controller, "ROOMS_REGISTRY_PATH", rooms_registry)
    monkeypatch.setitem(controller.FEATURE_FLAGS, "roomWrites", True)

    server, base = serve_once()
    try:
        monkeypatch.setattr(controller, "ALLOWED_ORIGINS", {base, f"http://localhost:{server.server_address[1]}"})
        _, session_headers, _ = request_json(f"{base}/api/session")
        cookie_header = session_headers["Set-Cookie"].split(";", 1)[0]
        request = urllib.request.Request(
            f"{base}/api/room/test-room/kickoff",
            data=b"{}",
            headers={
                "Cookie": cookie_header,
                "Content-Type": "application/json",
                "Origin": base,
                "X-Requested-With": "fusion-workbench",
                "Referer": f"{base}/index.html",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
    finally:
        server.shutdown()
    assert payload["ok"] is True
    packet_path = Path(payload["packetPath"])
    assert packet_path.exists()
    assert packet_path.parent == task_dir
    packet_text = packet_path.read_text(encoding="utf-8")
    assert "Workflow Room kickoff" in packet_text
    assert "test-room" in packet_text
    assert "no provider call" in packet_text
    store = json.loads(task_store.read_text(encoding="utf-8"))
    assert store["tasks"][0]["roomId"] == "test-room"


def test_room_kickoff_post_is_feature_flagged_off_by_default(monkeypatch):
    monkeypatch.setitem(controller.FEATURE_FLAGS, "roomWrites", False)

    server, base = serve_once()
    try:
        monkeypatch.setattr(controller, "ALLOWED_ORIGINS", {base, f"http://localhost:{server.server_address[1]}"})
        _, session_headers, _ = request_json(f"{base}/api/session")
        cookie_header = session_headers["Set-Cookie"].split(";", 1)[0]
        request = urllib.request.Request(
            f"{base}/api/room/sit-kanwas-fusion-room/kickoff",
            data=b"{}",
            headers={
                "Cookie": cookie_header,
                "Content-Type": "application/json",
                "Origin": base,
                "X-Requested-With": "fusion-workbench",
                "Referer": f"{base}/index.html",
            },
            method="POST",
        )
        try:
            urllib.request.urlopen(request, timeout=10)
        except urllib.error.HTTPError as exc:
            assert exc.code == 403
            assert "room writes disabled" in exc.read().decode("utf-8")
        else:
            raise AssertionError("expected default-disabled roomWrites to reject kickoff")
    finally:
        server.shutdown()


def test_room_kickoff_post_rejects_bad_origin(monkeypatch):
    monkeypatch.setitem(controller.FEATURE_FLAGS, "roomWrites", True)

    server, base = serve_once()
    try:
        monkeypatch.setattr(controller, "ALLOWED_ORIGINS", {base, f"http://localhost:{server.server_address[1]}"})
        _, session_headers, _ = request_json(f"{base}/api/session")
        cookie_header = session_headers["Set-Cookie"].split(";", 1)[0]
        request = urllib.request.Request(
            f"{base}/api/room/sit-kanwas-fusion-room/kickoff",
            data=b"{}",
            headers={
                "Cookie": cookie_header,
                "Content-Type": "application/json",
                "Origin": "http://evil.invalid",
                "X-Requested-With": "fusion-workbench",
                "Referer": f"{base}/index.html",
            },
            method="POST",
        )
        try:
            urllib.request.urlopen(request, timeout=10)
        except urllib.error.HTTPError as exc:
            assert exc.code == 403
        else:
            raise AssertionError("expected bad-origin kickoff to be rejected")
    finally:
        server.shutdown()


def test_room_kickoff_get_is_rejected():
    server, base = serve_once()
    try:
        request = urllib.request.Request(f"{base}/api/room/sit-kanwas-fusion-room/kickoff")
        try:
            urllib.request.urlopen(request, timeout=10)
        except urllib.error.HTTPError as exc:
            assert exc.code == 405
        else:
            raise AssertionError("expected GET kickoff to be method-not-allowed")
    finally:
        server.shutdown()


def test_task_packet_route_rejects_out_of_root_packet_path(monkeypatch, tmp_path):
    task_dir = tmp_path / "tasks"
    task_dir.mkdir()
    outside_packet = tmp_path / "outside.md"
    outside_packet.write_text("do not leak", encoding="utf-8")
    task_store = tmp_path / "tasks.json"
    task_store.write_text(
        json.dumps({
            "version": 1,
            "updatedAt": "test",
            "tasks": [{
                "id": "task-outside",
                "template": "evidence_closeout",
                "status": "queued",
                "packetPath": str(outside_packet),
            }],
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(controller, "TASK_DIR", task_dir)
    monkeypatch.setattr(controller, "TASKS_PATH", task_store)

    server, base = serve_once()
    try:
        monkeypatch.setattr(controller, "ALLOWED_ORIGINS", {base, f"http://localhost:{server.server_address[1]}"})
        _, session_headers, _ = request_json(f"{base}/api/session")
        cookie_header = session_headers["Set-Cookie"].split(";", 1)[0]
        request = urllib.request.Request(
            f"{base}/api/task/task-outside/packet",
            headers={
                "Cookie": cookie_header,
                "X-Requested-With": "fusion-workbench",
                "Referer": f"{base}/index.html",
            },
        )
        try:
            urllib.request.urlopen(request, timeout=10)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8")
            assert exc.code == 400
            assert "task packet must stay within" in body
            assert "do not leak" not in body
        else:
            raise AssertionError("expected out-of-root packetPath to be rejected")
    finally:
        server.shutdown()


def test_gstack_room_operations(monkeypatch, tmp_path):
    task_dir = tmp_path / "tasks"
    task_store = tmp_path / "tasks.json"
    rooms_dir = tmp_path / "rooms"
    rooms_dir.mkdir()
    rooms_registry = rooms_dir / "workflow-rooms.registry.json"
    rooms_registry.write_text(
        json.dumps({
            "schemaVersion": "workflow-rooms.registry/v0.1",
            "updatedAt": "test",
            "boundary": "test boundary",
            "rooms": [{
                "id": "test-room",
                "title": "Test Room",
                "mode": "L1-packet-room",
                "status": "draft-active",
                "members": [
                    {
                        "seatId": "codex-control",
                        "status": "available",
                        "role": "control"
                    },
                    {
                        "seatId": "o3-review",
                        "status": "available",
                        "role": "reviewer"
                    }
                ],
                "siteWorkflowBinding": {
                    "gstackRoomModelPolicy": {
                        "allowedJoinRoles": ["orchestrator", "coder", "reviewer"]
                    }
                }
            }],
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr(controller, "TASK_DIR", task_dir)
    monkeypatch.setattr(controller, "TASKS_PATH", task_store)
    monkeypatch.setattr(controller, "ROOMS_REGISTRY_PATH", rooms_registry)
    monkeypatch.setitem(controller.FEATURE_FLAGS, "roomWrites", True)

    server, base = serve_once()
    try:
        monkeypatch.setattr(controller, "ALLOWED_ORIGINS", {base, f"http://localhost:{server.server_address[1]}"})
        _, session_headers, _ = request_json(f"{base}/api/session")
        cookie_header = session_headers["Set-Cookie"].split(";", 1)[0]

        # 1. Join Room POST test
        request = urllib.request.Request(
            f"{base}/api/room/test-room/join",
            data=json.dumps({"seatId": "o3-review", "role": "orchestrator"}).encode("utf-8"),
            headers={
                "Cookie": cookie_header,
                "Content-Type": "application/json",
                "Origin": base,
                "X-Requested-With": "fusion-workbench",
                "Referer": f"{base}/index.html",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
        assert payload["ok"] is True

        registry = json.loads(rooms_registry.read_text(encoding="utf-8"))
        assert registry["rooms"][0]["members"][1]["status"] == "busy"
        assert registry["rooms"][0]["members"][1]["role"] == "orchestrator"

        # 2. Assign Task POST test
        request = urllib.request.Request(
            f"{base}/api/room/test-room/assign-task",
            data=json.dumps({
                "seatId": "o3-review",
                "title": "Build Test Feature",
                "description": "Implement feature and verify.",
                "allowedFiles": ["controller.py"],
                "testCommands": ["pytest"]
            }).encode("utf-8"),
            headers={
                "Cookie": cookie_header,
                "Content-Type": "application/json",
                "Origin": base,
                "X-Requested-With": "fusion-workbench",
                "Referer": f"{base}/index.html",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
        assert payload["ok"] is True
        task_id = payload["task"]["id"]

        registry = json.loads(rooms_registry.read_text(encoding="utf-8"))
        assert registry["rooms"][0]["members"][1]["currentTask"] == "Build Test Feature"

        # 3. Push Evidence POST test
        dummy_file = tmp_path / "dummy_evidence.txt"
        dummy_file.write_text("verification pass info", encoding="utf-8")
        request = urllib.request.Request(
            f"{base}/api/task/{task_id}/evidence",
            data=json.dumps({
                "evidencePath": str(dummy_file),
                "testLogs": "all 4 tests passed"
            }).encode("utf-8"),
            headers={
                "Cookie": cookie_header,
                "Content-Type": "application/json",
                "Origin": base,
                "X-Requested-With": "fusion-workbench",
                "Referer": f"{base}/index.html",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
        assert payload["ok"] is True

        # Seat state should reset to available
        registry = json.loads(rooms_registry.read_text(encoding="utf-8"))
        assert registry["rooms"][0]["members"][1]["status"] == "available"

        # 4. Propose Rule POST test
        request = urllib.request.Request(
            f"{base}/api/room/test-room/propose-rule",
            data=json.dumps({
                "proposedRules": "Always write tests.",
                "proposalReason": "Testing requirement"
            }).encode("utf-8"),
            headers={
                "Cookie": cookie_header,
                "Content-Type": "application/json",
                "Origin": base,
                "X-Requested-With": "fusion-workbench",
                "Referer": f"{base}/index.html",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
        assert payload["ok"] is True
        registry = json.loads(rooms_registry.read_text(encoding="utf-8"))
        assert registry["rooms"][0]["ruleProposals"][0]["proposedRules"] == "Always write tests."

        # 5. Exit Room POST test
        request = urllib.request.Request(
            f"{base}/api/room/test-room/exit-seat",
            data=json.dumps({
                "seatId": "o3-review",
                "exitType": "resume"
            }).encode("utf-8"),
            headers={
                "Cookie": cookie_header,
                "Content-Type": "application/json",
                "Origin": base,
                "X-Requested-With": "fusion-workbench",
                "Referer": f"{base}/index.html",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
        assert payload["ok"] is True
        registry = json.loads(rooms_registry.read_text(encoding="utf-8"))
        assert registry["rooms"][0]["members"][1]["status"] == "available"

        # 6. Close Room Request POST test
        request = urllib.request.Request(
            f"{base}/api/room/test-room/close-request",
            data=json.dumps({
                "verdict": "success",
                "completedItems": ["review", "test"],
                "openItems": [],
                "handoffPath": "some/path.md"
            }).encode("utf-8"),
            headers={
                "Cookie": cookie_header,
                "Content-Type": "application/json",
                "Origin": base,
                "X-Requested-With": "fusion-workbench",
                "Referer": f"{base}/index.html",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
        assert payload["ok"] is True
        registry = json.loads(rooms_registry.read_text(encoding="utf-8"))
        assert registry["rooms"][0]["status"] == "waiting_user"
        assert registry["rooms"][0]["closeRequest"]["verdict"] == "success"

    finally:
        server.shutdown()

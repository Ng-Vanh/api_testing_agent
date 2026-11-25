# API Testing Tool — M1

Tool hiện có luồng CLI **OpenAPI → preflight → ca GET → HTTP → kiểm tra contract → báo cáo JSON**, cùng khung FastAPI, UI React, contract Pydantic và lưu trữ SQLite/JSONL. Web API hiện có health; quản lý job và UI chạy testcase thuộc T10/T11. [Kế hoạch](../tasks/plan.md) và [checklist](../tasks/todo.md).

## Cài đặt bằng conda

Backend cần **Python 3.12.x**. Môi trường đã dùng để kiểm chứng local: `apitesting`, Python 3.12.16. Không cần tạo thêm venv.

Linux (bash), từ gốc repo:

```bash
conda activate apitesting
cd tool/backend
python --version
python -m pip install -r requirements-dev.lock
```

Windows: dùng **Anaconda Prompt** hoặc shell đã chạy `conda init`, sau đó dùng cùng lệnh `conda activate apitesting`, `cd tool/backend` và `python -m pip install -r requirements-dev.lock`. Nếu chưa có môi trường: `conda create -n apitesting python=3.12`, rồi activate. Cài runtime bằng `requirements.lock` nếu không cần pytest/ruff. Không cài riêng `requirements.txt` khi cần tái lập chính xác bản dependency.

`requirements.txt` là danh sách trực tiếp; `requirements.lock` khóa dependency runtime, `requirements-dev.lock` khóa bản phát triển. `requirements-llm.txt` là đầu vào cho tích hợp LLM ở T25, chưa cần cài cho M0. Khi cập nhật dependency, dùng `pip-compile` trong conda Python 3.12 và chạy lại test trước khi thay lockfile.

## Chạy API, UI và kiểm tra storage

Terminal backend, tại `tool/backend`:

```bash
conda activate apitesting
python -m uvicorn app.main:app --host 127.0.0.1 --port 8111
```

API health: `http://127.0.0.1:8111/health`; tài liệu: `http://127.0.0.1:8111/docs`.

Terminal frontend, tại `tool/frontend` (Node.js 22 và npm):

```bash
npm ci
npm run dev
```

Mở URL Vite in ra, thường là `http://127.0.0.1:5173`. Proxy `/api/health` kết nối API cổng 8111 trong development; build production cần reverse proxy tương tự. UI hiện hiển thị kết nối thật tới backend. Các màn hình nhập spec và chạy test thuộc các bước tiếp theo.

Cổng backend mặc định của tool là **8111**. UI development đã có proxy tới cổng này; khởi động lại Vite sau khi đổi cấu hình. Nếu trước đó đã đặt `APITEST_BACKEND_URL`, hãy cập nhật biến này thành `http://127.0.0.1:8111` hoặc bỏ biến để dùng mặc định. Cổng frontend có thể đổi bằng `npm run dev -- --port 15173`.

Terminal kiểm tra storage tại `tool/backend`:

```bash
conda activate apitesting
python -m app.worker --check
```

Lệnh tạo/kiểm `tool/data/tool.sqlite` và `checkpoints.sqlite`, rồi thoát. Đây là kiểm tra readiness, chưa phải vòng lặp lấy job. `APITEST_DATA_DIR` có thể đặt qua biến môi trường (đường dẫn tuyệt đối được khuyến nghị); `.env.example` chỉ là mẫu, ứng dụng chưa tự đọc `.env`. Data, artifact, secret và build output đã được gitignore.

Docker là tùy chọn: tại `tool`, chạy `docker compose up --build api`; `docker compose --profile storage-check run --rm worker-check` kiểm storage. Compose này chỉ chứa tool; chưa cung cấp reset/seed QAirline (T09).

## Kiểm tra spec và môi trường QAirline

Tại `tool/backend` sau khi activate conda:

```bash
python -m app.cli --help
python -m app.cli spec ../../QAirline/specs/qairline_openapi.json
python -m app.cli preflight ../examples/qairline/profile.json --spec ../../QAirline/specs/qairline_openapi.json
```

Parser trả 48 operation, không đọc benchmark. Phạm vi 34 operation core do cấu hình target/chọn tag, không ghi cứng tên nghiệp vụ QAirline trong parser. Parser giữ ref đệ quy còn lại cùng provenance; `x-contract-gaps` được đưa vào output khi spec có khai báo. Không tự suy ra nghiệp vụ đúng từ code/backend.

Preflight QAirline cần backend đã chạy ở cổng 5000 theo [hướng dẫn QAirline](../QAirline/README.md). Chỉ gửi GET tới `/api/airports`, không seed hoặc sửa DB. Profile local là cấu hình tin cậy của người vận hành: allowlist origin/IP, fixture được khai báo sẵn sàng, auth env và safe probe. Fixture readiness M0 dựa trên khai báo profile; kiểm trạng thái DB thật cần adapter T09/T12. Auth chưa có probe trả `unverified`; nếu `auth_required=true`, trạng thái này chặn readiness. API key chỉ đọc từ env được chỉ định. Probe kết nối IP đã kiểm tra, không resolve lần hai và không follow redirect.

## Contract và storage

`app/contracts/` định nghĩa boundary phiên bản `1`, từ Objective đến ExecutionPlan nhiều bước, request, trace, oracle, coverage và run. `ValidationResult` không cho `PASS/FAIL` khi thiếu expected hoặc oracle tin cậy. `case_verdict` ưu tiên `BLOCKED` khi setup chưa đạt.

Schema JSON dành cho nhóm UI/module khác nằm trong [`contracts.schema.json`](backend/examples/contracts.schema.json), ví dụ plan nhiều bước tại [`booking-plan.json`](backend/examples/booking-plan.json). Đây là ví dụ cấu trúc contract, chưa phải scenario đã có fixture/binding hoàn chỉnh để chạy. Sau khi thay model, tại `tool/backend` chạy `python -m scripts.export_contracts` để cập nhật schema.

SQLite dùng bảng `runs` và bảng append-only `records` có `kind` (`case/step/attempt/assertion/coverage/defect`), ID và khóa liên kết run. Mỗi record có artifact JSONL bất biến và SHA-256 để đối chiếu. Metadata được commit trước khi ghi artifact; `Store.reconcile(run_id)` báo artifact thiếu/hỏng sau crash, không tự tái gửi HTTP. SQLite checkpointer của LangGraph lưu riêng; checkpoint không bảo đảm HTTP chỉ chạy một lần.

M1 thêm loại record `report`, trạng thái run khi kết thúc và contract `RunReport`; validator sử dụng dialect OpenAPI 3.0/3.1 tương ứng, kể cả `nullable` của 3.0. Không tải `$ref` mạng khi kiểm schema. Trace gốc được dùng trong bộ nhớ để kiểm tra trước khi che secret; chỉ bản đã che được ghi vào SQLite/JSONL, checkpoint và báo cáo. `captured_body_sha256` là hash phần response đã nhận, không phải hash bản text đã che secret.

Redaction che các trường nhạy cảm phổ biến trong header/body/query URL; không phải bộ dò mọi dạng secret tự do. Cấu hình token tùy biến và body binary cần mở rộng redaction khi xây executor.

## Chạy M1 từ CLI

QAirline backend vẫn chạy ở **5000**; **8111 là cổng backend của tool**. CLI gọi trực tiếp QAirline, không cần khởi động UI hoặc FastAPI của tool. Tại `tool/backend`:

```bash
conda activate apitesting
python -m app.cli run --spec ../../QAirline/specs/qairline_openapi.json --profile ../examples/qairline/profile.json --operation listAirports --output ../data
```

Lệnh in báo cáo JSON có `run.run_id`, `verdict`, `assertions`, `traces` và `report_file`. Báo cáo được lưu tại `tool/data/artifacts/<run_id>/report.json`, kèm SQLite và các record JSONL để đối chiếu. Mở lại kết quả mà không gửi request:

```bash
python -m app.cli show <run_id> --output ../data
```

`show` từ chối báo cáo có artifact thiếu/hỏng hoặc file export không khớp dữ liệu bất biến. Mã thoát `run`: `0=PASS`, `2=FAIL`, `3=UNKNOWN`, `4=BLOCKED`, `5=ERROR`, `6=SKIPPED`; lỗi đọc tham số/file cấu hình là `1`. Một run `completed` vẫn có thể có verdict `FAIL` hoặc `UNKNOWN`; trạng thái run mô tả việc chạy đã kết thúc, không thay thế verdict.

M1 hỗ trợ **một GET không có body/path parameter/parameter bắt buộc** được chọn qua `--operation`; không chứa tên endpoint QAirline trong lõi. POST và các ca cần dữ liệu được báo `BLOCKED` từ CLI, dù HTTP Executor đã được test GET/POST độc lập. Các ca nhiều bước, valid/invalid/boundary đầy đủ và UI điều khiển run thuộc M2/M3. Không tự resume/retry HTTP; mỗi lần `run` tạo `run_id` mới. M1 chưa tính năm metric benchmark.

Preflight tiêu tốn một request GET, sau đó ca kiểm thử dùng một request; `request_budget=1` sẽ chỉ probe và ghi ca là `SKIPPED`. Ngân sách thời gian được kiểm giữa các pha, socket có timeout và giới hạn kích thước body. M1 kiểm JSON response; response nén chưa được giải mã sẽ cho `UNKNOWN` ở phần schema. Status chưa khai báo hoặc status lỗi có khai báo nhưng chưa rõ điều kiện mong đợi không tự động được kết luận lỗi nghiệp vụ.

Kiểm chứng end-to-end với **MongoDB tạm và backend QAirline riêng**, không thay đổi DB đang dùng (cần Docker, image `mongo:7` và dependency backend QAirline):

```bash
python -m scripts.smoke_qairline
```

Script tự tạo MongoDB rỗng, chạy backend trên cổng tạm, kiểm `listAirports`, mở lại report và dọn các tiến trình/container đã tạo. Fixture rỗng dùng để kiểm contract danh sách sân bay; reset/seed nghiệp vụ đầy đủ vẫn là T09.

## Kiểm tra

Tại `tool/backend`:

```bash
conda activate apitesting
python -m pytest -q
python -m ruff check app tests
python -m pip check
```

Tại `tool/frontend`: `npm run build`. Chạy các lệnh kiểm tra trên Linux và Windows khi xác minh cài mới. Hiện đã kiểm chứng Linux local; Windows vẫn chờ kiểm tra trực tiếp.

Tài liệu thư viện được đối chiếu: [FastAPI testing](https://fastapi.tiangolo.com/tutorial/testing/), [Pydantic models](https://docs.pydantic.dev/latest/concepts/models/), [LangGraph checkpoint](https://docs.langchain.com/oss/python/langgraph/checkpointers).

M1 đối chiếu thêm [Graph API của LangGraph](https://docs.langchain.com/oss/python/langgraph/graph-api), [OpenAPI Schema Validator](https://openapi-schema-validator.readthedocs.io/en/latest/validation.html) và [HTTP client của Python](https://docs.python.org/3.12/library/http.client.html). Executor dùng kết nối IP đã kiểm tra với hostname TLS đúng và không retry tự động.

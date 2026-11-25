# Kế hoạch triển khai chi tiết API Testing Tool

Trạng thái: **M0 có mã nguồn/kiểm chứng local Linux và cấu hình cổng 8111; M1 đã hoàn thành CLI từ spec tới báo cáo**. T01 còn xác minh cài mới trên Windows trực tiếp. Xem [bằng chứng M0](evidence/m0.md) và [M1](evidence/m1.md). Tài liệu này chia [thiết kế và phạm vi sản phẩm](../docs/research/04-api-testing-method-and-build-plan.md) thành các bước code có thể kiểm tra. Cập nhật tiến độ tại [todo.md](todo.md); chỉ đánh dấu xong khi đạt tiêu chí và lưu bằng chứng. Không sửa hoặc thay thế [`plan.md` nghiên cứu ở gốc repo](../plan.md).

## 1. Phạm vi và quyết định kỹ thuật

- Sản phẩm nằm trong `tool/`, độc lập với `QAirline/`: Python **3.12.x** cho backend/CLI/worker, dùng **conda activate apitesting**, FastAPI cho web API, một worker local, LangGraph cho điều phối, frontend riêng, SQLite cho metadata/checkpoint, JSONL cho trace. `requirements.txt` khai báo phụ thuộc trực tiếp; `requirements.lock` khóa bản cài; `requirements-dev.txt` và `requirements-llm.txt` tách môi trường phát triển và LLM; `requirements-dev.lock` khóa bản phát triển đã kiểm tra.
- Một engine phục vụ CLI và web UI. `schema-only` chạy không cần API key; `agent-assisted` thêm LLM đề xuất có kiểm soát. Runtime Coverage Tracker chỉ dùng spec/rule được phép; Benchmark Evaluator đọc ground truth **sau** khi run kết thúc.
- Một ca có `ExecutionPlan` nhiều bước: setup, action, observation/assertion, cleanup. Request sinh ngay trước từng bước. Verdict ca: `PASS`, `FAIL`, `UNKNOWN`, `BLOCKED`, `ERROR`, `SKIPPED`. Trạng thái delivery của attempt là trường khác.
- QAirline dùng MongoDB thử nghiệm cô lập, reset/seed trước run đo chính thức. `tool/compose.yaml` chỉ phục vụ công cụ; cấu hình QAirline nằm trong `tool/examples/qairline/`. UI của công cụ tách khỏi `QAirline/frontend/`.
- Sơ đồ phụ thuộc triển khai: **T01–T05 → T06–T08 → T09–T14 → T15–T21 → T22–T28**. Một số bước trong cùng nhóm có thể làm đồng thời sau khi contract T02 được chốt; phụ thuộc cụ thể ghi dưới từng bước.

## 2. Cách dùng checklist và định nghĩa xong

1. Gán **một người phụ trách** cho mỗi mã Txx trong [todo.md](todo.md). Có thể giao người khác review, nhất là oracle benchmark.
2. Làm bước theo phụ thuộc. Nếu cần đổi contract, cập nhật T02 và kiểm tra các bước liên quan trước khi code tiếp.
3. Với mỗi bước, lưu vào checklist: PR/commit hoặc đường dẫn file, lệnh kiểm tra và kết quả, ảnh/chứng cứ UI khi thích hợp. Không đánh dấu `[x]` chỉ vì code đã viết.
4. Một bước chỉ xong khi tiêu chí chức năng, phép kiểm tra tập trung và tài liệu cấu hình/giới hạn liên quan đều đạt. Không bỏ test thất bại, không đổi `FAIL` thành `UNKNOWN` để làm xanh kết quả.
5. Các checkpoint trong checklist chỉ xong khi chạy luồng **thật** qua QAirline hoặc API thứ hai được nêu; mock chỉ dùng cho kiểm tra module.

Lệnh bên dưới là **hợp đồng lệnh dự kiến**, được tạo và ổn định ở T01/T08: `python -m pytest`, `python -m app.cli`, `npm run build`, `node benchmark/qairline/catalog.test.js`. Nếu tên lệnh thay đổi khi triển khai, cập nhật tại đây và trong README của tool.

## 3. Các bước triển khai

### M0 — Khung sản phẩm và hợp đồng

#### T01. Tạo scaffold và môi trường cài đặt

**Phụ thuộc:** không. **Phạm vi file:** `tool/backend/.python-version`, `requirements*.txt`/lock, `tool/frontend/package.json`, `.gitignore`, `README.md`, cấu hình khởi động API/worker/UI. Tạo cấu trúc theo tài liệu thiết kế; chốt phiên bản dependency tương thích Python 3.12 trên Linux/Windows, không trộn dependency của QAirline vào tool.

**Hoàn thành khi:** cài từ môi trường sạch, API health và CLI `--help` chạy được, UI build được; secret/DB/artifact không bị commit. **Kiểm tra:** cài theo README trên Linux và Windows trực tiếp trên hai hệ; chạy `python --version`, API health, CLI help, `npm run build`; ghi phiên bản thực tế.

#### T02. Định nghĩa contract và verdict

**Phụ thuộc:** T01. **Phạm vi file:** `tool/backend/app/contracts/`, ví dụ JSON contract và test contract. Định nghĩa `EndpointSpec`, `TestObjective`, `AbstractTestCase`, `ExecutionPlan`, `PlanStep`, `ConcreteRequest`, `ExecutionTrace`, `ValidationResult`, `CoverageSnapshot`, `RunManifest`; tách verdict ca khỏi trạng thái gửi HTTP và nguồn oracle.

**Hoàn thành khi:** một scenario nhiều bước và một ca đơn lẻ serialize/deserialize được; setup lỗi ánh xạ `BLOCKED`, expected thiếu không thể tạo `PASS`. **Kiểm tra:** unit test contract hợp lệ/không hợp lệ và round-trip JSON; review giao diện dữ liệu với thành viên phụ trách UI/benchmark.

#### T03. Lưu run, attempt và artifact

**Phụ thuộc:** T02. **Phạm vi file:** `tool/backend/app/storage/`, migration/schema SQLite và test repository. Lưu run, case, step, attempt, assertion, coverage, defect theo `run_id`; ghi trace JSONL/artifact đã che secret, checkpoint LangGraph tách riêng; đối chiếu metadata/artifact sau crash.

**Hoàn thành khi:** restart vẫn đọc được run; attempt đầu bất biến; artifact thiếu/hỏng được báo rõ thay vì báo `PASS`; transaction ngắn với một worker. **Kiểm tra:** integration test ghi/đọc/restart, crash giữa metadata và artifact, lọc theo `run_id`.

#### T04. Profile môi trường và preflight an toàn

**Phụ thuộc:** T01, T02. **Phạm vi file:** `tool/backend/app/config.py`, `engine/preflight/` và test. Profile lưu host/port đích được phép, timeout, auth reference, ngân sách, fixture/reset capability; preflight kiểm spec, đích, kết nối và readiness, dùng probe đọc an toàn nếu có. Tắt redirect HTTP mặc định, chặn external `$ref` theo mặc định, kiểm đích sau phân giải DNS.

**Hoàn thành khi:** target QAirline được phép chạy; URL/redirect/external ref ngoài allowlist bị từ chối; không dùng POST để dò auth; fixture thiếu được báo trước. **Kiểm tra:** test preflight với server local hợp lệ, host bị cấm, redirect, DNS đổi đích, spec có external ref.

#### T05. Phân tích và chuẩn hóa OpenAPI

**Phụ thuộc:** T02, T04. **Phạm vi file:** `tool/backend/app/engine/spec/` và test. Đọc JSON/YAML, giải `$ref` nội bộ, chuẩn hóa operation ID, parameter, request/response schema, security, ví dụ và nguồn provenance; ghi `contract_gap` thay vì tự đoán.

**Hoàn thành khi:** đọc được 48 operation QAirline, trong đó 34 core; operation lỗi được chỉ rõ vị trí; không tải ref mạng ngoài profile. **Kiểm tra:** unit test `$ref`/schema lỗi và test parse `QAirline/specs/qairline_openapi.json`.

**Checkpoint M0:** T01–T05 xong; có contract ổn định, môi trường cài lại được và spec QAirline được phân tích thành 48 operation.

### M1 — Đường chạy CLI đầu tiên

#### T06. HTTP Executor và trace một request

**Phụ thuộc:** T02, T04. **Phạm vi file:** `tool/backend/app/engine/execution/http_executor.py`, trace/redaction và test. Gửi một request với path/query/header/body/auth, timeout, đo thời gian, lưu request/response và trạng thái delivery; không tự follow redirect hay retry request có side effect.

**Hoàn thành khi:** GET/POST tới server local có trace đủ để tái hiện; token bị che; timeout hoặc mất response được phân loại `ERROR`/`delivery_unknown` đúng ngữ cảnh. **Kiểm tra:** integration test server local cho 2xx, 4xx, timeout, redirect và mất acknowledgement.

#### T07. Validator contract và báo cáo JSON tối thiểu

**Phụ thuộc:** T02, T05, T06. **Phạm vi file:** `engine/validation/`, `engine/reporting/` và test. Kiểm status/content type/JSON Schema của response được đặc tả; gắn nguồn oracle vào từng assertion; xuất báo cáo JSON có verdict và trace ID.

**Hoàn thành khi:** response đúng/sai schema phân biệt rõ; status không mô tả không tự động thành `FAIL`; `contract_gap` không bị chấm schema như oracle chắc chắn. **Kiểm tra:** test trên response mẫu hợp lệ/sai kiểu/không có oracle, kiểm JSON report theo contract T02.

#### T08. LangGraph cơ bản và CLI end-to-end

**Phụ thuộc:** T03–T07. **Phạm vi file:** `app/orchestration/graph.py`, `app/cli.py`, runner/service và test. Nối preflight → spec → một ca `GET /api/airports` → HTTP → validator → report; CLI và service xuất chung `run_id` và contract.

**Hoàn thành khi:** một lệnh CLI chạy thật với QAirline local, xuất trace/report, chạy lại sau restart vẫn xem được run; `schema-only` không cần API key. **Kiểm tra:** smoke end-to-end trên backend QAirline cô lập và test CLI với server fixture local.

**Checkpoint M1:** Một run CLI thật từ spec đến report; request và verdict có thể truy theo `run_id`.

### M2 — Môi trường thử nghiệm, chuỗi API và UI đầu tiên

#### T09. Reset/seed QAirline cô lập

**Phụ thuộc:** T04, T08. **Phạm vi file:** `tool/examples/qairline/`, `tool/scripts/`, sửa seed QAirline chỉ khi cần. Tạo container/DB riêng cho thử nghiệm, reset rồi seed với thời gian/ngày bay kiểm soát; tắt hoặc kiểm soát scheduler khi đo. Không dùng importer hiện tại như lệnh reset vì nó chỉ thêm bản ghi thiếu.

**Hoàn thành khi:** hai lượt reset cho cùng seed tạo cùng ID/trạng thái; database QAirline thường ngày không bị tác động. **Kiểm tra:** so snapshot dữ liệu sau hai lần reset; thử chạy sau một ca ghi dữ liệu rồi reset; xác nhận URI chỉ trỏ DB thử nghiệm.

#### T10. Web API và run manager tối thiểu

**Phụ thuộc:** T03, T04, T08. **Phạm vi file:** `tool/backend/app/api/`, `app/runs/`, test API. API nhận spec/profile, khởi tạo run, đọc trạng thái/trace/report và yêu cầu hủy; worker riêng lấy một job từ SQLite, cập nhật trạng thái có thứ tự.

**Hoàn thành khi:** POST run trả `run_id`, GET run sau restart có kết quả, request web không giữ worker chạy đồng bộ; không thể khởi chạy URL ngoài profile. **Kiểm tra:** integration test vòng đời queued→running→completed/error/cancelled và restart API/worker.

#### T11. UI lát cắt đầu tiên

**Phụ thuộc:** T10. **Phạm vi file:** `tool/frontend/src/api/`, `pages/`, `components/` và test UI. Màn hình chọn spec/profile, khởi chạy và xem run/trace của ca đầu tiên; hiển thị lỗi preflight.

**Hoàn thành khi:** từ trình duyệt chạy được `GET /api/airports` qua tool, xem verdict và mở lại run sau reload. **Kiểm tra:** UI build; browser end-to-end trên Web API thật, kiểm loading/error và reload.

#### T12. Dependency graph và resource registry

**Phụ thuộc:** T05, T09. **Phạm vi file:** `engine/dependency/`, `engine/execution/resource_registry.py`, adapter QAirline và test. Nối producer/consumer ID từ spec/config/fixture; giữ nguồn và độ tin cậy của edge/guard; registry lưu ID theo run/sequence, không hard-code trong lõi.

**Hoàn thành khi:** ID Flight/User/Passenger từ fixture hoặc response bind đúng vào Booking; guard hỗ trợ ca valid mà không chặn ca negative cố ý. **Kiểm tra:** unit test edge/registry và integration test với fixture QAirline mới reset.

#### T13. Scenario Executor nhiều bước

**Phụ thuộc:** T06, T09, T12. **Phạm vi file:** `engine/execution/scenario_executor.py`, `generation/data_generator.py` cơ bản và test. Chạy setup → action → observation → cleanup; sinh request ngay trước từng bước; capture/bind response; giữ trace từng step.

**Hoàn thành khi:** chuỗi tạo/đọc/hủy Booking chạy được; setup lỗi làm ca mục tiêu `BLOCKED`; cleanup lỗi không ghi đè verdict action. **Kiểm tra:** integration test chuỗi Booking trên DB reset và test failure ở từng bước bằng server fixture.

#### T14. Khôi phục, hủy và side effect

**Phụ thuộc:** T03, T10, T13. **Phạm vi file:** `app/runs/`, checkpoint/routing và test crash. Lưu attempt ID trước HTTP, đánh dấu delivery; khi mất acknowledgement, đối chiếu tài nguyên nếu có read-back, nếu không dừng bước phụ thuộc. Hủy tại ranh giới bước và giữ trace gốc.

**Hoàn thành khi:** crash sau POST không tạo Booking thứ hai khi resume; attempt không rõ outcome giữ `delivery_unknown`; cancel không xóa bằng chứng đã có. **Kiểm tra:** fault injection tại trước gửi/sau server xử lý/trước lưu response, sau đó resume.

**Checkpoint M2:** CLI và UI cùng xem run; chuỗi Booking có binding/cleanup; crash hoặc hủy không âm thầm gửi lặp request ghi dữ liệu.

### M3 — Sinh ca thích nghi và oracle đáng tin

#### T15. Coverage Tracker runtime

**Phụ thuộc:** T05, T13. **Phạm vi file:** `engine/coverage/{targets,matcher,tracker}.py` và test. Tạo mục tiêu runtime từ spec/rule được phép; tính operation, parameter, boundary, intent, status, sequence ở ba mức đã sinh/đã chạy/đã xác minh; không import benchmark.

**Hoàn thành khi:** ca `BLOCKED` không được tính đã phủ hành vi; hai ca trùng một mục tiêu không làm tăng mẫu số; snapshot đủ cho planner/UI. **Kiểm tra:** test trên trace giả lập và một chuỗi Booking thật; kiểm dependency graph code không import dataset benchmark.

#### T16. Case/Data Generator và Intent Validator

**Phụ thuộc:** T05, T12, T15. **Phạm vi file:** `engine/generation/` và test. Sinh valid, missing field, invalid type/enum, boundary và stateful plan từ `TestObjective`; Data Generator gắn fixture/ID ngay trước bước; Intent Validator kiểm mục tiêu thật sự được thể hiện trong request và trạng thái nền.

**Hoàn thành khi:** một ca invalid thiếu đúng trường mục tiêu nhưng các precondition khác hợp lệ; ca vượt ghế cố tình vi phạm guard; ca valid không dùng ID giả. **Kiểm tra:** property/fixture test cho từng intent và integration test QAirline trên DB reset.

#### T17. Agent Planner xác định và điều kiện dừng

**Phụ thuộc:** T08, T15, T16. **Phạm vi file:** `orchestration/{planner,routing,state}.py` và test. Chọn mục tiêu theo coverage chưa đạt, dependency, readiness và ngân sách; quyết định `repair_data`, `repair_setup`, `new_case`, `stop`; lưu lý do chọn và random seed.

**Hoàn thành khi:** chọn boundary nếu valid/invalid đã phủ; không sửa ca invalid có chủ đích; dừng khi hết request/thời gian hoặc không còn mục tiêu khả dụng; `schema-only` hoàn toàn không gọi LLM. **Kiểm tra:** unit test priority/routing/budget và chạy lặp cùng seed để so quyết định.

#### T18. Oracle nghiệp vụ và nguồn chứng cứ

**Phụ thuộc:** T13, T16. **Phạm vi file:** `engine/validation/`, `app/adapters/qairline/` và test. Rule pack có ID, nguồn, trạng thái review; validator so response và state trước/sau theo rule approved; LLM suggestion/observed behavior chỉ là giả thuyết.

**Hoàn thành khi:** vi phạm rule approved cho `FAIL`, rule thiếu căn cứ cho `UNKNOWN`, lỗi hạ tầng cho `ERROR`; test riêng giá/ghế Booking và không lộ dữ liệu nhạy cảm. **Kiểm tra:** test ba lớp oracle với response/state đúng, sai và thiếu bằng chứng.

#### T19. Defect Analyzer và replay có kiểm soát

**Phụ thuộc:** T09, T14, T18. **Phạm vi file:** `engine/defects/` và test. Gom lỗi cùng chữ ký, lưu request/response, spec/code/seed version; replay trên DB reset và fixture tương đương khi được phép, phân biệt candidate/confirmed/unreproduced.

**Hoàn thành khi:** lỗi tái hiện có bước chạy và bằng chứng trước/sau; nơi không reset được giữ candidate, không tự chạy lại destructive request. **Kiểm tra:** test lỗi giả có thể tái hiện và lỗi biến mất sau reset; xác nhận không làm bẩn DB thường ngày.

#### T20. Báo cáo tổng hợp và metric vận hành

**Phụ thuộc:** T15, T18, T19. **Phạm vi file:** `engine/reporting/`, query storage và test. Báo cáo JSON/Markdown gồm run manifest, mục tiêu/ca/attempt, coverage runtime, sáu verdict, defect, chi phí/thời gian và mẫu số; không tự nhận là metric benchmark khi chưa có nhãn approved.

**Hoàn thành khi:** từ một trace có thể truy ngược testcase và oracle; số đã sinh/đã chạy/đã xác minh khớp DB; export tải được. **Kiểm tra:** snapshot/schema test report và đối chiếu tay một run Booking.

#### T21. UI hoàn chỉnh trên cùng engine

**Phụ thuộc:** T11, T17, T20. **Phạm vi file:** `tool/frontend/src/` và web API đọc kết quả. Hiển thị mục tiêu/ca phát sinh khi chạy, tiến độ, filter operation/verdict, từng attempt/trace, coverage, lỗi, bước tái hiện, export report và nút dừng.

**Hoàn thành khi:** UI không hứa hiển thị trước mọi ca thích nghi; reload không mất run; UI và CLI hiển thị cùng verdict/mẫu số; hiển thị `BLOCKED`/`UNKNOWN` có nguyên nhân. **Kiểm tra:** browser end-to-end trên API thật với ca pass/fail/blocked và thử hủy run.

**Checkpoint M3:** hệ thống có engine, CLI và UI để chạy/xem QAirline; oracle có provenance, coverage runtime có bằng chứng, lỗi có thể tái hiện khi fixture cho phép.

### M4 — Benchmark, AI Agent và đánh giá

#### T22. Duyệt ground truth QAirline và fixture

**Phụ thuộc:** T09, T18. **Phạm vi file:** `benchmark/qairline/`, fixture QAirline và bằng chứng review. Hiện có **34 file core với 76 nghĩa vụ đều `draft`**, cùng hai scenario `draft`; đối chiếu từng expected với spec, source, nghiệp vụ và backend trên DB reset. Duyệt chéo theo [quy trình benchmark](../benchmark/qairline/README.md); mục chưa đủ chứng cứ để `draft`/`needs_fixture` với lý do.

**Hoàn thành khi:** mọi nghĩa vụ core và hai scenario được phân loại approved hoặc bị loại khỏi mẫu số có lý do; item approved có người duyệt, thời gian và evidence. **Kiểm tra:** `node benchmark/qairline/catalog.test.js`, review chéo và chạy lại mẫu approved trên fixture mới.

#### T23. Tạo tập lỗi chuẩn để đo Defect Detection Rate

**Phụ thuộc:** T09, T18, T22. **Phạm vi file:** cấu hình phiên bản QAirline có lỗi đã xác nhận hoặc vài mutant cài thủ công, manifest và bằng chứng độc lập. Chọn tối thiểu ba lỗi nghiệp vụ/response khác nhau có thể bật/tắt, có oracle approved, cách reset và request tái hiện; giữ nhãn lỗi ẩn khỏi engine. Không cần xây hệ thống mutation testing tổng quát.

**Hoàn thành khi:** mỗi lỗi có mã, bản code/seed, điều kiện kích hoạt, expected/actual và phép kiểm tra lỗi thật sự hiện diện; bản không lỗi là đối chứng. **Kiểm tra:** chạy request tham chiếu trên bản có lỗi và bản đối chứng sau reset, lưu trace cùng nhãn chuyên gia.

#### T24. Benchmark Evaluator độc lập

**Phụ thuộc:** T20, T22, T23. **Phạm vi file:** `app/benchmark/`, CLI chấm và test. Sau run, matcher kiểm semantic `coverage_target` bằng request, precondition và bằng chứng; chỉ oracle approved đi vào ground truth. Tính năm metric: Endpoint Coverage, Test Case Validity, Response Validation Accuracy, Defect Detection Rate, Testing Time.

**Hoàn thành khi:** evaluator không được import vào engine sinh ca; nhiều ca trùng nghĩa vụ chỉ tính một; báo mẫu số approved/blocked/unknown và trace của phép chấm. **Kiểm tra:** fixture evaluator cho hit/miss/blocked/duplicate, test không rò benchmark vào graph runtime.

#### T25. Chế độ agent-assisted và feedback LLM

**Phụ thuộc:** T17, T18. **Phạm vi file:** `orchestration/`, adapter LLM và test. LLM chỉ đề xuất mục tiêu/edge/giá trị hoặc cách sửa setup/data; đầu ra có schema và provenance; áp ngân sách token/thời gian, tối đa hai sửa cho ca valid, giữ attempt gốc.

**Hoàn thành khi:** tắt LLM vẫn chạy `schema-only`; output sai schema bị bác; không biến LLM inference thành approved oracle; ca invalid không bị sửa. **Kiểm tra:** model stub cho output đúng/sai, timeout, budget và integration run hai chế độ cùng contract.

#### T26. Thử trên OpenAPI khác QAirline

**Phụ thuộc:** T20. **Phạm vi file:** fixture một REST API local khác QAirline, config và test. Chạy black-box spec → case → HTTP → validator → report mà không nạp adapter QAirline.

**Hoàn thành khi:** ít nhất một valid và một invalid được chạy, có trace/status/schema/report; các phần không đủ oracle được ghi `UNKNOWN`, không suy diễn nghiệp vụ. **Kiểm tra:** end-to-end trên API local thứ hai và kiểm import dependency không có tên endpoint QAirline trong lõi.

#### T27. Baseline, ablation và thực nghiệm

**Phụ thuộc:** T21, T24–T26. **Phạm vi file:** `tool/scripts/`, cấu hình thí nghiệm, báo cáo kết quả. Cùng spec, DB reset/seed, model/prompt version, seed và ngân sách cho `schema-only`, One-shot LLM, full Agent; thêm `Full - dependency graph` và `Full - feedback` nếu muốn quy công riêng. Chạy tối thiểu ba lần mỗi nhánh.

**Hoàn thành khi:** năm metric có mẫu số, dữ liệu gốc, trung vị/độ biến thiên; kết luận chỉ dựa trên nhãn approved; trường hợp không so được được nêu rõ. **Kiểm tra:** một lệnh sinh lại bảng số từ run artifact; đối chiếu thủ công một sample mỗi metric.

#### T28. Đóng gói và kiểm tra hệ thống hoàn chỉnh

**Phụ thuộc:** T21, T24–T27. **Phạm vi file:** `tool/README.md`, compose/tool config, test end-to-end, tài liệu giới hạn. Kiểm cài trên Linux/Windows, bảo vệ target/secret, lưu trữ/restart, hủy run và tái hiện lỗi; phát hành hướng dẫn chạy tool độc lập QAirline và hướng dẫn chạy với QAirline.

**Hoàn thành khi:** người khác làm theo README chạy được UI/CLI, workload QAirline và API thứ hai; không cần sửa source để cấu hình; toàn bộ checklist/checkpoint có evidence. **Kiểm tra:** fresh install từ clone trên hai hệ điều hành, full test suite và smoke UI/CLI/report.

**Checkpoint M4:** T01–T28 hoàn tất; công cụ dùng được từ UI và CLI, benchmark độc lập, có số liệu thực nghiệm và hướng dẫn cài đặt.

## 4. Rủi ro và quy tắc dừng

| Rủi ro | Quyết định khi gặp |
|---|---|
| Oracle QAirline chưa được duyệt | Tiếp tục phát triển tool với oracle contract; **không** công bố metric benchmark chính thức hoặc tự nâng `draft` thành `approved`. |
| POST đã tới server nhưng worker crash | Ghi `delivery_unknown`, đối chiếu trạng thái nếu có read-back; không tự gửi lại. |
| Không reset được môi trường đích | Không tự replay ca ghi dữ liệu; defect giữ candidate với trace gốc. |
| Coverage runtime và ground truth khác nhau | Giữ cả hai số, giải thích chênh lệch; không đưa benchmark vào planner. |
| UI hoặc LLM chậm tiến độ | Giữ vertical slice chạy được qua CLI/UI; không bỏ UI, benchmark hay kiểm chứng engine khỏi phạm vi bàn giao. |
| Yêu cầu làm việc trên nhiều hệ điều hành | Khóa dependency và kiểm tra fresh install; lỗi nền tảng được ghi thành task sửa trước khi đánh dấu T27. |

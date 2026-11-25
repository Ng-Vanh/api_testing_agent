# Checklist tiến độ API Testing Tool

Nguồn chi tiết và tiêu chí kiểm tra: [plan.md](plan.md). M0 đã có code và kiểm chứng Linux, cổng tool đã đổi sang 8111; T01 còn chờ xác nhận cài mới trên Windows trực tiếp. M1 đã chạy CLI từ spec tới báo cáo trên QAirline cô lập. Với mỗi Txx, điền `owner`, liên kết PR/commit hoặc file, lệnh kiểm tra và kết quả vào ô **evidence** trước khi đánh dấu `[x]`. Một checkpoint chỉ được đánh dấu khi các bước phụ thuộc và luồng thật tương ứng đã đạt.

| Trường theo dõi | Giá trị |
|---|---|
| Ngày bắt đầu | 2026-11-25 |
| Phiên bản Python | conda apitesting — Python 3.12.16 |
| Tổng bước | 28 |
| Đã hoàn thành | 7/28; T01 đã code/test Linux, chờ kiểm tra Windows |
| Người điều phối | Chưa gán |

## M0 — Khung sản phẩm và hợp đồng

- [ ] **T01** Scaffold và dependency — owner: Codex; [evidence](evidence/m0.md); Linux/build/lock đã đạt, còn chờ cài mới trên Windows.
- [x] **T02** Contract, plan, verdict — owner: Codex; [evidence](evidence/m0.md); contract/schema và unit test đã đạt local trên scaffold T01.
- [x] **T03** SQLite, checkpoint, trace artifact — owner: Codex; [evidence](evidence/m0.md); reopen, bất biến, redaction, crash reconciliation đã đạt.
- [x] **T04** Profile và preflight an toàn — owner: Codex; [evidence](evidence/m0.md); host/IP/redirect/auth/fixture và HTTP probe local đã đạt.
- [x] **T05** OpenAPI parser/normalizer — owner: Codex; [evidence](evidence/m0.md); JSON/YAML/ref, override parameter, spec lỗi và 48 operation đã đạt.
- [ ] **Checkpoint M0:** contract/parser/storage/preflight đạt local; còn chờ T01 kiểm tra Windows. [Evidence](evidence/m0.md).

## M1 — CLI từ spec đến báo cáo

- [x] **T06** HTTP Executor, redacted trace — phụ thuộc: T02, T04; owner: Codex; [evidence](evidence/m1.md); GET/POST, 4xx, timeout/mất acknowledgement, redirect và giới hạn body đã kiểm tra.
- [x] **T07** Contract validator, JSON report — phụ thuộc: T02, T05, T06; owner: Codex; [evidence](evidence/m1.md); status/content type/schema, nullable, unknown/gap và report corruption đã kiểm tra.
- [x] **T08** LangGraph + CLI vertical slice — phụ thuộc: T03–T07; owner: Codex; [evidence](evidence/m1.md); `run`/`show` dùng chung service, checkpoint và report; QAirline thật/cô lập đạt PASS.
- [x] **Checkpoint M1:** `GET /api/airports` đạt PASS trên backend QAirline + MongoDB tạm riêng, mở lại report không gửi request. [Evidence](evidence/m1.md).

## M2 — Kịch bản nhiều request và UI đầu tiên

- [ ] **T09** Reset/seed MongoDB QAirline cô lập — phụ thuộc: T04, T08; owner: ___; evidence: ___
- [ ] **T10** Web API, run manager, worker — phụ thuộc: T03, T04, T08; owner: ___; evidence: ___
- [ ] **T11** UI chọn spec, chạy và xem trace — phụ thuộc: T10; owner: ___; evidence: ___
- [ ] **T12** Dependency graph, resource registry — phụ thuộc: T05, T09; owner: ___; evidence: ___
- [ ] **T13** Scenario Executor Booking — phụ thuộc: T06, T09, T12; owner: ___; evidence: ___
- [ ] **T14** Resume/cancel không lặp side effect — phụ thuộc: T03, T10, T13; owner: ___; evidence: ___
- [ ] **Checkpoint M2:** UI/CLI chung run; Booking nhiều bước chạy và khôi phục an toàn; evidence: ___

## M3 — Sinh ca, oracle, coverage và UI hoàn chỉnh

- [ ] **T15** Runtime Coverage Tracker — phụ thuộc: T05, T13; owner: ___; evidence: ___
- [ ] **T16** Case/Data Generator, Intent Validator — phụ thuộc: T05, T12, T15; owner: ___; evidence: ___
- [ ] **T17** Agent Planner xác định, budget/stop — phụ thuộc: T08, T15, T16; owner: ___; evidence: ___
- [ ] **T18** Oracle nghiệp vụ, provenance — phụ thuộc: T13, T16; owner: ___; evidence: ___
- [ ] **T19** Defect Analyzer, replay có reset — phụ thuộc: T09, T14, T18; owner: ___; evidence: ___
- [ ] **T20** Báo cáo/metric vận hành — phụ thuộc: T15, T18, T19; owner: ___; evidence: ___
- [ ] **T21** UI ca động, coverage, defect, export — phụ thuộc: T11, T17, T20; owner: ___; evidence: ___
- [ ] **Checkpoint M3:** engine + CLI + UI chạy QAirline; oracle/coverage/lỗi có bằng chứng; evidence: ___

## M4 — Ground truth, AI Agent và đánh giá

- [ ] **T22** Duyệt 76 nghĩa vụ core + 2 scenario, bổ sung fixture — phụ thuộc: T09, T18; owner: ___; reviewer: ___; evidence: ___
- [ ] **T23** Tập lỗi chuẩn ít nhất 3 lỗi để đo detection — phụ thuộc: T09, T18, T22; owner: ___; reviewer: ___; evidence: ___
- [ ] **T24** Benchmark Evaluator độc lập, 5 metric — phụ thuộc: T20, T22, T23; owner: ___; evidence: ___
- [ ] **T25** Agent-assisted, LLM feedback có giới hạn — phụ thuộc: T17, T18; owner: ___; evidence: ___
- [ ] **T26** OpenAPI local thứ hai, không adapter QAirline — phụ thuộc: T20; owner: ___; evidence: ___
- [ ] **T27** Baseline/ablation, tối thiểu 3 lần lặp — phụ thuộc: T21, T24–T26; owner: ___; evidence: ___
- [ ] **T28** Fresh install Linux/Windows, đóng gói và hướng dẫn — phụ thuộc: T21, T24–T27; owner: ___; evidence: ___
- [ ] **Checkpoint M4:** hệ thống hoàn chỉnh, benchmark độc lập, kết quả và tài liệu có thể tái lập; evidence: ___

## Nhật ký kiểm tra

| Ngày | Bước | Người kiểm tra | Lệnh/đường dẫn bằng chứng | Kết quả hoặc việc còn lại |
|---|---|---|---|---|
| 2026-11-25 | T01–T05 | Codex | [Bằng chứng M0](evidence/m0.md) | 17 test đạt; UI build và HTTP smoke đạt; Windows chưa được kiểm tra. |
| 2026-11-25 | T06–T08, cổng 8111 | Codex | [Bằng chứng M1](evidence/m1.md) | CLI end-to-end và QAirline cô lập đạt PASS; API 8111/proxy 5173 đạt; T01 Windows vẫn mở. |

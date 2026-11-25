# QAirline API benchmark dataset (bản nháp 0.2)

Thư mục `datasets/` chứa **một file JSON cho mỗi cặp HTTP method + path** trong OpenAPI của QAirline. Hiện có 48 file: 34 operation JSON nghiệp vụ thuộc phạm vi V1 (`scope: core`) và 14 operation mở rộng (`scope: extension`). Tổng cộng có 91 nghĩa vụ kiểm thử. Đây là **đáp án đánh giá**, không phải input cho Agent sinh test; Agent chỉ nhận OpenAPI và cấu hình môi trường.

## Cấu trúc một file

Ví dụ đầy đủ: [`datasets/bookings/createBooking.json`](datasets/bookings/createBooking.json).

| Trường | Ý nghĩa |
|---|---|
| `version`, `benchmark` | Phiên bản định dạng dataset và tên hệ thống. |
| `operation` | `operationId`, HTTP `method`, `path`, `scope`. Một URL có GET/POST sẽ có hai file. |
| `sources` | JSON Pointer tới operation trong OpenAPI cùng route/controller đã đối chiếu. |
| `contract_gap` | Có khi OpenAPI hiện tại chưa mô tả đúng response thực tế; schema oracle được tạm ngưng cho operation đó. |
| `obligations[]` | Danh sách hành vi cần kiểm thử độc lập với số test case mà Agent sinh. |
| `obligations[].id`, `operation_id` | ID nghĩa vụ và ID operation. `operation_id` lặp lại giá trị ở `operation.operationId` để mỗi nghĩa vụ vẫn tự định danh khi được xuất riêng; kiểm tra catalog buộc hai giá trị bằng nhau. |
| `category`, `subcategory`, `intent` | Loại ca tổng quát, loại chi tiết (`missing_required`, `invalid_enum`, `boundary_value`, `atomicity`...) và mục đích bằng lời. |
| `coverage_target` | Điều kiện để tính một test do Agent sinh là đã phủ nghĩa vụ: fixture cần có, predicate semantic của request và bằng chứng quan sát cần lưu. |
| `input` | Tên fixture và mẫu request: `path`, `query`, `body` hoặc `multipart`. Method/path lấy từ `operation`. |
| `expected` | Status mong đợi và các assertion có cấu trúc. Không lấy status thực tế của backend làm đáp án. |
| `oracle` | Cơ sở (`contract`, `business_rule`, `security_rule`, `robustness_rule`), nguồn chứng cứ và trạng thái review. |
| `readiness` | `ready`, `needs_fixture` hoặc `needs_rule_review`. Trường này nói về khả năng chuẩn bị/chấm ca, không có nghĩa oracle đã được duyệt. |

Ví dụ rút gọn từ `createBooking.mismatched_passenger_count`:

```json
{
  "id": "createBooking.mismatched_passenger_count",
  "operation_id": "createBooking",
  "category": "invalid",
  "subcategory": "cross_field_mismatch",
  "intent": "passengerCount khác độ dài passengerIDs",
  "coverage_target": {
    "match": "semantic",
    "preconditions": [{ "kind": "fixture_state", "name": "seeded" }],
    "request_predicates": [
      { "kind": "length_mismatch", "count_field": "body.passengerCount", "list_field": "body.passengerIDs" },
      { "kind": "otherwise_valid" }
    ],
    "evidence_required": ["request", "response", "state_before", "state_after", "oracle_result"]
  },
  "input": {
    "fixture": "seeded",
    "request": {
      "body": {
        "userID": "${fixture:users:qa_seed_user_01:_id}",
        "flightID": "${fixture:flights:QA201-2:_id}",
        "flightClass": "economy",
        "passengerCount": 2,
        "passengerIDs": ["${fixture:passengers:qa-passenger-01@example.test:_id}"]
      }
    }
  },
  "expected": {
    "status": [400],
    "assertions": [
      { "kind": "response_matches_openapi", "ref": ".../responses/400" },
      { "kind": "state_unchanged", "resources": ["bookings", "flight.seatsAvailable"] }
    ]
  },
  "oracle": {
    "basis": "contract",
    "evidence": ["QAirline/specs/qairline_openapi.json", "QAirline/backend/controllers/BookingController.js"],
    "review": "draft"
  },
  "readiness": "ready"
}
```

`input` dùng các tham chiếu có kiểu để tránh ghi cứng ID của MongoDB:

- `${fixture:<collection>:<natural-key>:<field>}` lấy giá trị từ [seed](../../QAirline/seed/data.json) sau khi build/import. Ví dụ `fixture:flights:QA201-2:_id`. Natural key của booking là `username|flightCode|class`.
- `${secret:<name>}` lấy mật khẩu khi chạy; `seed_password` phải bằng mật khẩu đã dùng khi import seed. Không lưu mật khẩu trong dataset.
- `${clock:<name>}` sinh thời điểm tương lai sau khi reset DB; hai token `future_day_10T01_00Z` và `future_day_10T03_00Z` phải cùng ngày UTC.

`input.fixture: seeded` dùng dữ liệu seed hiện có. Các fixture `unlinked_user`, `unlinked_airport`, `unlinked_aircraft`, `one_seat_flight`, `full_destination_flight`, `benchmark_content` và `benchmark_image` cần được dựng riêng trước khi chạy những ca đánh dấu `needs_fixture`. Mỗi ca ghi dữ liệu phải bắt đầu từ DB đã reset và seed lại; chạy nhiều ca ghi liên tiếp trên cùng DB sẽ làm sai kết quả. Script import hiện tại **không phải** reset: nó không xóa dữ liệu cũ và không làm mới ngày bay.

## Kịch bản liên API

Các nghĩa vụ trong `datasets/` đánh giá từng operation. Thư mục [`scenarios/`](scenarios/) đánh giá **chuỗi phụ thuộc và biến động trạng thái**; nó không làm thay đổi tổng 48 dataset/91 nghĩa vụ ở trên:

| Scenario | Chuỗi và oracle | Trạng thái |
|---|---|---|
| [`booking-create-cancel.json`](scenarios/booking-create-cancel.json) | Đọc Flight → tạo Passenger → tạo/đọc/hủy Booking → kiểm giá, ghế giảm rồi hoàn, Booking không còn | `ready`, oracle `draft` |
| [`booking-failed-transfer-atomicity.json`](scenarios/booking-failed-transfer-atomicity.json) | Chuyển Booking sang Flight hết ghế → kiểm Booking và số ghế hai chuyến không đổi | `needs_fixture`, oracle `draft` |

Mỗi scenario có `scenario_id`, `fixture`, `steps[]` (operation ID, request, status, trường cần capture), `assertions[]`, `oracle` và `readiness`. `${memory:<name>}` lấy giá trị đã capture ở bước trước. Bộ chấm cần tính **sequence coverage** và tỷ lệ chuỗi chạy tới bước cuối riêng với operation coverage. Các expected/state assertion vẫn phải được duyệt theo quy trình bên dưới trước khi tính vào ground truth.

## Quy tắc chấm

1. Chỉ chấm **độ phủ hành vi** khi test do Agent sinh thỏa `coverage_target.preconditions` và `request_predicates`, đồng thời có đủ `evidence_required`. So khớp theo ý nghĩa, không đòi request trùng ID/giá trị của `input.request` mẫu. Nhiều test trùng một nghĩa vụ chỉ tính một lần. HTTP 4xx của ca invalid có chủ đích vẫn có thể là kết quả đúng.
2. Chỉ dùng oracle `approved` làm **ground truth chính thức**. Tất cả oracle hiện là `draft`; `ready` chỉ nói fixture/request có thể chuẩn bị, không tự động phê duyệt expected. `approved` bắt buộc có `approved_by`, `approved_at` và `verification_evidence` trong file.
3. Các ca `needs_fixture` hoặc `needs_rule_review` không đưa vào mẫu số của phép đo chính cho đến khi hoàn tất điều kiện tương ứng. Vẫn báo riêng số ca đang bị chặn để tránh làm đẹp độ phủ.
4. `response_matches_openapi` so theo đúng status và content type. Các operation có `contract_gap` chỉ giữ kiểm tra status cho đến khi sửa/duyệt lại spec. Ví dụ response Flight/Booking được `populate` thành object trong controller nhưng OpenAPI hiện mô tả một số trường đó là ObjectId.
5. Nhãn lỗi `confirmed` cần tái hiện trên DB mới, so expected/actual và ghi phiên bản spec, code, seed. Một lỗi HTTP 500 đơn lẻ chỉ là ứng viên.

Để kiểm tra catalog không thiếu/trùng operation, chạy từ gốc repo:

```bash
node benchmark/qairline/catalog.test.js
```

Kiểm tra trên đối chiếu 48 operation trong OpenAPI, 34 operation `core`, JSON Pointer, status có trong spec, cú pháp placeholder, các khóa fixture seed dùng bởi ca `ready`, cùng operation/status và thứ tự capture trong scenario. Bộ dataset này chưa có runner chấm test do Agent sinh; runner cần dùng hợp đồng output của Agent sau khi module sinh test được chốt.

### Cách duyệt oracle

Với từng nghĩa vụ: (1) đối chiếu expected với OpenAPI và yêu cầu nghiệp vụ độc lập; (2) chạy ca trên DB thử nghiệm đã reset, lưu request/response và snapshot DB nếu có state assertion; (3) phân loại rõ sai khác là lỗi spec, lỗi backend hay quy tắc chưa được chốt; (4) người phụ trách ghi `approved_by`, `approved_at`, `verification_evidence` rồi mới đổi `review` thành `approved`. Chỉ chạy lại backend hiện tại **không đủ** để xác nhận một quy tắc nghiệp vụ mong muốn, vì backend có thể đang chứa lỗi mà benchmark cần phát hiện.

`coverage_target` hiện là **hợp đồng cho bộ chấm sau này**. `request_predicates` dùng một tập từ vựng hữu hạn, ví dụ `field_absent`, `length_mismatch`, `resource_absent`, `capacity_exceeded`, `field_relation`, `valid_request`. Bộ chấm phải kiểm tra các predicate trên request và trạng thái fixture thực tế; không được gán coverage chỉ vì Agent tự khai báo `obligation.id`. Các predicate chưa có evaluator thực thi, nên việc chấm tự động vẫn là công việc tiếp theo.

## Hướng dẫn đánh giá và phê duyệt từng nghĩa vụ

### 1. Chuẩn bị một lượt review có thể tái hiện

Làm việc trên backend và MongoDB **local dành riêng cho kiểm thử**, không dùng DB mà người khác đang thao tác. Ghi lại commit backend, phiên bản OpenAPI, thời điểm, cấu hình scheduler và seed. Chạy [script import seed](../../QAirline/README.md#5-lần-đầu-chạy-có-tự-seed-database-không) vào DB sạch. Script import chỉ thêm dữ liệu thiếu; nó **không reset** dữ liệu hoặc làm mới ngày bay. Vì vậy, với ca ghi/sửa/xóa hoặc ca phụ thuộc ngày bay, cần một DB thử nghiệm sạch cho mỗi lần chạy và import seed lại. Khi chưa có lệnh reset riêng, không dùng việc chạy lại import script làm bằng chứng rằng trạng thái ban đầu giống nhau.

Chọn một file trong `datasets/` và **một** `obligation.id` tại mỗi lượt review. Ưu tiên `scope: core` và `readiness: ready`. Với `needs_fixture`, tạo và ghi lại fixture bổ sung trước khi chạy; với `needs_rule_review`, chốt quy tắc mong muốn với nhóm trước khi phê duyệt. Không đổi `readiness` chỉ vì backend trả về một status nào đó.

### 2. Đánh giá nội dung trước khi gửi request

| Câu hỏi | Tiêu chí đạt |
|---|---|
| API có đúng không? | `operation_id` khớp `operation.operationId`, method/path trong file khớp OpenAPI và route. |
| Ca kiểm tra đúng hành vi không? | `category`, `subcategory`, `intent` và `coverage_target` cùng mô tả một điều kiện. Ví dụ `length_mismatch` phải so `passengerCount` với **độ dài** `passengerIDs`. |
| Request mẫu có cô lập biến đang thử không? | Placeholder giải được từ fixture; các trường khác hợp lệ. `otherwise_valid` nghĩa là mọi điều kiện ngoài biến cố ý làm sai đều đáp ứng schema, tham chiếu tài nguyên và precondition. |
| Expected có nguồn đáng tin không? | Status, schema và quy tắc nghiệp vụ có căn cứ từ OpenAPI đã đối chiếu hoặc yêu cầu được nhóm thống nhất. Controller cho biết hành vi **hiện tại**; nó không tự chứng minh hành vi **đúng**. |
| Assertion có đủ sức kết luận không? | Có thể đo từng assertion bằng response hoặc snapshot trước–sau. Ví dụ ca bị từ chối phải kiểm tra DB không bị ghi dở, nếu đó là mục tiêu của ca. |

Nếu OpenAPI và controller mâu thuẫn, hoặc yêu cầu nghiệp vụ chưa được quyết định, ghi kết luận `needs_rule_review`/`contract_gap` và giữ oracle ở `draft`. Chỉ sửa expected sau khi xác định **nguồn nào sai**; không tự đổi expected để khớp response vừa thấy.

### 3. Chạy thử và lưu bằng chứng: ví dụ Booking

Với `createBooking.mismatched_passenger_count` trong [`createBooking.json`](datasets/bookings/createBooking.json), có thể dùng nút **Try it out** ở `http://localhost:5000/api-docs/`:

1. Gọi `GET /api/users`, `GET /api/flights/code/QA201-2`, `GET /api/passengers`; lấy `_id` của `qa_seed_user_01`, chuyến `QA201-2` và một hành khách seed. Các ID này phải có thật; chỉ điều kiện **số lượng không khớp** được cố ý làm sai.
2. Gọi `GET /api/bookings` và `GET /api/flights/{id}`; lưu danh sách booking và `flightClass.economy.seatsAvailable` làm trạng thái **trước**.
3. Gửi `POST /api/bookings` với `userID`, `flightID`, `passengerIDs: [<ID hành khách>]`, `flightClass: "economy"`, nhưng `passengerCount: 2`.
4. Lưu đầy đủ request, HTTP status và JSON response. Sau đó gọi lại hai GET ở bước 2, lưu trạng thái **sau**. Đối chiếu expected: HTTP `400`, response theo schema của status này, không có booking mới và số ghế không đổi.
5. Lặp lại trên DB thử nghiệm sạch. Nếu backend trả kết quả khác, ghi sai khác làm **ứng viên lỗi**; không tự sửa oracle theo kết quả thực tế.

Đối với ca hợp lệ tạo tài nguyên, lưu thêm ID tài nguyên mới, liên kết tới User/Flight/Passenger và các thay đổi giá/ghế. Với ca `stateful`, `security` hoặc `robustness`, cần kiểm tra đủ assertion tương ứng; chỉ nhìn status code là chưa đủ.

### 4. Lưu hồ sơ review và quyết định

Lưu một hồ sơ bằng chứng theo `obligation.id` (ví dụ `benchmark/qairline/evidence/createBooking.mismatched_passenger_count.json`). Hồ sơ nên có: `obligation_id`, commit backend, phiên bản spec/seed, thời điểm chạy, mô tả DB ban đầu, request đã che mật khẩu, response, snapshot trước–sau, nguồn quy tắc mong muốn, kết quả từng assertion và kết luận. Không đưa mật khẩu hoặc dữ liệu nhạy cảm vào repo.

Chỉ đổi `oracle.review` thành `approved` khi **tất cả** điều kiện sau đạt:

- `coverage_target` nhận diện đúng hành vi và không phụ thuộc ID mẫu cụ thể.
- Fixture/precondition tạo được và ca có thể tái hiện trên DB sạch.
- Expected có nguồn được nhóm chấp nhận **độc lập với việc backend hiện tại pass hay fail**.
- Mỗi assertion có bằng chứng kiểm tra; không còn `contract_gap` ảnh hưởng tới assertion đang dùng.
- Có người chịu trách nhiệm duyệt, ngày duyệt và đường dẫn hồ sơ bằng chứng.

Khi đó cập nhật riêng oracle của obligation đã duyệt, chẳng hạn:

```json
{
  "review": "approved",
  "approved_by": "Tên thành viên phụ trách",
  "approved_at": "<ngày-duyệt-YYYY-MM-DD>",
  "verification_evidence": [
    "benchmark/qairline/evidence/createBooking.mismatched_passenger_count.json"
  ]
}
```

Nếu backend **fail** một oracle đã được xác nhận là đúng, vẫn có thể phê duyệt oracle và ghi nhận ứng viên lỗi. Nếu chính quy tắc mong đợi còn tranh cãi, giữ `draft`. Sau mỗi lần sửa dataset, chạy `node benchmark/qairline/catalog.test.js`; kiểm tra này xác nhận cấu trúc và tham chiếu, **không thay thế** việc duyệt nghiệp vụ hoặc chạy thử.

# KẾ HOẠCH NGHIÊN CỨU KHOA HỌC & TRIỂN KHAI: AI AGENT TỰ ĐỘNG KIỂM THỬ API TRÊN HỆ THỐNG QAIRLINE

> [!NOTE]
> Tài liệu này được xây dựng dựa trên khảo sát trực tiếp mã nguồn hệ thống thực nghiệm [QAirline](file:///home/vietanh/Workspaces/self/ApiTesting/QAirline) và tổng hợp 5 công trình nghiên cứu khoa học thực tế (2023–2025) tại các hội nghị hàng đầu về Công nghệ Phần mềm (ICSE, FSE, ASE, ICST).

---

## Phần 1. Problem Analysis (Phân tích bài toán & Khảo sát QAirline)

### 1.1. Phân tích bài toán tổng quát
Bài toán yêu cầu xây dựng một **AI Agent tự động kiểm thử RESTful API** với khả năng:
1. **API Specification Analysis**: Đọc và trích xuất cấu trúc endpoint, method, tham số, schema, ràng buộc và mô tả ngữ nghĩa từ tài liệu OpenAPI/Swagger.
2. **Intelligent Test Case Generation**: Sinh test case đa dạng (Valid, Invalid, Boundary, Edge Case, Stateful Sequence) thay vì dữ liệu ngẫu nhiên.
3. **Automated Test Execution**: Tự động gửi HTTP request (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`), quản lý headers, auth, query/path params, body và lưu vết thực thi.
4. **Response Validation**: Kiểm tra không chỉ HTTP status code mà cả cấu trúc JSON, kiểu dữ liệu, ràng buộc nghiệp vụ (response oracle) và phát hiện sai lệch bất thường.
5. **Defect Detection & Reporting**: Phân loại lỗi, lưu request/response tái hiện và xuất báo cáo tổng hợp.

**Phân biệt 3 lớp kiểm thử trong bài toán:**
- **Kiểm thử tuân thủ đặc tả (Specification Conformance Testing):** Đúng HTTP status code, đúng JSON schema, đúng kiểu dữ liệu/enum/required fields theo OpenAPI.
- **Kiểm thử nghiệp vụ & có trạng thái (Business Logic & Stateful Testing):** Các ràng buộc liên quan đến trạng thái hệ thống (ví dụ: đặt vé vượt quá `seatsAvailable`, `passengerIDs.length != passengerCount`, chuỗi `Tạo Airport/Aircraft -> Tạo Flight -> Tạo Passenger -> Tạo Booking`).
- **Kiểm thử bảo mật & độ bền (Security & Robustness Testing):** Xử lý đầu vào độc hại/biên (NoSQL/SQL injection, chuỗi quá dài, ObjectId sai định dạng gây crash 500, truy cập trái phép không có token).

---

### 1.2. Kết quả khảo sát thực tế repository QAirline

Qua kiểm tra trực tiếp mã nguồn tại [QAirline/backend](file:///home/vietanh/Workspaces/self/ApiTesting/QAirline/backend):

#### A. Kiến trúc & Công nghệ
- **Backend:** Node.js + Express (`^4.21.1`), Mongoose (`^7.8.3`) kết nối MongoDB, `bcrypt` (`^5.1.1`) để hash mật khẩu, `multer` + `gridfs-stream` cho upload file, `node-cron` cho tác vụ nền, `swagger-jsdoc` (`^6.2.8`) và `swagger-ui-express` (`^5.0.1`).
- **Frontend:** React (`QAirline/frontend/`).
- **Database:** MongoDB. Trong [db.js](file:///home/vietanh/Workspaces/self/ApiTesting/QAirline/backend/config/db.js#L4), chuỗi kết nối MongoDB Atlas đang được **hardcode trực tiếp** (`mongodb+srv://admin:admin@...`).

#### B. Tình trạng Swagger / OpenAPI Specification
- Trong [server.js](file:///home/vietanh/Workspaces/self/ApiTesting/QAirline/backend/server.js#L13-L26), hệ thống có cấu hình `swagger-jsdoc` mount tại `/api-docs` và quét `./routes/**/*.js`.
- **Phát hiện quan trọng:** Kiểm tra toàn bộ 10 file trong `backend/routes/` cho thấy **chưa có bất kỳ chú thích `@swagger` JSDoc nào**. Do đó, `/api-docs` hiện tại chỉ sinh ra đặc tả rỗng (`paths: {}`).

#### C. Danh sách các nhóm Endpoint hiện có (48 endpoints trên 10 route files)
| Nhóm Route | Prefix | Số endpoint | Các endpoint chính |
|---|---|---|---|
| `UserRoute.js` | `/api/users` | 6 | `POST /login`, `POST /`, `GET /:id`, `GET /`, `PUT /:id`, `DELETE /:id` |
| `AirportRoute.js` | `/api/airports` | 5 | `POST /`, `GET /:id`, `GET /`, `PUT /:id`, `DELETE /:id` |
| `AircraftRoute.js` | `/api/aircrafts` | 6 | `POST /`, `GET /`, `GET /:id`, `PUT /:id`, `DELETE /:id`, `GET /type/:type` |
| `FlightRoute.js` | `/api/flights` | 7 | `POST /search`, `POST /`, `PUT /:id`, `GET /:id`, `GET /`, `DELETE /:id`, `GET /code/:code` |
| `PassengerRoute.js` | `/api/passengers` | 3 | `POST /`, `GET /:id`, `GET /` |
| `BookingRoute.js` | `/api/bookings` | 7 | `POST /`, `GET /user/:userID`, `GET /:id`, `PUT /:id`, `DELETE /:id`, `GET /`, `GET /rank/popular-flights` |
| `ContentRoute.js` | `/api/content` | 5 | `GET /`, `POST /`, `PUT /:id`, `GET /:id`, `DELETE /:id` |
| `FileRoute.js` | `/api/files` | 5 | `POST /upload`, `GET /`, `GET /:filename`, `DELETE /:id`, `GET /image/:filename` |
| `StatisticsRoute.js` | `/api/statistics` | 1 | `GET /` |
| `SchedulerRoute.js` | `/scheduler` | 3 | `POST /start`, `POST /stop`, `GET /status` |

#### D. Các Mongoose Models & Phụ thuộc dữ liệu (8 models)
- `UserModel`: `name`, `username`, `password` (bcrypt), `role` (`['user', 'admin']`), `bookings[]` (ref `Booking`).
- `AirportModel`: `code` (unique), `name`, `city`.
- `AircraftModel`: `code`, `manufacturer`, `model`, `seats`, `type` (`['Narrow Body', 'Wide Body', 'Regional Jet']`), `range`, `cruiseSpeed`, `engineType`, `inService`, `lastMaintenance`, `nextMaintenance`.
- `FlightModel`: `flightCode`, `departureAirport` (ref `Airport`), `arrivalAirport` (ref `Airport`), `departureTime`, `arrivalTime`, `flightDuration`, `flightClass.{economy,business}.{price, seatsAvailable}`, `aircraft` (ref `Aircraft`), `flightStatus` (`['Scheduled', 'On time', 'Delayed', 'Landed', 'In flight']`).
- `PassengerModel`: `name`, `email`.
- `BookingModel`: `userID` (ref `User`), `flightID` (ref `Flight`), `flightClass` (`['economy', 'business']`), `passengerCount`, `passengers[]` (ref `Passenger`), `bookingDate`, `totalPrice`.
- `ContentModel`, `FileModel`.

#### E. Các lỗi thực tế & Khó khăn khi áp dụng AI Agent kiểm thử QAirline
Qua đọc mã nguồn các controller ([BookingController.js](file:///home/vietanh/Workspaces/self/ApiTesting/QAirline/backend/controllers/BookingController.js), [UserController.js](file:///home/vietanh/Workspaces/self/ApiTesting/QAirline/backend/controllers/UserController.js), [FlightController.js](file:///home/vietanh/Workspaces/self/ApiTesting/QAirline/backend/controllers/FlightController.js)), nhóm phát hiện các đặc điểm & vấn đề thực tế:
1. **Thiếu OpenAPI Specification hoàn chỉnh:** Vì route chưa có `@swagger`, AI Agent không có đầu vào chuẩn ngay lập tức. Cần bổ sung bước chuẩn hóa/tạo file `openapi.yaml` từ source code (hoặc thêm JSDoc `@swagger`) làm đầu vào cho thực nghiệm.
2. **Phụ thuộc trạng thái sâu (Deep Stateful Dependencies):** Để test `POST /api/bookings`, phải tồn tại `userID`, `flightID`, `passengerIDs[]`; để tạo `Flight`, phải tồn tại `departureAirport`, `arrivalAirport`, `aircraft`. Nếu chạy request độc lập, đa số sẽ thất bại với `404` hoặc `500`.
3. **Lỗi xử lý ngoại lệ thực tế trong code (Real Defects để Agent phát hiện):**
   - Trong `UserController.getUserById`: nếu truyền `:id` không đúng định dạng 24-hex ObjectId, `User.findById` ném `CastError` và trả về **HTTP 500** thay vì `400/404`.
   - Trong `BookingController.createBooking`: dòng 54–55 gọi `user.bookings.push(...)` mà không kiểm tra `if (!user)` — nếu `userID` hợp lệ về định dạng ObjectId nhưng không tồn tại trong DB, hệ thống lưu xong `Booking` rồi crash với `TypeError` -> **HTTP 500** (gây dữ liệu rác không rollback).
   - Trong `UserController.createUser`: trả về cả trường `password` (đã hash) trong JSON response; trùng `username` trả `400` thay vì `409`.
   - Không có middleware xác thực JWT/RBAC bảo vệ các endpoint nhạy cảm như `DELETE /api/users/:id` hay `POST /api/flights`.
4. **Rủi ro dữ liệu:** Hardcode Atlas URI trong `db.js` khiến việc chạy fuzzing/testing trực tiếp có thể làm hỏng dữ liệu chung.

### 1.3. Phạm vi nghiên cứu & Chuẩn bị môi trường thực nghiệm
- **Phạm vi API thực nghiệm:** Tập trung vào **6 nhóm API nghiệp vụ cốt lõi (34 endpoints)**: `Users`, `Airports`, `Aircrafts`, `Flights`, `Passengers`, `Bookings` (loại trừ `FileRoute` binary upload và `SchedulerRoute` cron nội bộ khỏi vòng lặp sinh JSON tự động chính để đảm bảo tính tập trung).
- **Môi trường thử nghiệm an toàn & Reset DB:**
  - Chạy MongoDB cục bộ qua Docker (`mongo:7`) và cấu hình `process.env.MONGO_URI` trong `QAirline/backend/config/db.js` (không đụng vào Atlas URI).
  - Xây dựng `seed.js` / `reset_db.py` để xóa sạch các collection và nạp lại dữ liệu nền tối thiểu (ví dụ: 2 airports, 1 aircraft, 1 flight, 1 user, 1 passenger) trước mỗi phiên đánh giá baseline hoặc trước mỗi kịch bản phá hủy dữ liệu.

---

## Phần 2. Related Work (Nghiên cứu 5 công trình khoa học liên quan)

### 2.1. Danh sách 5 bài báo khoa học được lựa chọn (2023–2025)

1. **Paper 1 (RESTGPT):** Kim, M., Stennett, T., Shah, D., Sinha, S., & Orso, A. (2024). *Leveraging Large Language Models to Improve REST API Testing*. In **ICSE-NIER 2024** (46th IEEE/ACM International Conference on Software Engineering: New Ideas and Emerging Results). DOI: `10.48550/arXiv.2312.00894` ([arXiv:2312.00894](https://arxiv.org/abs/2312.00894)).
2. **Paper 2 (KAT):** Le, T., et al. (2024). *KAT: Dependency-Aware Automated API Testing with Large Language Models*. In **ICST 2024** (IEEE Conference on Software Testing, Verification and Validation). DOI: `10.1109/ICST60714.2024.00017`.
3. **Paper 3 (AutoRestTest):** Kim, M., Stennett, T., Sinha, S., & Orso, A. (2025). *A Multi-Agent Approach for REST API Testing with Semantic Graphs and LLM-Driven Inputs*. In **ICSE 2025** (47th IEEE/ACM International Conference on Software Engineering). DOI: `10.48550/arXiv.2501.08600` ([arXiv:2501.08600](https://arxiv.org/abs/2501.08600)).
4. **Paper 4 (RBCTest):** Huynh, M.-H., Le, Q.-T., Nguyen, T., Nguyen, V., Nguyen, V., & Nguyen, T. N. (2024). *Using LLM for Mining and Testing Constraints in API Testing*. In **ASE 2024** (39th IEEE/ACM International Conference on Automated Software Engineering). DOI: `10.1145/3691620.3695341`.
5. **Paper 5 (LlamaRestTest):** Kim, M., Sinha, S., & Orso, A. (2025). *LlamaRestTest: Effective REST API Testing with Small Language Models*. In **FSE 2025** (Proceedings of the ACM on Software Engineering). [arXiv:2501.08598](https://arxiv.org/abs/2501.08598).

---

### 2.2. Phân tích chi tiết từng Paper

#### Paper 1: RESTGPT (ICSE-NIER 2024)
| Nội dung | Phân tích chi tiết |
|---|---|
| **Problem** | Các công cụ kiểm thử REST API truyền thống bỏ qua phần mô tả bằng ngôn ngữ tự nhiên (natural language descriptions) trong OpenAPI Specification (OAS), dẫn đến sinh giá trị tham số kém chính xác và độ phủ thấp. |
| **Motivation** | Tài liệu OpenAPI thực tế chứa rất nhiều ràng buộc nghiệp vụ, định dạng và ví dụ nằm trong trường `description` thay vì schema hình thức (`pattern`, `enum`, `minimum`). |
| **Methodology** | Dùng LLM phân tích văn bản mô tả trong OAS để trích xuất các quy tắc ràng buộc máy đọc được (machine-interpretable rules) và sinh giá trị mẫu theo ngữ cảnh, sau đó làm giàu (augment) trực tiếp vào file OAS gốc. |
| **Architecture** | Pipeline tiền xử lý OAS: `OAS Parser -> LLM Prompting (Rule & Example Extractor) -> Augmented OAS -> Existing Black-box Testers (RESTler, EvoMaster)`. |
| **AI/LLM** | Sử dụng GPT (prompt engineering có cấu trúc) để trích xuất ràng buộc tham số và sinh example values. |
| **Dataset** | Tập các RESTful services thực tế có OpenAPI specification (cùng benchmark với ARAT-RL / EvoMaster). |
| **Evaluation** | So sánh tỷ lệ trích xuất đúng ràng buộc/giá trị và mức tăng độ phủ (code/operation coverage) khi đưa Augmented OAS vào công cụ test so với OAS gốc. |
| **Results** | Vượt trội các kỹ thuật trích xuất ràng buộc dựa trên NLP truyền thống và giúp công cụ kiểm thử đạt độ phủ cao hơn. |
| **Limitations** | Chỉ xử lý tĩnh trước khi chạy test (offline spec enhancement); chưa xử lý chuỗi phụ thuộc nhiều bước hay kiểm tra response oracle. |
| **Applicability** | **Kế thừa:** Dùng LLM làm giàu OpenAPI spec của QAirline (trích xuất format `flightCode`, `airport code`, `flightClass`, ràng buộc ngày tháng). **Điều chỉnh:** Kết hợp thêm bước đọc Mongoose schema/route của QAirline khi tạo spec. **Đóng góp riêng:** Tự động phân loại rule thành `input_constraint` và `business_rule`. |

#### Paper 2: KAT (ICST 2024)
| Nội dung | Phân tích chi tiết |
|---|---|
| **Problem** | Các công cụ fuzzing truyền thống gặp bế tắc khi một endpoint cần dữ liệu đầu vào được sinh ra từ response của endpoint khác (ví dụ: `booking` cần `flightID`). |
| **Motivation** | Heuristic khớp tên trường đơn thuần (string matching) bỏ sót nhiều phụ thuộc ngữ nghĩa (ví dụ `flightID` trong `Booking` ứng với `_id` của `Flight`). |
| **Methodology** | Xây dựng **Operation Dependency Graph (ODG)** $G=(N, V)$ bằng phương pháp lai: (1) Heuristic khớp tên trường + (2) LLM phân tích ngữ nghĩa OAS để tìm phụ thuộc `Operation-Schema` và `Schema-Schema`; sau đó sinh kịch bản test theo thứ tự topo và sinh script kiểm tra ràng buộc. |
| **Architecture** | `OAS -> Hybrid ODG Builder (Heuristic + GPT) -> Dependency-Aware Test Sequence & Constraint Script Generator -> Executor`. |
| **AI/LLM** | GPT thực hiện suy luận ngữ nghĩa xây dựng cạnh phụ thuộc trong ODG, sinh dữ liệu đầu vào hợp ngữ cảnh và sinh script kiểm tra ràng buộc. |
| **Dataset** | 12 RESTful services thực tế. |
| **Evaluation** | Test coverage (operation/branch coverage), số lỗi phát hiện được (đặc biệt 5xx), và tỷ lệ giảm False Positive nhờ kiểm tra ràng buộc ngữ nghĩa. |
| **Results** | Đạt coverage cao hơn và giảm đáng kể false positive so với các công cụ state-of-the-art thời điểm đó. |
| **Limitations** | Phụ thuộc nhiều vào độ đầy đủ của OAS; đồ thị ODG tĩnh không tự cập nhật nếu server trả về cấu trúc lỗi bất ngờ khi chạy. |
| **Applicability** | **Kế thừa:** Mô hình ODG lai (Heuristic + LLM) để xây dựng thứ tự gọi API cho QAirline (`Airport/Aircraft -> Flight -> Passenger/User -> Booking`). **Đóng góp riêng:** Bổ sung trích xuất phụ thuộc từ khóa ngoại Mongoose (`ref: 'Flight'`) để tăng độ chính xác 100% cho cạnh phụ thuộc. |

#### Paper 3: AutoRestTest (ICSE 2025)
| Nội dung | Phân tích chi tiết |
|---|---|
| **Problem** | Làm sao kết hợp tối ưu việc chọn endpoint, giải quyết phụ thuộc, chọn tham số và sinh giá trị trong kiểm thử hộp đen REST API. |
| **Motivation** | Các công cụ trước đây tách rời việc sinh chuỗi request và sinh giá trị, hoặc chỉ dùng LLM cho toàn bộ quá trình gây tốn kém chi phí và chậm. |
| **Methodology** | Đề xuất **Semantic Property Dependency Graph (SPDG)** kết hợp với **Multi-Agent Reinforcement Learning (MARL)** gồm 4 agent cộng tác (API Agent, Dependency Agent, Parameter Agent, Value Agent) và LLM sinh giá trị domain-specific. |
| **Architecture** | Kiến trúc 4-Agent MARL tương tác qua bảng Q-value/phần thưởng dựa trên HTTP status code (2xx/4xx/5xx) kết hợp SPDG và LLM Value Pool. |
| **AI/LLM** | LLM đóng vai trò sinh giá trị ngữ nghĩa và hiểu mô tả OAS; MARL tối ưu hóa chính sách chọn tổ hợp `(endpoint, dependency, parameter, value)`. |
| **Dataset** | Benchmark các dịch vụ REST thực tế (bao gồm các dịch vụ trong EvoMaster/ARAT-RL benchmark). |
| **Evaluation** | Code coverage (line/branch), operation coverage, và số lỗi 500 Internal Server Error phát hiện được. |
| **Results** | Đạt hiệu năng state-of-the-art về operation coverage và phát hiện lỗi so với RESTler, EvoMaster, ARAT-RL. |
| **Limitations** | Cơ chế MARL 4 agent phức tạp khi cài đặt, cần thời gian hội tụ lớn và chi phí điều chỉnh hyperparameters. |
| **Applicability** | **Kế thừa:** Ý tưởng SPDG và cơ chế chấm điểm phần thưởng (reward) khi tìm ra `2xx` mới hoặc `5xx`. **Điều chỉnh:** Đơn giản hóa MARL thành **Single Agent Orchestrator với Priority Queue + Feedback Memory** để phù hợp quy mô bài tập lớn nhưng vẫn giữ được tính thích nghi. |

#### Paper 4: RBCTest (ASE 2024)
| Nội dung | Phân tích chi tiết |
|---|---|
| **Problem** | Kiểm thử chỉ dựa trên HTTP status code (2xx vs 5xx) bỏ sót rất nhiều lỗi logic nằm bên trong **response body** (ví dụ: API trả về 200/201 nhưng `totalPrice` tính sai hoặc vẫn còn trường `password`). |
| **Motivation** | Cần tự động hóa việc xây dựng **Test Oracle** cho nội dung JSON response dựa trên mô tả API. |
| **Methodology** | Dùng LLM khai phá các ràng buộc bất biến của response body (**Response Body Constraints - RBC**) từ tài liệu API (ví dụ: quan hệ giữa input và output, ràng buộc giá trị trường trả về), sau đó tự động sinh mã kiểm tra (assertion/verification scripts) để đối chiếu response thực tế. |
| **Architecture** | `API Docs -> LLM Constraint Miner (Prompting + Few-shot) -> Constraint Formalizer -> Executable Oracle Verifier -> Bug Report`. |
| **AI/LLM** | LLM (GPT) trích xuất ràng buộc logic từ mô tả endpoint và sinh biểu thức/hàm kiểm tra JSON response. |
| **Dataset** | Tập các RESTful APIs thực tế có tài liệu mô tả chi tiết và các lỗi response được gán nhãn. |
| **Evaluation** | Precision/Recall của việc khai phá ràng buộc đúng và tỷ lệ phát hiện lỗi response (Oracle accuracy / Defect detection). |
| **Results** | Phát hiện được nhiều lỗi logic nghiệp vụ trong response body mà kiểm tra status code hoặc schema validator thông thường bỏ qua. |
| **Limitations** | Có thể sinh False Positive nếu mô tả API mơ hồ hoặc LLM suy diễn sai quy tắc nghiệp vụ ngầm. |
| **Applicability** | **Kế thừa trực tiếp:** Xây dựng module **Response Validator** cho QAirline (kiểm tra `totalPrice == passengerCount * price`, `seatsAvailable` giảm đúng `passengerCount` sau booking, không rò rỉ dữ liệu nhạy cảm). **Đóng góp riêng:** Phân tách rõ oracle thành 3 tầng: Status Code -> JSON Schema -> LLM-mined Business Invariants. |

#### Paper 5: LlamaRestTest (FSE 2025)
| Nội dung | Phân tích chi tiết |
|---|---|
| **Problem** | Phụ thuộc hoàn toàn vào LLM thương mại cỡ lớn (GPT-4) gây tốn chi phí, chậm và lo ngại bảo mật dữ liệu; đồng thời LLM tĩnh không học được từ phản hồi lỗi của server. |
| **Motivation** | Chứng minh các mô hình ngôn ngữ nhỏ (SLM ~8B) được tinh chỉnh chuyên biệt kết hợp vòng phản hồi từ server có thể đạt hiệu quả tương đương hoặc vượt LLM lớn. |
| **Methodology** | Fine-tune và lượng tử hóa 2 mô hình **Llama-3-8B** trên dữ liệu giá trị mẫu và phụ thuộc liên tham số (Inter-Parameter Dependencies - IPDs); tích hợp **vòng phản hồi từ server response** (ví dụ đọc thông báo lỗi `400 Bad Request` để tự sửa payload ở lần thử sau). |
| **Architecture** | `OAS -> SLM (Value & IPD Models) -> Test Executor -> Server Response Feedback Loop (RL/Memory) -> Refined Test Inputs`. |
| **AI/LLM** | Hai mô hình SLM (Llama-3-8B) chuyên biệt cho sinh giá trị và phát hiện IPD từ phản hồi server. |
| **Dataset** | 12 dịch vụ REST thực tế (bao gồm Spotify, v.v.). |
| **Evaluation** | So sánh với RESTler, MoRest, EvoMaster, ARAT-RL và RESTGPT về operation coverage, valid input rate và phát hiện lỗi. |
| **Results** | Vượt các baseline truyền thống và cả công cụ dùng GPT tĩnh (RESTGPT) trong việc sinh input hợp lệ và khám phá IPD ẩn. |
| **Limitations** | Đòi hỏi hạ tầng GPU để fine-tune và host Llama-3-8B cục bộ. |
| **Applicability** | **Kế thừa:** Cơ chế **Feedback-driven Retry & Memory** (phân tích thông báo lỗi `400` như *"Invalid flight class selected"* hoặc *"Not enough seats available"* để tự động điều chỉnh input ở vòng lặp kế tiếp). **Điều chỉnh:** Thay vì fine-tune Llama-3-8B (nặng về phần cứng cho BTL), dùng **Few-shot In-Context Learning + Error Memory** với LLM API/Ollama nhẹ. |

---

### 2.3. Bảng so sánh 5 Paper & Research Gap

| Tiêu chí | RESTGPT (ICSE-NIER'24) | KAT (ICST'24) | AutoRestTest (ICSE'25) | RBCTest (ASE'24) | LlamaRestTest (FSE'25) |
|---|---|---|---|---|---|
| **Trọng tâm chính** | Làm giàu OpenAPI Spec | Đồ thị phụ thuộc ODG | SPDG + Multi-Agent RL | Khai phá Oracle (Response Body) | SLM + Feedback Loop |
| **Xử lý phụ thuộc API** | Không | **Rất mạnh (ODG)** | **Rất mạnh (SPDG + MARL)** | Không | Có (IPD nội bộ) |
| **Sinh dữ liệu thông minh** | Tốt (từ mô tả OAS) | Tốt (GPT) | Tốt (LLM Value Pool) | Không | **Rất tốt (SLM + Feedback)** |
| **Kiểm tra Response Oracle** | Chỉ status code | Ràng buộc cơ bản | Chỉ status code (5xx) | **Rất mạnh (RBC Mining)** | Chỉ dùng để feedback |
| **Vòng lặp phản hồi (Memory)** | Không (Tĩnh) | Hạn chế | Có (MARL reward) | Không | **Có (Server Error Feedback)** |
| **Độ phức tạp triển khai** | Thấp | Trung bình | Rất cao (4-agent MARL) | Trung bình | Cao (cần fine-tune SLM) |

**Research Gap tổng hợp:**
1. Chưa có sự kết hợp gọn nhẹ giữa **ODG/SPDG (giải quyết chuỗi phụ thuộc)** + **Feedback-driven Input Repair (tự sửa test input từ lỗi 4xx)** + **Response Body Constraint Oracle (phát hiện lỗi logic 2xx sai dữ liệu)** trong một kiến trúc thống nhất, chi phí thấp.
2. Các nghiên cứu thường giả định OpenAPI Spec đã có sẵn và đầy đủ, trong khi các dự án thực tế (như `QAirline`) thường thiếu hoặc có OpenAPI Spec rỗng, đòi hỏi bước chuẩn hóa từ mã nguồn.

---

## Phần 3. Proposed Methodology (Phương pháp đề xuất & Kiến trúc AI Agent)

### 3.1. Đề xuất Research Questions (RQs)
- **RQ1 (Specification & Dependency):** Làm thế nào để khai thác kết hợp cấu trúc OpenAPI và suy luận ngữ nghĩa của LLM để xây dựng đồ thị phụ thuộc API chính xác, giúp sinh chuỗi kiểm thử có trạng thái (stateful) trên QAirline? *(Tham khảo: RESTGPT, KAT)*
- **RQ2 (Feedback-driven Test Generation):** Cơ chế bộ nhớ và phản hồi từ HTTP response (`Test Memory & Feedback`) giúp cải thiện tỷ lệ test case hợp lệ (`Test Case Validity`) và khả năng sinh boundary/edge cases như thế nào so với sinh một lần (one-shot LLM)? *(Tham khảo: LlamaRestTest, AutoRestTest)*
- **RQ3 (Response Oracle & Defect Detection):** Việc áp dụng khai phá ràng buộc Response Body bằng LLM (`Response Validator`) có giúp phát hiện các lỗi nghiệp vụ/an toàn ẩn sau mã trạng thái `200/201` mà kiểm tra status code thông thường bỏ sót hay không? *(Tham khảo: RBCTest)*
- **RQ4 (Effectiveness vs Baselines):** Hệ thống AI Agent tích hợp đề xuất đạt hiệu quả như thế nào về độ phủ endpoint, số lỗi duy nhất phát hiện được và chi phí thực thi so với Manual, Random, Schema-based và Non-Agent LLM?

### 3.2. Lựa chọn kiến trúc: Single Agent Orchestrator vs Multi-Agent
- **So sánh:**
  - *Multi-Agent (như AutoRestTest):* 4 agent độc lập giao tiếp qua RL, mạnh trên hệ thống cực lớn nhưng khó debug, tốn token, khó đồng bộ trong đồ án 5 người.
  - *Single Agent Orchestrator + Modular Tools (Đề xuất):* Một **Agent điều phối trung tâm** nắm giữ trạng thái (`State/Memory`) và gọi tuần tự/thích nghi **9 module chuyên biệt** (như các tool/component).
- **Quyết định:** Chọn **Single Agent Orchestrator với 9 module chuyên biệt**. Giải pháp này kế thừa đầy đủ điểm mạnh của 5 paper (ODG của KAT, Spec Enhancement của RESTGPT, Feedback Loop của LlamaRestTest, Response Oracle của RBCTest) nhưng giữ kiến trúc sạch, dễ kiểm soát hallucination và dễ phân chia cho 5 thành viên.

### 3.3. Chi tiết 9 thành phần trong Kiến trúc AI Agent

| # | Thành phần | Nhiệm vụ | Input -> Output | Kỹ thuật / Thuật toán | AI/LLM | Paper tham khảo |
|---|---|---|---|---|---|---|
| 1 | **API Specification Analyzer** | Chuẩn hóa & trích xuất endpoint, method, schema, mô tả và quy tắc ẩn từ OpenAPI 3.0. | `openapi.yaml` -> `StructuredAPISpec` (JSON) | OpenAPI Parser + Prompt trích xuất ràng buộc định dạng/miền giá trị. | LLM (Structured Output) | **RESTGPT** (ICSE-NIER'24) |
| 2 | **API Dependency Analyzer** | Xây dựng đồ thị phụ thuộc có hướng $G=(V,E)$ và sắp xếp thứ tự topo cho chuỗi gọi API. | `StructuredAPISpec` -> `ODG` & `ExecutionOrder` | Heuristic khớp tên trường (`_id` $\leftrightarrow$ `flightID`) + LLM suy luận ngữ nghĩa. | LLM (Semantic Edge Inference) | **KAT** (ICST'24) & **AutoRestTest** (ICSE'25) |
| 3 | **Test Case Generator** | Sinh kịch bản test (Valid, Invalid, Boundary, Edge, Stateful Sequence) cho từng endpoint/chuỗi. | `StructuredAPISpec` + `ODG` -> `AbstractTestCases` | Equivalence Partitioning, Boundary Value Analysis + LLM Scenario Planning. | LLM (Chain-of-Thought) | **KAT** & **AutoRestTest** |
| 4 | **Test Data Generator** | Sinh payload JSON cụ thể; thay thế biến phụ thuộc (`{{flight._id}}`); tự sửa dữ liệu khi nhận phản hồi lỗi. | `AbstractTestCases` + `TestMemory` -> `ConcretePayloads` | Template substitution + Context-aware LLM value generation + Mutation. | LLM (Few-shot + Repair) | **RESTGPT** & **LlamaRestTest** (FSE'25) |
| 5 | **Test Execution Engine** | Thực thi HTTP requests (`GET/POST/PUT/DELETE`), quản lý headers, timeout, lưu vết request/response. | `ConcretePayloads` -> `ExecutionTrace` | `httpx` async/sync client, trích xuất ID từ response lưu vào runtime context. | Không | Chuẩn thực thi (**RESTler/KAT**) |
| 6 | **Response Validator** | Kiểm chứng 3 tầng: (1) Status code, (2) JSON Schema, (3) Business & Security Oracles. | `ExecutionTrace` + `RBC Rules` -> `ValidationResult` | `jsonschema` validator + LLM-mined assertion rules (Python expressions). | LLM (Oracle Mining offline) | **RBCTest** (ASE'24) |
| 7 | **Defect Analyzer** | Phân loại lỗi (`5xx Crash`, `Schema Mismatch`, `Business Logic Bug`, `Security/Data Leak`), khử trùng lặp (deduplication). | `ValidationResult` (Failed) -> `UniqueDefects` | Rule-based clustering theo `(endpoint, status_code, error_signature)`. | LLM (Tóm tắt nguyên nhân lỗi) | **RBCTest** & **AutoRestTest** |
| 8 | **Test Memory & Feedback Mechanism** | Lưu trữ các ID tài nguyên đã tạo (`userID`, `flightID`), lịch sử lỗi `4xx` và phần thưởng độ phủ để điều hướng vòng sau. | `ExecutionTrace` -> `UpdatedMemory` & `RepairHints` | Key-Value Resource Pool + Error-Feedback Prompting (max $K$ retries). | Không / Context Injection | **LlamaRestTest** (FSE'25) |
| 9 | **Report Generator** | Tổng hợp metrics (Coverage, Validity, Defect Rate), xuất báo cáo Markdown/HTML/JSON kèm curl tái hiện. | `UniqueDefects` + `Metrics` -> `TestReport.md/html` | Template rendering (Jinja2 / Markdown). | Không | Yêu cầu hệ thống |

### 3.4. Quy trình hoạt động End-to-End & Pseudo-code

```mermaid
flowchart TD
    A["OpenAPI Specification (openapi.yaml)"] --> B["1. API Specification Analyzer (RESTGPT)"]
    B --> C["2. API Dependency Analyzer - ODG (KAT/SPDG)"]
    C --> D["3. Test Case Generator (Valid/Invalid/Boundary/Stateful)"]
    D --> E["4. Test Data Generator"]
    M["8. Test Memory & Feedback Pool"] <--> E
    E --> F["5. Test Execution Engine (HTTP Client)"]
    F --> G["6. Response Validator 3 Tầng (RBCTest)"]
    G -->|Pass / Tạo được Resource| M
    G -->|4xx Có thể sửa (Max K=2)| M
    G -->|5xx / Sai Schema / Sai Business Rule| H["7. Defect Analyzer & Deduplication"]
    H --> I["9. Report Generator (Markdown / HTML / JSON)"]
```

**Pseudo-code vòng lặp Agent Feedback Loop (kết hợp KAT + LlamaRestTest + RBCTest):**
```python
def run_agent_testing(openapi_path, base_url, max_retries=2):
    spec = spec_analyzer.analyze(openapi_path)                 # RESTGPT
    odg = dependency_analyzer.build_odg(spec)                  # KAT
    ordered_sequences = topological_sort(odg)
    oracles = response_validator.mine_oracles(spec)            # RBCTest
    memory = TestMemory()

    for seq in ordered_sequences:
        abstract_cases = test_case_gen.generate(seq, spec)
        for case in abstract_cases:
            for attempt in range(max_retries + 1):
                payload = data_gen.generate(case, memory, repair_hint=memory.last_hint(case))
                trace = executor.execute(base_url, payload)
                memory.update_resources(trace)                 # Lưu _id mới tạo (vd: flightID)
                val_result = response_validator.validate(trace, oracles)

                if val_result.is_defect:
                    defect_analyzer.record(trace, val_result)
                    break
                if val_result.needs_repair and attempt < max_retries:
                    memory.store_hint(case, trace.response_body) # LlamaRestTest feedback
                    continue
                break

    return report_generator.export(defect_analyzer.get_unique_defects(), memory.metrics())
```

---

## Phần 4. Team Assignment (Phân công công việc cho 5 thành viên)

Mỗi thành viên phụ trách **1 paper khoa học** + **triển khai module tương ứng** + **viết phần báo cáo nghiên cứu & thực nghiệm của module đó**:

| Thành viên | Paper nghiên cứu phụ trách | Chủ đề nghiên cứu | Module triển khai phụ trách | Task chi tiết & Đầu ra cụ thể |
|---|---|---|---|---|
| **Nguyễn Việt Anh** | **Paper 1: RESTGPT** (ICSE-NIER 2024) | Trích xuất ràng buộc từ ngôn ngữ tự nhiên & chuẩn hóa OpenAPI Spec | **Module 1:** API Specification Analyzer + Chuẩn hóa OpenAPI cho QAirline | - Phân tích paper RESTGPT.<br>- Rà soát 34 endpoints & Mongoose models của QAirline để viết `specs/qairline_openapi.yaml`.<br>- Code `spec_analyzer/` dùng LLM trích xuất rule ẩn & example values.<br>- Chạy Baseline 4 (Non-Agent LLM one-shot) để so sánh. |
| **Lê Tiến Thành** | **Paper 2: KAT** (ICST 2024) | Đồ thị phụ thuộc ODG & sinh chuỗi kiểm thử có trạng thái | **Module 2:** API Dependency Analyzer + **Module 3:** Test Case Generator | - Phân tích paper KAT.<br>- Code `dependency_analyzer/` dựng đồ thị ODG (`networkx`) kết hợp heuristic + LLM.<br>- Thực hiện topological sort tạo chuỗi gọi API có trạng thái.<br>- Sinh abstract test cases (Valid, Invalid, Boundary, Edge, Stateful). |
| **Tô Quang Hưng** | **Paper 5: LlamaRestTest** (FSE 2025) | Sinh dữ liệu ngữ nghĩa & vòng lặp tự sửa lỗi từ phản hồi server | **Module 4:** Test Data Generator + **Module 8:** Test Memory & Feedback | - Phân tích paper LlamaRestTest.<br>- Code `data_generator/` sinh payload JSON theo ngữ cảnh & thay thế biến phụ thuộc (`{{flight._id}}`).<br>- Xây dựng `TestMemory` lưu ID tài nguyên và cơ chế Error-Feedback Retry (tự sửa payload khi gặp `4xx`). |
| **Vũ Đức An** | **Paper 3: AutoRestTest** (ICSE 2025) | Kiến trúc điều phối Agent, thực thi tự động & đo độ phủ | **Agent Orchestrator** (`main.py`) + **Module 5:** Test Execution Engine + **Module 9:** Report Generator + Docker/DB Reset | - Phân tích paper AutoRestTest.<br>- Dựng `docker-compose.yml` (MongoDB local + QAirline) & viết `reset_db.py`.<br>- Code `executor/` (`httpx`), vòng lặp điều phối Agent trong `main.py` và `reporter/` xuất báo cáo MD/HTML.<br>- Chạy Baseline 2 (Random) & Baseline 3 (Schema-based). |
| **Vũ Minh Thành** | **Paper 4: RBCTest** (ASE 2024) | Khai phá Response Body Constraints & phát hiện lỗi nghiệp vụ | **Module 6:** Response Validator (3 tầng) + **Module 7:** Defect Analyzer | - Phân tích paper RBCTest.<br>- Lập bảng Ground-truth bugs của QAirline và viết Baseline 1 (Manual Test Cases).<br>- Code `validator/` kiểm tra 3 tầng (Status Code, JSON Schema, LLM-mined Business Oracles).<br>- Code phân loại & khử trùng lặp lỗi (`UniqueDefects`). |

---

## Phần 5. Implementation Plan (Kế hoạch kỹ thuật & Cấu trúc Project)

### 5.1. Công nghệ đề xuất
- **Ngôn ngữ chính:** Python 3.11+ (hệ sinh thái mạnh cho AI/LLM, `httpx`, `networkx`, `jsonschema`).
- **LLM Integration:** `litellm` hoặc SDK chuẩn (hỗ trợ linh hoạt OpenAI GPT-4o-mini / Gemini Flash / hoặc Ollama local để tối ưu chi phí và chống phụ thuộc một nhà cung cấp).
- **Quản lý dữ liệu & Schema:** `pydantic` v2 (định nghĩa contract chuẩn giữa các module), `prance` / `pyyaml` (đọc OpenAPI 3.0), `jsonschema` (validate response).
- **Môi trường hệ thống mục tiêu (QAirline):** Docker Compose chạy `mongo:7` + `QAirline/backend` (port `5000`), kèm script `reset_db.py` (dùng `pymongo`).

### 5.2. Cấu trúc thư mục Project đề xuất
```text
ApiTesting/
├── QAirline/                      # Hệ thống mục tiêu (chỉnh sửa tối thiểu config env + seed)
├── specs/
│   └── qairline_openapi.yaml      # OpenAPI 3.0 spec chuẩn hóa (Nguyễn Việt Anh)
├── agent/                         # Mã nguồn hệ thống AI Agent (Python)
│   ├── main.py                    # Agent Orchestrator (Vũ Đức An)
│   ├── models/
│   │   └── contracts.py           # Pydantic models dùng chung cho 9 module (Cả nhóm)
│   ├── spec_analyzer/             # Module 1: RESTGPT-based (Nguyễn Việt Anh)
│   ├── dependency_analyzer/       # Module 2 & 3: KAT-based ODG & Case Gen (Lê Tiến Thành)
│   ├── data_generator/            # Module 4 & 8: LlamaRestTest-based Data & Memory (Tô Quang Hưng)
│   ├── executor/                  # Module 5: HTTP Runner & DB Reset (Vũ Đức An)
│   ├── validator/                 # Module 6 & 7: RBCTest-based Oracle & Defect (Vũ Minh Thành)
│   └── reporter/                  # Module 9: Markdown/HTML Report Generator (Vũ Đức An)
├── baselines/                     # Manual (Vũ Minh Thành), Random & Schema (Vũ Đức An), One-shot LLM (Nguyễn Việt Anh)
├── experiments/                   # Kết quả chạy thực nghiệm, logs, ground-truth bugs
├── docker-compose.yml             # MongoDB local + QAirline backend (Vũ Đức An)
└── requirements.txt
```

### 5.3. Kế hoạch tích hợp (Integration Contract)
- Toàn bộ 5 thành viên thống nhất file `agent/models/contracts.py` ngay từ **Tuần 2** với 4 cấu trúc dữ liệu lõi: `EndpointSpec`, `TestCase`, `ExecutionTrace`, `DefectReport`.
- Mỗi module có unit test độc lập (`pytest`) sử dụng mock JSON trước khi ghép vào `main.py` ở Giai đoạn 4.

---

## Phần 6. Experimental Design (Thiết kế thực nghiệm & Đánh giá)

### 6.1. Môi trường & Dataset thực nghiệm
- **Đối tượng:** 34 endpoints thuộc 6 nhóm nghiệp vụ cốt lõi của `QAirline` (`Users`, `Airports`, `Aircrafts`, `Flights`, `Passengers`, `Bookings`).
- **Quy mô sinh test case mục tiêu:** Tối thiểu **50–100 test cases** bao phủ cả 4 loại: Valid, Invalid, Boundary, và Stateful Multi-step (vượt mức tối thiểu 30–50 của đề bài).
- **Ground Truth:** Nhóm rà soát mã nguồn `QAirline/backend/controllers/` để lập danh sách các lỗi thực tế đã biết (ví dụ: `CastError` 500 khi sai ObjectId, `TypeError` 500 khi `userID` không tồn tại lúc tạo booking, rò rỉ trường `password` hash khi tạo user, thiếu auth trên endpoint xóa).

### 6.2. Các Baseline so sánh (5 phương pháp)
1. **Baseline 1 — Manual Test Cases:** Bộ test viết tay bằng Postman/Pytest bởi thành viên nhóm (làm chuẩn tham chiếu).
2. **Baseline 2 — Random-based API Testing:** Gửi request ngẫu nhiên đến các endpoint với chuỗi/số sinh ngẫu nhiên (không dùng schema, không thứ tự).
3. **Baseline 3 — Schema-based Test Generation:** Dùng công cụ sinh test thuần từ OpenAPI schema (như `Schemathesis` hoặc generator chỉ đọc `type`/`required`, không có LLM và không có ODG).
4. **Baseline 4 — Non-Agent LLM (One-shot):** Gửi toàn bộ `openapi.yaml` vào LLM một lần để sinh script test tĩnh, không có đồ thị phụ thuộc ODG, không có Memory/Feedback Loop và không có Response Oracle mining.
5. **Proposed — AI Agent (Ours):** Hệ thống đề xuất tích hợp đủ 9 module.

### 6.3. Evaluation Metrics
| Metric | Định nghĩa & Công thức đo |
|---|---|
| **API Endpoint Coverage (%)** | `(Số endpoint được gọi ít nhất 1 lần hợp lệ / Tổng số 34 endpoints mục tiêu) * 100` |
| **Test Case Validity (%)** | `(Số test case đúng định dạng HTTP/Schema và phục vụ đúng mục tiêu test / Tổng số test case sinh ra) * 100` |
| **Operation Sequence Coverage (%)** | Tỷ lệ các chuỗi phụ thuộc nghiệp vụ (vd: `Airport -> Flight -> Booking`) thực thi thành công đến bước cuối. |
| **Response Validation Accuracy (%)** | Độ chính xác của `Response Validator` khi đối chiếu với Ground Truth (`TP + TN / Total`). |
| **Defect Detection Rate & Unique Defects** | Số lượng lỗi duy nhất (`Unique Defects`) phát hiện được trên tổng số lỗi thực tế của QAirline. |
| **False Positive Rate (%)** | Tỷ lệ cảnh báo lỗi sai trên các request thực chất hoạt động đúng. |
| **Execution Time (s)** | Tổng thời gian từ lúc phân tích spec đến lúc xuất báo cáo. |

### 6.4. Kết quả kỳ vọng
- **Proposed AI Agent** đạt Endpoint Coverage và Operation Sequence Coverage cao hơn rõ rệt so với Random, Schema-based và Non-Agent LLM (nhờ ODG + Memory lưu `flightID`/`userID`).
- **Test Case Validity** tăng đáng kể nhờ cơ chế Error-Feedback Loop (giảm lỗi thiếu trường hoặc sai format).
- **Unique Defects Detected** vượt trội ở nhóm lỗi nghiệp vụ/500 ẩn sâu (nhờ chuỗi Stateful + Response Body Oracle từ RBCTest).

---

## Phần 7. Timeline and Deliverables (Kế hoạch 6 giai đoạn — Dự kiến 8 tuần)

| Giai đoạn | Thời gian | Công việc cụ thể | Phụ trách | Kết quả đầu ra (Deliverables) | Tiêu chí hoàn thành (DoD) |
|---|---|---|---|---|---|
| **GĐ 1: Khảo sát & Nghiên cứu Paper** | Tuần 1–2 | - Dựng Docker MongoDB local cho QAirline (**Vũ Đức An**).<br>- Viết `specs/qairline_openapi.yaml` (**Nguyễn Việt Anh**).<br>- Đọc sâu & tóm tắt 5 paper: RESTGPT (**Việt Anh**), KAT (**Tiến Thành**), LlamaRestTest (**Quang Hưng**), AutoRestTest (**Đức An**), RBCTest (**Minh Thành**). | Cả nhóm (Điều phối chính: **Nguyễn Việt Anh** & **Vũ Đức An**) | Môi trường QAirline chạy local; file `qairline_openapi.yaml`; 5 bản phân tích paper. | QAirline chạy ổn định local; `qairline_openapi.yaml` pass OpenAPI 3.0 validator; 5/5 paper được trình bày. |
| **GĐ 2: Thiết kế phương pháp & Contract** | Tuần 3 | - Chốt 4 RQs & kiến trúc 9 module (**Nguyễn Việt Anh**).<br>- Định nghĩa `agent/models/contracts.py` (**Vũ Đức An** & **Lê Tiến Thành**).<br>- Lập danh sách Ground-truth bugs của QAirline (**Vũ Minh Thành** & **Tô Quang Hưng**). | Cả nhóm | Tài liệu thiết kế kiến trúc; `contracts.py`; bảng Ground-truth bugs. | Các thành viên ký duyệt interface JSON/Pydantic giữa các module. |
| **GĐ 3: Phát triển các Module độc lập** | Tuần 4–5 | - Module 1 (`spec_analyzer`): **Nguyễn Việt Anh**.<br>- Module 2 & 3 (`dependency_analyzer`): **Lê Tiến Thành**.<br>- Module 4 & 8 (`data_generator` & `TestMemory`): **Tô Quang Hưng**.<br>- Module 5 & 9 (`executor` & `reporter`): **Vũ Đức An**.<br>- Module 6 & 7 (`validator` & `defect_analyzer`): **Vũ Minh Thành**. | Từng thành viên theo module phụ trách | 9 module chạy được độc lập kèm unit test (`pytest`). | Mỗi module đạt pass 100% unit test trên dữ liệu mock. |
| **GĐ 4: Tích hợp AI Agent** | Tuần 6 | - Ghép nối 9 module vào `agent/main.py` (**Vũ Đức An** chủ trì).<br>- Chạy thử end-to-end trên QAirline, tinh chỉnh prompt giảm hallucination (**Nguyễn Việt Anh**, **Lê Tiến Thành**, **Tô Quang Hưng**, **Vũ Minh Thành**). | **Vũ Đức An** chủ trì + Cả nhóm debug | Hệ thống AI Agent hoàn chỉnh chạy end-to-end; báo cáo mẫu đầu tiên. | Agent tự động chạy hết 34 endpoints và xuất được `TestReport.md` không crash. |
| **GĐ 5: Thực nghiệm & So sánh Baseline** | Tuần 7 | - Baseline 1 Manual (**Vũ Minh Thành**).<br>- Baseline 2 Random & Baseline 3 Schema (**Vũ Đức An**).<br>- Baseline 4 One-shot LLM (**Nguyễn Việt Anh**).<br>- Chạy thực nghiệm AI Agent 3 lần với `reset_db.py`, thống kê metrics & chấm điểm lỗi (**Lê Tiến Thành**, **Tô Quang Hưng**, **Vũ Minh Thành**). | Cả nhóm theo từng Baseline & Metric | Bảng số liệu thực nghiệm so sánh 5 phương pháp; log request/response. | Có đầy đủ số liệu cho tất cả metrics ở Phần 6 trên >= 50 test cases. |
| **GĐ 6: Hoàn thiện Báo cáo & Thuyết trình** | Tuần 8 | - Tổng hợp báo cáo khoa học 7 phần: mỗi thành viên viết phần paper + module của mình (**Nguyễn Việt Anh** biên tập tổng).<br>- Làm slide (**Lê Tiến Thành**, **Tô Quang Hưng**).<br>- Chuẩn bị kịch bản Demo trực tiếp (**Vũ Đức An**, **Vũ Minh Thành**). | Cả nhóm | Báo cáo PDF/Markdown hoàn chỉnh; Slide; Kịch bản Demo. | Báo cáo rõ ràng phần kế thừa vs đóng góp mới; demo chạy thành công. |

# Năm công trình nền tảng cho công cụ kiểm thử API

Ngày kiểm chứng: 2026-11-25. Chỉ dùng trang hội nghị/nhà xuất bản, bản thảo của tác giả và PDF do nhóm tác giả công bố. Số liệu dưới đây là **kết quả trên benchmark của paper**, không phải kết quả trên QAirline. `plan.md` là bản nháp; các tên, số liệu và phạm vi được đối chiếu lại ở đây.

## Bảng chọn paper và phân công

| Thành viên theo `plan.md` | Công trình đã xác minh | Vai trò trong đề tài |
|---|---|---|
| Nguyễn Việt Anh | **RESTGPT** — M. Kim, T. Stennett, D. Shah, S. Sinha, A. Orso, *Leveraging Large Language Models to Improve REST API Testing*, ICSE 2024 NIER, tr. 37–41. [Hội nghị](https://conf.researchr.org/details/icse-2024/icse-2024-new-ideas-and-emerging-results/12/Leveraging-Large-Language-Models-to-Improve-REST-API-Testing), [paper PDF](https://arxiv.org/pdf/2312.00894). | Chuẩn hóa OpenAPI và trích quy tắc/giá trị từ mô tả. |
| Lê Tiến Thành | **KAT** — T. Le, T. Tran, D. Cao, V. Le, T. N. Nguyen, V. Nguyen, *KAT: Dependency-aware Automated API Testing with Large Language Models*, ICST 2024, DOI [10.1109/ICST60714.2024.00017](https://doi.org/10.1109/ICST60714.2024.00017), [paper PDF](https://arxiv.org/pdf/2407.10227). | Đồ thị phụ thuộc operation và sinh chuỗi request. |
| Vũ Đức An | **AutoRestTest (research paper)** — M. Kim, T. Stennett, S. Sinha, A. Orso, *A Multi-Agent Approach for REST API Testing with Semantic Graphs and LLM-Driven Inputs*, ICSE 2025, DOI [10.1109/ICSE55347.2025.00179](https://doi.org/10.1109/ICSE55347.2025.00179), [IBM](https://research.ibm.com/publications/a-multi-agent-approach-for-rest-api-testing-with-semantic-graphs-and-llm-driven-inputs), [paper PDF](https://arxiv.org/pdf/2411.07098). | Điều phối, ưu tiên khám phá, executor và đo lường. |
| Vũ Minh Thành | **Huynh et al. (poster)** — M.-H. Huynh, Q.-T. Le, T. N. Nguyen, V. Nguyen, *Using LLM for Mining and Testing Constraints in API Testing*, ASE 2024 **Posters**, 2 trang, DOI [10.1145/3691620.3695341](https://doi.org/10.1145/3691620.3695341), [hội nghị](https://conf.researchr.org/details/ase-2024/ase-2024-posters/23/Using-LLM-for-Mining-and-Testing-Constraints-in-API-Testing), [paper PDF](https://katalon.com/hubfs/%5BCommunication%5D%20Research%20Paper/5.%20Using%20LLM%20for%20Mining%20and%20Testing%20Constraints%20in%20API%20Testing.pdf). | Oracle cho ràng buộc response body. |
| Tô Quang Hưng | **LlamaRestTest** — M. Kim, S. Sinha, A. Orso, *LlamaRestTest: Effective REST API Testing with Small Language Models*, *Proceedings of the ACM on Software Engineering* 2(FSE), 2025, DOI [10.1145/3715737](https://doi.org/10.1145/3715737), [IBM](https://research.ibm.com/publications/llamaresttest-effective-rest-api-testing-with-small-language-models), [paper PDF](https://arxiv.org/pdf/2501.08598). | Sinh input theo ngữ nghĩa và học từ server response. |

### 1. RESTGPT — mô tả tự nhiên thành quy tắc và giá trị

- **Bài toán/động lực:** Công cụ đọc phần schema hình thức của OAS nhưng bỏ qua mô tả tự nhiên của parameter. Vì vậy chúng không khai thác được enum, quan hệ giữa tham số hoặc giá trị mẫu chỉ được viết bằng lời.
- **Phương pháp và kiến trúc:** Nhận OpenAPI → chọn description liên quan → prompt LLM trích xuất quy tắc máy đọc được và example values → làm giàu spec → đưa spec tăng cường cho công cụ kiểm thử hiện có. Đây là **bước tiền xử lý spec**, không phải Agent chạy request. Paper trình bày luồng rule generator và specification enhancement trong [PDF, mục 3](https://arxiv.org/pdf/2312.00894).
- **Dữ liệu/đánh giá/kết quả:** 9 REST services có ground truth từ NLP2REST; so sánh trích rule với NLP2REST và giá trị hợp lệ với ARTE. Paper báo **precision 97%** cho trích rule, so với 50% của NLP2REST không validation và 79% có validation; giá trị đúng cú pháp và ngữ nghĩa cho **73% parameter**, so với **17%** của ARTE. Đây là đánh giá sơ bộ trên rule/value, **không chứng minh** coverage hay số lỗi QAirline sẽ tăng. [Bằng chứng](https://arxiv.org/pdf/2312.00894).
- **Giới hạn:** Cần description có thông tin; không tự giải quyết chuỗi phụ thuộc, thực thi, oracle hay feedback. QAirline hiện thiếu OAS có nội dung, nên phải tạo spec có kiểm chứng trước; LLM không thể suy ra luật kinh doanh đáng tin cậy từ mô tả rỗng.
- **Kế thừa cho QAirline:** Trích constraint/value vào một lớp `inferred_rule` có provenance; người phụ trách đối chiếu với model/controller. Tạo OpenAPI cho 34 operation từ mã nguồn là **công việc riêng của nhóm**, không phải đóng góp của RESTGPT.

### 2. KAT — đồ thị phụ thuộc operation

- **Bài toán/động lực:** Một request thường cần ID từ response của operation trước. Ghép tên trường đơn giản dễ bỏ sót `flightID` ↔ `Flight._id`.
- **Phương pháp và kiến trúc:** Xây **Operation Dependency Graph (ODG)**: node là operation, cạnh `A → B` khi output của A cung cấp input của B. KAT kết hợp khớp input/output bằng heuristic với GPT để suy luận quan hệ operation–schema và schema–schema; sau đó sinh chuỗi request, test script, constraint script và dữ liệu. [Thuật toán ODG, mục III-B](https://arxiv.org/pdf/2407.10227).
- **Dữ liệu/đánh giá/kết quả:** 12 REST services; so với RestTestGen về độ phủ **status code được ghi trong spec**, hiệu quả sinh test và lỗi/mismatch. Độ phủ status code tổng hợp trung bình là **74,9% với KAT** và **59,2% với RestTestGen** trong Table II; đây không phải line/branch coverage. [Bảng II và định nghĩa metric](https://arxiv.org/pdf/2407.10227).
- **Giới hạn:** ODG phụ thuộc OAS đủ chính xác; edge do LLM suy ra có thể sai; chuỗi đúng thứ tự vẫn thất bại nếu dữ liệu cụ thể không hợp lệ. Không dùng topological sort đơn thuần cho toàn bộ operation vì CRUD có thể tạo chu trình; cần lập chuỗi theo mục tiêu và quản lý tài nguyên sau mỗi bước.
- **Kế thừa cho QAirline:** Tạo edge `Airport/Aircraft → Flight` và `User/Passenger/Flight → Booking` từ `$ref`, tên trường và `ref` Mongoose. `ref` là nguồn bổ sung **white-box riêng của nhóm**, trong khi KAT làm việc từ OAS. Lưu ID theo loại tài nguyên và output path đã được kiểm chứng.

### 3. AutoRestTest — điều phối khám phá nhiều yếu tố

- **Bài toán/động lực:** Chọn operation, dependency, parameter và value như các việc độc lập tạo ra tổ hợp request kém hiệu quả.
- **Phương pháp và kiến trúc:** Research paper dùng **SPDG** (semantic property dependency graph), LLM cho giá trị theo miền và **4 agent học tăng cường**: API/operation, dependency, parameter, value; reward từ phản hồi HTTP điều chỉnh lựa chọn tiếp theo. [IBM và PDF](https://research.ibm.com/publications/a-multi-agent-approach-for-rest-api-testing-with-semantic-graphs-and-llm-driven-inputs). Có một **tool demo paper riêng** tên *AutoRestTest: A Tool...* mô tả 5 agent có thêm header; không trộn số lượng agent hoặc tên đồ thị của hai ấn phẩm khi trích dẫn. [Tool demo](https://research.ibm.com/publications/autoresttest-a-tool-for-automated-rest-api-testing-using-llms-and-marl).
- **Dữ liệu/đánh giá/kết quả:** 12 dịch vụ thực tế; so với ARAT-RL, EvoMaster, MoRest, RESTler về code coverage (khi có mã), operation coverage và lỗi 500. Trên **3 dịch vụ không có mã nguồn** trong Table II, AutoRestTest thực thi thành công tổng **25 operation**, các baseline tương ứng 11, 10, 10, 9. Không diễn giải số 25 thành kết quả trên cả 12 dịch vụ. [Table II](https://arxiv.org/pdf/2411.07098).
- **Giới hạn:** MARL cần trạng thái, reward và ngân sách chạy lớn; paper tập trung coverage/500, chưa giải quyết oracle nghiệp vụ response body. QAirline chỉ có 34 operation mục tiêu, nên chưa có bằng chứng rằng tái hiện MARL sẽ đáng chi phí.
- **Kế thừa cho QAirline:** Kế thừa ý tưởng **ưu tiên operation chưa được bao phủ** và dùng feedback để chọn ca tiếp theo; triển khai scheduler quy tắc, giới hạn request/time và log quyết định trước. Multi-Agent MARL chỉ là đối chứng kiến trúc, không phải V1.

### 4. Huynh et al. — oracle response body

- **Bài toán/động lực:** Kiểm tra status và schema không bắt được JSON đúng kiểu nhưng sai quan hệ nghiệp vụ (ví dụ thời gian chuyến bay trả về ngoài khoảng lọc).
- **Phương pháp và kiến trúc:** Từ OAS, lọc description của operation, request parameter và response property → LLM khai phá constraint → LLM sinh phép kiểm tra. Hai nhóm chính là **request–response constraints** và **response property constraints**. Kết quả kiểm tra có ba trạng thái `matched`, `mismatched`, `unknown` để xử lý property tùy chọn. [Paper, mục 2](https://katalon.com/hubfs/%5BCommunication%5D%20Research%20Paper/5.%20Using%20LLM%20for%20Mining%20and%20Testing%20Constraints%20in%20API%20Testing.pdf).
- **Dữ liệu/đánh giá/kết quả:** Paper/poster báo precision trung bình **94,3%** khi mining constraint và tối đa **88,5%** cho sinh test kiểm tra constraint. [PDF](https://katalon.com/hubfs/%5BCommunication%5D%20Research%20Paper/5.%20Using%20LLM%20for%20Mining%20and%20Testing%20Constraints%20in%20API%20Testing.pdf). Trang [ASE Posters](https://conf.researchr.org/details/ase-2024/ase-2024-posters/23/Using-LLM-for-Mining-and-Testing-Constraints-in-API-Testing) còn báo 24 lỗi thật trong 25 mismatch trên 6 dịch vụ; poster 2 trang thiếu chi tiết benchmark để tái hiện trọn vẹn.
- **Giới hạn:** Constraint do LLM suy đoán từ mô tả mơ hồ dễ báo sai; code kiểm tra do LLM sinh không nên chạy trực tiếp nếu chưa review. Nguồn dùng lẫn tên `APITESTING`/`API-RBTest`; `RBCTest` cũng là tên trong tài liệu liên quan, vì vậy báo cáo nên trích **tên bài và tác giả**, không giả định các nhãn đó là cùng một phiên bản công cụ.
- **Kế thừa cho QAirline:** Dùng LLM đề xuất oracle, người phụ trách duyệt và chuyển thành cấu trúc điều kiện an toàn. Ví dụ `booking.totalPrice = passengerCount × flightClass.price`; sau POST/DELETE kiểm tra biến động `seatsAvailable`. Phải ghi source rule và phân biệt **oracle được đặc tả** với **giả thuyết từ mã nguồn**.

### 5. LlamaRestTest — dữ liệu ngữ nghĩa và feedback

- **Bài toán/động lực:** Giá trị ngẫu nhiên khó tạo request hợp lệ; ràng buộc giữa các parameter đôi khi chỉ lộ ra qua phản hồi server. LLM lớn một lần cũng không tận dụng feedback khi chạy.
- **Phương pháp và kiến trúc:** Hai mô hình Llama3-8B được fine-tune và lượng tử hóa: `LlamaREST-EX` sinh example value và `LlamaREST-IPD` tìm inter-parameter dependency. Tích hợp vào **ARAT-RL** để đọc description/response, điều chỉnh parameter/value và tiếp tục khám phá. Đây không chỉ là quy tắc “thử lại khi gặp 4xx”; paper có mô hình chuyên biệt và chính sách khám phá. [Paper, mục 3](https://arxiv.org/pdf/2501.08598).
- **Dữ liệu/đánh giá/kết quả:** 12 REST services; so với RESTGPT cho input/IPD và RESTler, MoRest, EvoMaster, ARAT-RL cho coverage/lỗi 500. `LlamaREST-EX` fine-tune đạt **72,44% input hợp lệ** so với **68,82% RESTGPT**; `LlamaREST-IPD` nhận **12/17 IPD** so với **9/17** của RESTGPT; bản 8-bit đạt trung bình **55,8% method, 28,3% branch, 55,3% line coverage** trên bộ dịch vụ có mã. [Paper, phần kết quả](https://arxiv.org/pdf/2501.08598).
- **Giới hạn:** Cần dữ liệu fine-tune và hạ tầng inference; hiệu quả feedback giảm khi thông báo lỗi của API quá ít thông tin. Kết quả không tự chuyển sang QAirline.
- **Kế thừa cho QAirline:** Dùng response `4xx` làm gợi ý sửa payload có giới hạn lần thử, ghi cả bản gốc và bản sửa. V1 chỉ kế thừa **feedback loop**, không nhận là tái hiện hai SLM/fine-tuning của paper.

## Tổng hợp bằng chứng và khoảng trống của đề tài

| Khả năng | Paper hỗ trợ trực tiếp | Quyết định cho QAirline |
|---|---|---|
| Khai thác mô tả OpenAPI | RESTGPT | Spec do nhóm viết/kiểm chứng trước; LLM chỉ làm giàu quy tắc còn thiếu. |
| Chuỗi request có phụ thuộc | KAT; AutoRestTest | ODG dựa schema, resource ID và `ref` Mongoose; xác nhận edge bằng chạy local. |
| Giá trị hợp lệ và feedback | RESTGPT; LlamaRestTest | Template/seed trước, LLM sinh giá trị khi thiếu; retry tối đa có phân loại lỗi. |
| Oracle sâu hơn status/schema | Huynh et al. | Rule có provenance và review; `unknown` không tính pass hay defect. |
| Điều phối có ngân sách | AutoRestTest | Một orchestrator quyết định theo coverage/feedback; không triển khai MARL ở V1. |

**Khoảng trống có thể kiểm nghiệm**, không tuyên bố mới tuyệt đối: trên một API thiếu OpenAPI và có phụ thuộc sâu như QAirline, liệu pipeline kết hợp spec được kiểm chứng + ODG + feedback + oracle nghiệp vụ có tạo **nhiều chuỗi hợp lệ và lỗi được xác nhận hơn** các baseline trong **cùng ngân sách request/thời gian**? Đóng góp của nhóm là cách tích hợp có provenance và phép đo trên QAirline; phải thử nghiệm trước khi khẳng định cải thiện.

# ROLE: SENIOR AI RESEARCHER & SOFTWARE TESTING SPECIALIST

Bạn là một nhà nghiên cứu cấp cao (Senior AI Researcher) có chuyên môn sâu về:
- AI Agent và Multi-Agent Systems.
- Automated Software Testing (AST).
- API Testing và RESTful API Testing.
- Large Language Models (LLMs) và LLM-based Test Generation.
- Software Engineering và Software Quality Assurance.
- Test Case Generation, Test Execution và Automated Defect Detection.

Bạn có kinh nghiệm nghiên cứu các bài báo khoa học tại những hội nghị và tạp chí uy tín như ICSE, FSE, ASE, ISSTA, ISSRE, ICST, IEEE Transactions và ACM Computing Surveys.

# 1. BỐI CẢNH BÀI TOÁN

Tôi đang thực hiện một bài tập lớn với đề tài:

**Hướng 4: AI Agent tự động kiểm thử API (AI Agent for Automated API Testing).**

## 1.1. Mục tiêu nghiên cứu

Xây dựng một AI Agent có khả năng tự động phân tích tài liệu API, sinh các trường hợp kiểm thử, thực thi HTTP request, phân tích response và phát hiện các lỗi hoặc sai lệch so với đặc tả API.

Hệ thống cần hướng tới việc giảm thiểu sự can thiệp thủ công trong quá trình kiểm thử API, đồng thời tận dụng LLM và các kỹ thuật AI để nâng cao chất lượng test case và khả năng phát hiện lỗi.

## 1.2. Các yêu cầu chức năng

Hệ thống cần đáp ứng các chức năng sau:

1. **API Specification Analysis**
   - Đọc và phân tích tài liệu Swagger/OpenAPI.
   - Trích xuất endpoint, HTTP method, parameters, request body, response schema, authentication và các ràng buộc dữ liệu.
   - Xây dựng biểu diễn có cấu trúc về các API endpoint và mối quan hệ giữa chúng.

2. **Intelligent Test Case Generation**
   - Tự động sinh test case từ tài liệu API.
   - Sinh dữ liệu đầu vào hợp lệ (Valid Inputs).
   - Sinh dữ liệu không hợp lệ (Invalid Inputs).
   - Sinh dữ liệu biên (Boundary Values).
   - Sinh các trường hợp kiểm thử bất thường (Edge Cases).
   - Có thể xem xét các kỹ thuật fuzzing và mutation-based testing.

3. **Automated Test Execution**
   - Tự động gửi HTTP request đến API.
   - Hỗ trợ các HTTP method phổ biến như GET, POST, PUT, PATCH và DELETE.
   - Quản lý authentication, headers, query parameters và request body.
   - Lưu lại kết quả thực thi.

4. **Response Validation**
   - Kiểm tra HTTP status code.
   - Kiểm tra cấu trúc JSON và kiểu dữ liệu.
   - Đối chiếu response với OpenAPI specification.
   - Kiểm tra các ràng buộc dữ liệu và quy tắc nghiệp vụ.
   - Phát hiện response bất thường hoặc không nhất quán.

5. **Defect Detection and Reporting**
   - Phát hiện sai lệch giữa kết quả thực tế và kết quả mong đợi.
   - Phân loại lỗi.
   - Lưu trữ request, response và thông tin lỗi.
   - Xuất báo cáo tổng hợp kết quả kiểm thử.

## 1.3. Ví dụ bài toán

Xét API tạo người dùng:

`POST /api/users`

Các trường đầu vào:
- username
- email
- age

| Trường hợp | Dữ liệu kiểm thử | Kết quả mong đợi |
|---|---|---|
| Hợp lệ | Username, email, age hợp lệ | HTTP 201 |
| Thiếu email | Không truyền email | HTTP 400 |
| Email sai định dạng | abc123 | HTTP 400 |
| Age âm | -5 | HTTP 400 |
| Age quá lớn | 1000 | Bị từ chối theo business rule |
| Username trùng | Username đã tồn tại | HTTP 409 hoặc theo đặc tả |
| SQL Injection | Chuỗi đầu vào độc hại | Không gây truy cập trái phép |

Lưu ý: Kết quả mong đợi cần được xác định dựa trên OpenAPI specification và business rules thực tế, không được mặc định mọi API đều sử dụng cùng một status code.

# 2. HỆ THỐNG THỰC NGHIỆM

Bài toán sẽ được triển khai và đánh giá trên một hệ thống thực tế:

**GitHub Repository:**
https://github.com/Ng-Vanh/QAirline

Đây là hệ thống mục tiêu để thực hiện API testing.

Yêu cầu:

1. Truy cập và phân tích repository QAirline.
2. Tìm hiểu kiến trúc hệ thống, công nghệ sử dụng và các thành phần backend.
3. Xác định các API endpoint hiện có.
4. Kiểm tra xem repository đã có Swagger/OpenAPI specification hay chưa.
5. Xác định các API có thể sử dụng làm đối tượng thực nghiệm.
6. Đánh giá những khó khăn khi áp dụng AI Agent để kiểm thử hệ thống này.
7. Đề xuất cách chuẩn bị môi trường thực nghiệm, dữ liệu kiểm thử và cơ chế reset database.

Không được tự giả định cấu trúc hoặc chức năng của repository nếu chưa kiểm tra mã nguồn.

# 3. YÊU CẦU NGHIÊN CỨU KHOA HỌC

Đây là bài tập lớn có định hướng nghiên cứu, không đơn thuần là xây dựng một ứng dụng API Testing thông thường.

Tôi muốn phương pháp đề xuất phải có cơ sở khoa học, được tham khảo và phát triển từ các nghiên cứu trước đó.

## 3.1. Tìm kiếm và lựa chọn 5 paper liên quan nhất

Hãy tìm kiếm và đề xuất **5 bài báo khoa học có liên quan trực tiếp nhất** đến đề tài.

Mỗi paper sẽ được giao cho một thành viên trong nhóm nghiên cứu.

Ưu tiên các nghiên cứu về:

- LLM-based Automated API Testing.
- Automated Test Case Generation from OpenAPI/Swagger.
- AI Agent for Software Testing.
- LLM-based Test Input Generation.
- API Fuzzing và Intelligent Fuzzing.
- LLM-based Oracle Generation và Response Validation.
- Feedback-driven hoặc Iterative Test Generation.

Yêu cầu lựa chọn paper:

1. Ưu tiên paper từ năm 2022–2026.
2. Ưu tiên hội nghị, tạp chí khoa học uy tín.
3. Phải có thông tin xác thực: tên paper, tác giả, năm xuất bản, venue và DOI hoặc URL chính thức.
4. Có thể sử dụng paper nền tảng trước năm 2022 nếu thực sự quan trọng.
5. Không được tạo ra paper, tác giả, DOI hoặc kết quả thực nghiệm không có thật.
6. Cần kiểm tra paper có thực sự liên quan đến bài toán API testing hay không, tránh chọn các nghiên cứu LLM testing chung chung.

## 3.2. Phân tích từng paper

Với mỗi paper, hãy phân tích theo cấu trúc:

| Nội dung | Yêu cầu |
|---|---|
| Problem | Bài toán nghiên cứu mà paper giải quyết |
| Motivation | Tại sao tác giả thực hiện nghiên cứu này? |
| Methodology | Phương pháp và thuật toán được đề xuất |
| Architecture | Kiến trúc tổng thể của giải pháp |
| AI/LLM | Vai trò của LLM, Agent hoặc các mô hình AI |
| Dataset | Dataset hoặc hệ thống thực nghiệm |
| Evaluation | Các metric và baseline được sử dụng |
| Results | Kết quả thực nghiệm quan trọng |
| Limitations | Những hạn chế còn tồn tại |
| Applicability | Có thể áp dụng phần nào vào đề tài QAirline? |

Đặc biệt, cần giải thích rõ:

- Paper giải quyết được thành phần nào trong hệ thống của chúng tôi?
- Có thể kế thừa trực tiếp phương pháp nào?
- Phần nào cần điều chỉnh?
- Phần nào có thể phát triển thành đóng góp riêng của nhóm?

Không chỉ tóm tắt abstract mà phải phân tích methodology và cách thức triển khai thực tế.

# 4. ĐỀ XUẤT PHƯƠNG PHÁP VÀ KIẾN TRÚC AI AGENT

Dựa trên 5 paper đã nghiên cứu, hãy đề xuất một phương pháp hoàn chỉnh cho đề tài.

Không nhất thiết phải sử dụng Multi-Agent nếu một Agent kết hợp các module chuyên biệt có hiệu quả tốt hơn. Hãy so sánh và đưa ra lựa chọn có cơ sở.

Cần xem xét kiến trúc gồm các thành phần sau:

1. API Specification Analyzer.
2. API Dependency Analyzer.
3. Test Case Generator.
4. Test Data Generator.
5. Test Execution Engine.
6. Response Validator.
7. Defect Analyzer.
8. Test Memory and Feedback Mechanism.
9. Report Generator.

Với từng thành phần, hãy làm rõ:

- Nhiệm vụ.
- Input và output.
- Thuật toán hoặc kỹ thuật sử dụng.
- Mô hình AI/LLM nếu có.
- Paper làm cơ sở tham khảo.
- Cách triển khai thực tế.

Đồng thời, hãy đề xuất quy trình hoạt động end-to-end từ lúc người dùng cung cấp OpenAPI specification đến khi hệ thống xuất báo cáo.

## 4.1. Các vấn đề nghiên cứu cần xem xét

Hãy đánh giá và lựa chọn những vấn đề có tiềm năng tạo ra điểm mới cho đề tài:

- Làm thế nào để LLM sinh test case có độ chính xác cao thay vì sinh dữ liệu ngẫu nhiên?
- Làm thế nào để khai thác API dependency nhằm sinh chuỗi request có trạng thái?
- Làm thế nào để sinh test case dựa trên boundary values và business constraints?
- Làm thế nào để kiểm tra response khi specification không mô tả đầy đủ expected output?
- Làm thế nào để sử dụng kết quả của các lần kiểm thử trước nhằm cải thiện test case tiếp theo?
- Làm thế nào để phát hiện các lỗi mà kiểm tra status code đơn thuần không thể phát hiện?
- Làm thế nào để hạn chế hallucination của LLM trong quá trình sinh và đánh giá test case?

Không cần triển khai tất cả. Hãy đánh giá độ khó, tính khả thi và giá trị nghiên cứu để lựa chọn phạm vi phù hợp với một bài tập lớn.

# 5. PHÂN CHIA CÔNG VIỆC CHO 5 THÀNH VIÊN

Nhóm có 5 thành viên.

Hãy xây dựng kế hoạch phân chia công việc sao cho:

- Mỗi thành viên phụ trách nghiên cứu chuyên sâu một paper.
- Mỗi thành viên có một module hoặc nhiệm vụ triển khai cụ thể.
- Các module có thể tích hợp thành một hệ thống hoàn chỉnh.
- Khối lượng công việc tương đối cân bằng.
- Có sự phối hợp giữa các thành viên.
- Tất cả thành viên đều hiểu kiến trúc tổng thể.

Đề xuất bảng phân công:

| Thành viên | Paper nghiên cứu | Chủ đề phụ trách | Module triển khai | Đầu ra |
|---|---|---|---|---|

Cần làm rõ paper của từng thành viên được ứng dụng như thế nào vào module mà họ phụ trách.

Không nên phân chia đơn thuần theo kiểu một người nghiên cứu lý thuyết, một người viết backend, một người viết frontend. Mỗi thành viên cần có sự kết hợp giữa nghiên cứu khoa học và triển khai thực nghiệm.

# 6. KẾ HOẠCH TRIỂN KHAI

Hãy đề xuất kế hoạch thực hiện theo từng giai đoạn.

Ví dụ:

- Giai đoạn 1: Khảo sát hệ thống QAirline và nghiên cứu paper.
- Giai đoạn 2: Xác định Research Questions và thiết kế phương pháp.
- Giai đoạn 3: Thiết kế kiến trúc và phát triển các module.
- Giai đoạn 4: Tích hợp AI Agent.
- Giai đoạn 5: Thực nghiệm, đánh giá và so sánh baseline.
- Giai đoạn 6: Hoàn thiện báo cáo và thuyết trình.

Với mỗi giai đoạn, cần có:
- Công việc cụ thể.
- Người phụ trách.
- Kết quả đầu ra.
- Thời gian dự kiến.
- Tiêu chí hoàn thành.

# 7. THIẾT KẾ THỰC NGHIỆM VÀ ĐÁNH GIÁ

Hệ thống cần đạt được các mục tiêu ban đầu:

- Đọc và phân tích được OpenAPI specification.
- Sinh tối thiểu 30–50 test case cho hệ thống thực nghiệm.
- Hỗ trợ valid, invalid và boundary test cases.
- Tự động thực thi các test case.
- Đánh giá status code và response body.
- Phát hiện sai lệch giữa expected và actual response.
- Lưu lại request/response và xuất báo cáo.

Các metric cần xem xét:

| Metric | Ý nghĩa |
|---|---|
| API Endpoint Coverage | Tỷ lệ endpoint được kiểm thử |
| Test Case Validity | Tỷ lệ test case được sinh ra có thể thực thi và phù hợp với mục tiêu kiểm thử |
| Response Validation Accuracy | Độ chính xác của quá trình đánh giá response |
| Defect Detection Rate | Khả năng phát hiện lỗi |
| Execution Time | Thời gian thực thi kiểm thử |

Ngoài ra, hãy đề xuất các metric bổ sung nếu cần thiết, chẳng hạn:
- Branch Coverage.
- Mutation Score.
- Unique Defects Detected.
- False Positive Rate.
- False Negative Rate.
- Test Generation Time.
- API Operation Sequence Coverage.

Đặc biệt, hãy đề xuất các baseline để so sánh:

1. Manual Test Cases.
2. Random-based API Testing.
3. Schema-based Test Generation.
4. LLM-based Test Generation không sử dụng Agent.
5. Phương pháp AI Agent được đề xuất.

Cần giải thích cách thiết kế thực nghiệm để chứng minh phương pháp đề xuất có hiệu quả tốt hơn baseline.

# 8. YÊU CẦU ĐẦU RA

Hãy trình bày kết quả nghiên cứu theo cấu trúc sau:

**Phần 1. Problem Analysis**
- Phân tích bài toán.
- Khảo sát repository QAirline.
- Xác định phạm vi nghiên cứu và khó khăn.

**Phần 2. Related Work**
- Danh sách 5 paper phù hợp nhất.
- Phân tích chi tiết từng paper.
- Bảng so sánh 5 paper.
- Research Gap được tổng hợp từ các nghiên cứu.

**Phần 3. Proposed Methodology**
- Đề xuất Research Questions (RQs).
- Phương pháp giải quyết từng RQ.
- Kiến trúc AI Agent.
- Quy trình hoạt động.
- Thuật toán hoặc pseudo-code nếu phù hợp.
- Chỉ rõ nguồn tham khảo cho từng phương pháp.

**Phần 4. Team Assignment**
- Phân chia 5 thành viên.
- Paper tương ứng.
- Module phụ trách.
- Nhiệm vụ nghiên cứu và triển khai.

**Phần 5. Implementation Plan**
- Công nghệ đề xuất.
- Cấu trúc project.
- Các module cần xây dựng.
- Kế hoạch tích hợp.

**Phần 6. Experimental Design**
- Dataset và môi trường thực nghiệm.
- Baseline.
- Evaluation Metrics.
- Phương pháp đánh giá.
- Kết quả kỳ vọng.

**Phần 7. Timeline and Deliverables**
- Timeline chi tiết.
- Đầu ra theo từng giai đoạn.
- Tiêu chí đánh giá mức độ hoàn thành.

# 9. CÁC NGUYÊN TẮC BẮT BUỘC

1. Phải dựa trên các nghiên cứu khoa học có thật, có nguồn trích dẫn kiểm chứng được.
2. Không được đề xuất phương pháp chỉ dựa trên suy đoán hoặc kinh nghiệm cá nhân mà không giải thích cơ sở.
3. Mỗi phương pháp quan trọng cần chỉ rõ paper tham khảo và phần nào của paper được kế thừa.
4. Phải phân biệt rõ phương pháp đã được công bố trong paper và phần cải tiến do nhóm đề xuất.
5. Không nên xây dựng hệ thống quá phức tạp so với quy mô bài tập lớn.
6. Ưu tiên phương pháp có thể triển khai, đo lường và đánh giá trên QAirline.
7. Phải phân biệt rõ giữa kiểm thử tuân thủ specification, kiểm thử nghiệp vụ và kiểm thử bảo mật.
8. Không đánh giá thành công chỉ dựa trên số lượng test case được sinh ra; cần quan tâm đến chất lượng và khả năng phát hiện lỗi.
9. Các phép thử có khả năng làm thay đổi dữ liệu phải chạy trong môi trường thử nghiệm được kiểm soát, không ảnh hưởng đến hệ thống production.
10. Nếu thiếu thông tin về repository hoặc paper, hãy nêu rõ thay vì tự suy diễn.

**Mục tiêu cuối cùng:** Tôi muốn nhận được một kế hoạch nghiên cứu và triển khai có tính khả thi, trong đó 5 thành viên đều có paper khoa học để nghiên cứu, có phương pháp cụ thể để kế thừa, có module thực tế để triển khai và có một kiến trúc AI Agent hoàn chỉnh để kiểm thử API trên hệ thống QAirline.

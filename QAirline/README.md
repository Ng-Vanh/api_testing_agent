# Chạy QAirline trên máy cá nhân (Linux / Windows)

Tài liệu này hướng dẫn chạy **MongoDB local + backend Express + frontend React** từ mã nguồn trong thư mục `QAirline/`. Các lệnh được đọc từ `backend/package.json`, `frontend/package.json` và cấu hình hiện tại; chưa có bài kiểm tra chạy end-to-end được thực hiện cho cả Linux lẫn Windows.

## 1. Cần cài gì?

- **Node.js 22.x LTS** (kèm npm). Lockfile frontend có `react-router-dom` yêu cầu Node >= 20; dùng cùng một nhánh Node cho cả nhóm. Xem [trang tải Node.js](https://nodejs.org/en/download) và [lịch hỗ trợ](https://nodejs.org/en/about/previous-releases).
- **Docker** để chạy MongoDB: [Docker Engine cho Linux](https://docs.docker.com/engine/install/) hoặc [Docker Desktop cho Windows](https://docs.docker.com/desktop/setup/install/windows-install/) với WSL 2/Linux containers. Có thể dùng MongoDB cài trực tiếp nếu đã có service trên `localhost:27017`.
- Trình duyệt để mở frontend. Postman/Insomnia chỉ cần nếu muốn tạo dữ liệu mẫu bằng tay.

Kiểm tra công cụ đã sẵn sàng trong Terminal (Linux) hoặc PowerShell (Windows):

```text
node --version
npm --version
docker --version
```

Không cần chạy `npm install` ở thư mục `QAirline/` gốc: backend và frontend có `package.json`/`package-lock.json` riêng.

## 2. Khởi động MongoDB local

Chạy trong Terminal hoặc PowerShell:

```text
docker run -d --name qairline-mongo -p 127.0.0.1:27017:27017 -v qairline-mongo-data:/data/db mongo:7
```

Kiểm tra `docker ps` thấy `qairline-mongo` đang chạy. Lệnh này tạo **volume để giữ dữ liệu giữa các lần chạy**. Các lần sau chỉ cần `docker start qairline-mongo`; dừng bằng `docker stop qairline-mongo`. Nếu cổng 27017 đang được MongoDB khác dùng, hãy dừng service đó hoặc đổi cổng và đổi `MONGO_URI` tương ứng.

## 3. Chạy backend

Mở terminal thứ nhất tại thư mục gốc repo:

```text
cd QAirline/backend
npm ci
npm run dev
```

Trong PowerShell, có thể dùng `cd .\QAirline\backend`. `npm ci` cài theo lockfile; chỉ cần chạy lại khi dependency thay đổi. `npm run dev` dùng `nodemon`; có thể dùng `npm start` để chạy bằng `node`.

Backend đọc `MONGO_URI` từ biến môi trường hoặc file `QAirline/backend/.env`. **Nếu không đặt `MONGO_URI`**, mặc định là `mongodb://localhost:27017/qairline`; cổng HTTP mặc định là **5000** ([cấu hình DB](backend/config/db.js), [server](backend/server.js)). Nếu muốn ghi rõ cấu hình, tạo `QAirline/backend/.env`:

```dotenv
MONGO_URI=mongodb://127.0.0.1:27017/qairline
PORT=5000
```

`.env` đã nằm trong `.gitignore`. Biến môi trường `MONGO_URI` đã đặt ở hệ điều hành sẽ được ưu tiên hơn giá trị trong `.env`; hãy kiểm tra để bảo đảm backend không kết nối nhầm DB khác. Chờ log `Successfully started backend` rồi mở `http://localhost:5000/api/airports`: với DB rỗng, API dự kiến trả `{"airports":[]}`. Log `Connected to MongoDB Atlas via shared config` trong code là **chuỗi in cố định**, không chứng minh đang dùng Atlas.

Swagger UI ở `http://localhost:5000/api-docs/`; file OpenAPI JSON ở `http://localhost:5000/api-docs.json`. Đặc tả nguồn nằm tại [`specs/qairline_openapi.json`](specs/qairline_openapi.json), mô tả 48 operation. Nếu vừa kéo thay đổi này về và trang Swagger vẫn trống, dừng backend đang chạy rồi chạy lại `npm run dev`, sau đó tải lại trang.

## 4. Chạy frontend và trỏ về backend local

Mở terminal thứ hai tại thư mục gốc repo:

```text
cd QAirline/frontend
npm ci
npm start
```

Trong PowerShell, có thể dùng `cd .\QAirline\frontend`. Frontend thường mở tại `http://localhost:3000`.

**Cần đổi API URL trước khi dùng giao diện local.** [`frontend/src/Config.js`](frontend/src/Config.js) hiện trỏ thẳng tới Render; trường `proxy` trong `frontend/package.json` không có tác dụng với các request dùng URL tuyệt đối này. Sửa file thành:

```js
const Config = {
  apiBaseUrl: 'http://localhost:5000',
};

export default Config;
```

Sau khi đổi, frontend sẽ gửi request tới backend local. Không dùng URL Render để thử các thao tác tạo, sửa, xóa hoặc chạy bộ kiểm thử API. Nếu cần dùng hai môi trường thường xuyên, nên thay giá trị hardcode bằng cấu hình môi trường frontend trong một thay đổi mã riêng.

## 5. Lần đầu chạy có tự seed database không?

**Không tự động.** Backend chỉ kết nối MongoDB và chạy scheduler; nó không tạo dữ liệu mẫu khi khởi động. Volume Docker mới có DB ứng dụng rỗng. Repo hiện có bộ seed riêng; chạy **một lần thủ công** sau khi đã cài dependency backend và khởi động MongoDB:

```bash
bash QAirline/scripts/import-seed.sh
```

Lệnh trên chạy từ **thư mục gốc repo** trong Linux Terminal, Windows Git Bash hoặc WSL. Script sẽ hỏi mật khẩu cho các tài khoản demo; không lưu mật khẩu vào repo. Nếu đang ở thư mục `QAirline/`, dùng `bash scripts/import-seed.sh`. Tài khoản có tên `qa_seed_admin`, `qa_seed_user_01`, `qa_seed_user_02`, `qa_seed_user_03` và cùng mật khẩu đã nhập. Nếu chạy không tương tác (CI), đặt biến môi trường `QAIRLINE_SEED_PASSWORD` trước khi gọi script; đừng ghi mật khẩu vào file được commit.

Bộ dữ liệu tại [`seed/data.json`](seed/data.json) gồm **8 sân bay, 4 máy bay, 24 chuyến bay, 4 tài khoản, 8 hành khách và 6 booking**. Tên/mã sân bay đối chiếu với [Vietnam Airlines Airport Maps](https://airportmap.vietnamairlines.com/); các mã máy bay, chuyến bay, giá và con người là dữ liệu mô phỏng. Ngày bay được đặt cách thời điểm nhập 2, 4 và 7 ngày. Chạy lại lệnh không tạo bản ghi trùng và không đổi dữ liệu seed đã có; muốn có ngày bay mới cần dùng DB local mới hoặc viết quy trình reset. Nếu DB đã có cùng mã sân bay/tài nguyên với ID khác, script sẽ dừng và yêu cầu DB local rỗng để tránh ghi đè.

Bộ seed tập trung vào 6 nhóm API nghiệp vụ của đề tài; **chưa nhập Content/ảnh GridFS**, nên mục tin tức trên trang chủ vẫn có thể trống.

Script chỉ cho phép URI `mongodb://localhost[:port]/qairline` hoặc `mongodb://127.0.0.1[:port]/qairline`. Backend vẫn phải trỏ đúng **cùng DB local**. Không dùng bộ tài khoản demo trên môi trường công khai.

### Nhập dữ liệu bằng tay (tùy chọn)

Chỉ dùng cách này nếu **không** chạy seed script trên cùng database; hai cách cùng tạo các mã sân bay mẫu và sẽ va chạm dữ liệu.

Để có dữ liệu dùng thử, tạo theo thứ tự bằng Postman/Insomnia hoặc API client tương đương (chọn `Content-Type: application/json`). Đây là **ví dụ nhập tay**, không phải seed tự động. Sao chép `_id` từ response của bước trước sang bước sau:

| Thứ tự | Request | JSON body mẫu |
|---|---|---|
| 1 | `POST http://localhost:5000/api/airports` | `{"code":"SGN","name":"Tan Son Nhat","city":"Ho Chi Minh City"}` |
| 2 | `POST http://localhost:5000/api/airports` | `{"code":"HAN","name":"Noi Bai","city":"Ha Noi"}` |
| 3 | `POST http://localhost:5000/api/aircrafts` | `{"code":"VN-A001","manufacturer":"Airbus","model":"A320","seats":180,"type":"Narrow Body","range":6100,"cruiseSpeed":830,"engineType":"Turbofan","inService":true,"lastMaintenance":"2034-01-01","nextMaintenance":"2034-07-01"}` |
| 4 | `POST http://localhost:5000/api/flights` | Xem mẫu dưới đây; thay ba ID thật từ bước 1–3. |

```json
{
  "flightCode": "QA001",
  "departureAirport": "<SGN_AIRPORT_ID>",
  "arrivalAirport": "<HAN_AIRPORT_ID>",
  "departureTime": "2035-01-15T02:00:00.000Z",
  "arrivalTime": "2035-01-15T04:00:00.000Z",
  "flightClass": {
    "economy": { "price": 1000000, "seatsAvailable": 100 },
    "business": { "price": 2500000, "seatsAvailable": 20 }
  },
  "aircraft": "<AIRCRAFT_ID>",
  "flightStatus": "Scheduled"
}
```

Muốn thử luồng đặt vé, tạo thêm `POST /api/users` với `name`, `username`, `password`; `POST /api/passengers` với `name`, `email`; sau đó gọi `POST /api/bookings` với `userID`, `flightID`, `flightClass` (`economy` hoặc `business`), `passengerCount` và `passengerIDs` có đúng số phần tử. Dữ liệu mẫu trên dùng ngày năm 2035 để scheduler không đánh dấu chuyến bay đã hạ cánh trong thời gian gần; khi chạy sau ngày đó, chọn ngày tương lai mới.

Với thực nghiệm AI Agent, bộ seed hiện tại cung cấp dữ liệu ban đầu nhưng **chưa có lệnh reset DB**. Cần bổ sung cơ chế reset trước mỗi lần chạy baseline để các phương pháp có cùng dữ liệu xuất phát.

## 6. Kiểm tra nhanh và vấn đề thường gặp

| Dấu hiệu | Cần kiểm tra |
|---|---|
| Backend báo `MongoDB connection error` | Container đang chạy chưa, cổng 27017 có đúng không, `MONGO_URI` có trỏ local không. |
| Frontend mở được nhưng không có chuyến bay | DB rỗng hoặc ngày tìm kiếm không khớp `departureTime`; tạo dữ liệu mẫu ở mục 5. |
| Frontend vẫn gọi Render | `frontend/src/Config.js` chưa đổi hoặc dev server chưa nạp lại cấu hình. |
| Port 3000/5000 đã dùng | Dừng tiến trình cũ hoặc đổi `PORT`; nếu đổi cổng backend, cập nhật `Config.js`. |
| `/api-docs/` mở nhưng không thấy endpoint | Khởi động lại backend sau khi cập nhật mã; kiểm tra `http://localhost:5000/api-docs.json` có trường `paths`. |

**Giới hạn hiện tại:** chưa có Docker Compose, reset DB tự động hay bài kiểm tra xuyên suốt trên Linux/Windows. Importer đã được chạy thử với MongoDB tạm trên Linux; frontend chưa được xác nhận end-to-end. Khi triển khai công cụ kiểm thử, hãy chạy nó với backend và MongoDB local đã cô lập.

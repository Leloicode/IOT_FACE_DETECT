# Hướng Dẫn Cài Đặt và Sử Dụng Dự Án (Face Recognition + MQTT + ESP32)

Dự án này là một hệ thống điểm danh tự động nhận diện khuôn mặt kết hợp cảnh báo IoT. Dưới đây là hướng dẫn toàn tập từ A-Z để bạn hoặc team của bạn có thể chạy dự án thành công.

---

## PHẦN 1: Chuẩn bị Môi trường Máy Tính (Backend)

Phần nhận diện khuôn mặt yêu cầu thư viện `dlib`. Để cài đặt dễ dàng nhất trên Windows mà không bị lỗi, **bắt buộc bạn phải sử dụng Python 3.11**.

1. **Gỡ cài đặt Python cũ (Nếu có)**: Nếu máy bạn đang có Python 3.12 hoặc 3.13, hệ thống sẽ không tự động build được `dlib`. Bạn nên tải đúng bản 3.11.
2. **Tải Python 3.11**: [Truy cập link tải Python 3.11.9 (64-bit)](https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe).
3. **Cài đặt Python**:
   > [!IMPORTANT]
   > Khi cửa sổ cài đặt hiện lên, **BẮT BUỘC** phải tích vào ô vuông **"Add python.exe to PATH"** (nằm ở dưới cùng) trước khi bấm nút "Install Now".
4. **Cắm Webcam**: Đảm bảo máy tính đã được kết nối với Webcam (nếu dùng Laptop thì đã có sẵn).

---

## PHẦN 2: Khởi động Backend (Xử lý AI)

Khi máy tính đã có Python 3.11, việc còn lại là tự động hoàn toàn:

1. Vào thư mục gốc của dự án.
2. Bấm đúp (Double-click) vào file **`start_backend.bat`**.
3. Lần chạy đầu tiên: 
   - Script sẽ tự động nhận diện Python, tạo môi trường ảo (venv) để không làm rác máy tính.
   - Nó sẽ tự động tải các thư viện AI (OpenCV, face_recognition, flask...). Quá trình này mất khoảng 2-5 phút tuỳ tốc độ mạng.
4. Khi cửa sổ Terminal (màu đen) hiện lên dòng chữ: `[INFO] Webserver backend dang chay tai http://localhost:5000`, tức là AI đã sẵn sàng hoạt động ngầm!
   > [!TIP]
   > Hãy giữ cửa sổ màu đen này mở trong suốt quá trình sử dụng hệ thống. Nếu muốn tắt AI, hãy chọn cửa sổ đó và bấm tổ hợp phím `Ctrl + C`.

---

## PHẦN 3: Sử dụng Web Dashboard (Giao diện điều khiển)

Giao diện Web không cần cài đặt, bạn chỉ cần mở file HTML lên:

1. Vào thư mục `web_dashboard`.
2. Mở file **`index.html`** bằng bất kỳ trình duyệt nào (Chrome, Edge, Cốc Cốc...).
3. Chọn tab **Cấu Hình (Settings)** (biểu tượng bánh răng).
4. Tại ô **Backend URL**, bạn nhập vào: `http://localhost:5000`
5. Bấm **Lưu & Tải**. Lúc này góc trên bên phải màn hình sẽ báo xanh **"Backend online"**.
6. Trải nghiệm:
   - **Đăng Ký Nhân Viên**: Nhập Tên và MSSV, đứng trước Webcam, bấm đăng ký để hệ thống tự quét và học khuôn mặt mới ngay trên web.
   - **Camera**: Bật để xem trực tiếp luồng video AI đang xử lý (bạn có thể bấm nút Start/Stop AI tại đây).
   - **Bảng điều khiển**: Xem realtime khi có người đi qua camera (kể cả trên điện thoại nếu bạn host file HTML này lên Vercel).

---

## PHẦN 4: Nạp Code ESP32 (Thiết bị IoT)

Đây là phần cứng, được dùng để hiển thị chữ (LCD) và phát loa cảnh báo (Buzzer) khi nhận diện thấy người lạ hoặc người quen.

1. **Cài đặt Arduino IDE** và thêm gói hỗ trợ ESP32.
2. **Cài đặt thư viện**: Vào mục **Library Manager** của Arduino IDE, gõ và cài đặt 3 thư viện sau:
   - `PubSubClient` (tác giả Nick O'Leary)
   - `LiquidCrystal I2C` (tác giả Frank de Brabander)
   - `ArduinoJson` (tác giả Benoit Blanchon)
3. **Cấu hình mạng WiFi**:
   Mở file `esp32_firmware/esp32_firmware.ino`. Tìm dòng:
   ```cpp
   const char* ssid = "TEN_WIFI_CUA_BAN";
   const char* password = "MAT_KHAU_WIFI";
   ```
   Thay bằng tên và mật khẩu WiFi tại nơi bạn đang chạy dự án (phải có internet để kết nối lên MQTT).
4. **Nạp Code**: Chọn cổng COM của ESP32 và bấm Upload.
5. **Cách hoạt động**:
   - ESP32 sẽ tự động kết nối mạng và chờ lệnh từ AI gửi tới qua MQTT (`broker.emqx.io`).
   - Khi có người được nhận diện, màn hình LCD sẽ in tên người đó.
   - Khi có người lạ mặt, Còi (Buzzer) sẽ kêu tít tít báo động. Bạn có thể bấm nút "Tắt còi báo động" ngay trên Web Dashboard để dập tiếng còi từ xa.

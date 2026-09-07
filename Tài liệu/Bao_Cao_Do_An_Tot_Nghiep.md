# BÁO CÁO ĐỒ ÁN TỐT NGHIỆP

## TÊN ĐỀ TÀI: Xây Dựng Hệ Thống Điểm Danh Tự Động Nhận Diện Khuôn Mặt Kết Hợp Cảnh Báo Bằng IoT

---

## LỜI CẢM ƠN
Trong quá trình thực hiện đồ án tốt nghiệp, em đã nhận được rất nhiều sự giúp đỡ, chỉ bảo tận tình từ các thầy cô, gia đình và bạn bè. Em xin gửi lời cảm ơn sâu sắc đến Giảng viên hướng dẫn đã trực tiếp định hướng, cung cấp cho em những kiến thức quý báu và giải đáp những vướng mắc trong suốt thời gian em thực hiện đề tài này.
Em cũng xin gửi lời cảm ơn đến các thầy cô trong Khoa Công Nghệ Thông Tin đã truyền đạt cho em những nền tảng kiến thức vững chắc trong suốt những năm học qua, tạo tiền đề để em có thể hoàn thành tốt đồ án này.

---

## TÓM TẮT ĐỒ ÁN
Đồ án "Xây Dựng Hệ Thống Điểm Danh Tự Động Nhận Diện Khuôn Mặt Kết Hợp Cảnh Báo Bằng IoT" tập trung vào việc nghiên cứu và ứng dụng trí tuệ nhân tạo (Computer Vision) kết hợp với công nghệ Internet vạn vật (IoT) để giải quyết bài toán quản lý nhân sự, điểm danh tự động. Hệ thống bao gồm ba thành phần chính: (1) Máy chủ Backend tích hợp AI xử lý luồng video trực tiếp để nhận diện khuôn mặt; (2) Trạm phần cứng IoT (ESP32) thực hiện việc cảnh báo bằng âm thanh, ánh sáng và hiển thị thông tin lên màn hình LCD; (3) Giao diện quản trị Web Dashboard giúp người quản lý dễ dàng giám sát, thêm mới nhân viên và điều khiển thiết bị từ xa. Hệ thống sử dụng giao thức MQTT để đảm bảo việc giao tiếp thời gian thực với độ trễ thấp giữa AI và phần cứng.

---

## CHƯƠNG 1: TỔNG QUAN ĐỀ TÀI

### 1.1 Đặt vấn đề và lý do chọn đề tài
Trong thời đại công nghệ số hóa hiện nay, việc quản lý nhân sự và đảm bảo an ninh đang trở thành một nhu cầu thiết yếu đối với các doanh nghiệp, trường học và các cơ quan tổ chức. Phương pháp điểm danh truyền thống (bằng thẻ từ, vân tay hay chữ ký giấy) bộc lộ nhiều hạn chế như: nhân viên quên thẻ, gian lận quẹt thẻ hộ, tốc độ chậm gây ùn tắc giờ cao điểm, hoặc các vấn đề về vệ sinh, lây nhiễm chéo khi sử dụng chung máy chấm công vân tay. 

Sự phát triển mạnh mẽ của Trí tuệ nhân tạo (AI), đặc biệt là lĩnh vực Thị giác máy tính (Computer Vision), cùng với xu hướng Internet of Things (IoT) đã mở ra hướng đi mới. Hệ thống điểm danh bằng công nghệ nhận diện khuôn mặt kết hợp thiết bị IoT được sinh ra để giải quyết triệt để các vấn đề trên. Công nghệ này mang lại sự tiện lợi (không cần chạm), tự động hóa cao, tốc độ nhận diện nhanh và tăng cường mức độ bảo mật thông qua việc cảnh báo theo thời gian thực khi có người lạ xâm nhập. 

### 1.2 Mục tiêu nghiên cứu
- Nghiên cứu và áp dụng các thuật toán Deep Learning vào việc nhận diện khuôn mặt người dùng theo thời gian thực với độ chính xác cao.
- Xây dựng mạng lưới IoT hoàn chỉnh sử dụng vi điều khiển ESP32, có khả năng tương tác hai chiều với máy chủ điều khiển thông qua môi trường Internet.
- Phát triển phần mềm quản lý trên nền tảng Web (Web Dashboard) cung cấp giao diện trực quan giúp người dùng cuối dễ dàng vận hành, đăng ký nhân viên mới qua Camera và theo dõi các sự kiện vào/ra.

### 1.3 Đối tượng và phạm vi nghiên cứu
- **Đối tượng:** Cán bộ, nhân viên văn phòng, hoặc sinh viên được cấp quyền ra vào hệ thống. Các đối tượng chưa được đăng ký sẽ bị hệ thống phân loại là "Người lạ".
- **Phạm vi nghiên cứu:** Ứng dụng mô hình trích xuất đặc trưng khuôn mặt HOG/CNN thông qua thư viện `dlib` và `face_recognition` bằng ngôn ngữ Python. Sử dụng mạch xử lý trung tâm ESP32 tích hợp WiFi làm thiết bị trạm (Node IoT). Giao tiếp dữ liệu qua giao thức MQTT.

### 1.4 Phương pháp nghiên cứu
- **Nghiên cứu tài liệu:** Tìm hiểu lý thuyết về Computer Vision, các mô hình học máy, cách thức hoạt động của MQTT và lập trình nhúng ESP32.
- **Thực nghiệm:** Xây dựng mô hình thực tế, viết mã nguồn cho Backend, Frontend và Firmware. Tiến hành lắp ráp các linh kiện điện tử.
- **Đánh giá và tối ưu:** Chạy thử nghiệm hệ thống trong các điều kiện môi trường ánh sáng khác nhau, ghi nhận kết quả độ chính xác, độ trễ và tiến hành tối ưu hóa luồng xử lý.

---

## CHƯƠNG 2: CƠ SỞ LÝ THUYẾT VÀ CÔNG NGHỆ ÁP DỤNG

### 2.1 Tổng quan về Trí tuệ nhân tạo và Thị giác máy tính
Trí tuệ nhân tạo (AI) đang định hình lại cách chúng ta tương tác với thế giới. Trong đó, Thị giác máy tính (Computer Vision) là một nhánh của AI, giúp máy tính có khả năng "nhìn" và phân tích hình ảnh, video giống như con người. Bài toán nhận diện khuôn mặt (Face Recognition) là một trong những ứng dụng phổ biến nhất của Computer Vision, bao gồm hai bước chính: Phát hiện khuôn mặt (Face Detection) - xác định vị trí khuôn mặt trong không gian ảnh, và Nhận diện (Recognition) - đối chiếu khuôn mặt đó với cơ sở dữ liệu để biết đó là ai.

### 2.2 Các mô hình nhận diện khuôn mặt
Có nhiều phương pháp nhận diện khuôn mặt từ truyền thống đến hiện đại:
- **Haar Cascade:** Nhanh nhưng độ chính xác thấp, dễ bị nhiễu bởi góc nghiêng và ánh sáng.
- **HOG (Histogram of Oriented Gradients) kết hợp SVM:** Cung cấp tốc độ xử lý tốt trên CPU và độ chính xác khá cao, rất phù hợp cho các bài toán thời gian thực.
- **CNN (Convolutional Neural Networks):** Mạng nơ-ron tích chập mang lại độ chính xác cực cao nhưng đòi hỏi phần cứng (GPU) mạnh.
Đồ án này lựa chọn sử dụng thư viện `face_recognition` dựa trên `dlib`, sử dụng mô hình HOG để dò tìm khuôn mặt và ResNet để mã hóa (encode) khuôn mặt thành 128 điểm đặc trưng (128-d vector). Phương pháp này cân bằng hoàn hảo giữa tốc độ (đáp ứng Real-time) và độ chính xác (99.38% trên tập dữ liệu Labeled Faces in the Wild).

### 2.3 Internet of Things (IoT) và Giao thức MQTT
IoT là mạng lưới các vật thể vật lý được nhúng các cảm biến, phần mềm để kết nối và trao đổi dữ liệu với các thiết bị khác trên Internet. Để các thiết bị IoT giao tiếp hiệu quả, giao thức **MQTT (Message Queuing Telemetry Transport)** được sử dụng rộng rãi nhờ ưu điểm: nhẹ, tiêu tốn ít băng thông, hỗ trợ chất lượng dịch vụ (QoS) và mô hình Publish/Subscribe (Xuất bản / Đăng ký). 
Hệ thống sử dụng MQTT Broker đám mây (EMQX) để trung chuyển thông điệp giữa máy chủ AI (Publisher) và vi điều khiển ESP32 (Subscriber).

### 2.4 Vi điều khiển ESP32
ESP32 là một hệ thống trên một vi mạch (SoC) giá rẻ, tiêu thụ năng lượng thấp của Espressif Systems. Điểm mạnh vượt trội của ESP32 là tích hợp sẵn Wi-Fi và Bluetooth chuẩn kép, sở hữu bộ xử lý lõi kép Tensilica Xtensa LX6 tốc độ lên đến 240 MHz. Điều này giúp ESP32 vượt trội hơn các dòng mạch như Arduino UNO hay ESP8266, hoàn toàn đủ sức xử lý các tác vụ mạng, nhận dữ liệu JSON phức tạp và điều khiển nhiều thiết bị ngoại vi cùng lúc.

---

## CHƯƠNG 3: PHÂN TÍCH VÀ THIẾT KẾ HỆ THỐNG

### 3.1 Thiết kế kiến trúc tổng thể hệ thống
Hệ thống được chia làm 3 thành phần chính hoạt động độc lập nhưng liên kết chặt chẽ với nhau:
1. **AI & Backend Server (Máy chủ xử lý):** Trái tim của hệ thống, chạy trên PC/Laptop. Sử dụng Python, OpenCV để capture khung hình, Flask để host Web API, và mô hình Deep Learning để định danh khuôn mặt.
2. **Web Dashboard (Giao diện người dùng):** Giao diện HMTL/CSS/JS chạy trên trình duyệt, kết nối với Backend. Cung cấp trang tổng quan xem log, luồng video mjpeg trực tiếp, và công cụ quản lý cơ sở dữ liệu khuôn mặt.
3. **IoT Node (Trạm thiết bị cứng):** Mạch ESP32 được lắp đặt tại khu vực ra vào (cửa/cổng). Đóng vai trò phản hồi vật lý: Còi hú khi có người lạ xâm nhập, đèn LED sáng và LCD hiển thị tên khi nhân viên điểm danh thành công.

### 3.2 Thiết kế phần mềm (Luồng xử lý AI)
- **Bước 1:** Đọc khung hình từ Camera (Webcam).
- **Bước 2:** Tiền xử lý, thu nhỏ khung hình (resize) để tăng tốc độ phân tích.
- **Bước 3:** Sử dụng thuật toán HOG dò tìm vị trí các khuôn mặt trong ảnh.
- **Bước 4:** Trích xuất vector 128 chiều cho từng khuôn mặt tìm được.
- **Bước 5:** Tính toán khoảng cách (Euclidean distance) giữa vector vừa tìm được với toàn bộ vector trong cơ sở dữ liệu. Nếu khoảng cách < 0.6 (ngưỡng dung sai), xác định danh tính người quen. Ngược lại, gán nhãn "Unknown" (Người lạ).
- **Bước 6:** Gửi bản tin định dạng JSON chứa tên người hoặc tín hiệu cảnh báo thông qua MQTT lên Broker.

### 3.3 Thiết kế phần cứng (IoT Node)
Trạm IoT được xây dựng dựa trên các linh kiện:
- **ESP32 DEVKIT V1:** Chịu trách nhiệm kết nối WiFi và MQTT.
- **Màn hình LCD 16x2 + I2C:** Hiển thị trạng thái hệ thống, Tên người được điểm danh, Cảnh báo xâm nhập. Giao tiếp qua chuẩn I2C (SDA: D21, SCL: D22) để tiết kiệm dây dẫn.
- **Còi báo (Buzzer):** Kích hoạt bằng mức logic HIGH (Chân D4). Kêu một tiếng ngắn khi điểm danh thành công, kêu liên hồi khi có người lạ.
- **Đèn LED:** LED Đỏ (Chân D5) chớp tắt khi cảnh báo, LED Xanh (Chân D15) sáng khi điểm danh hợp lệ.

### 3.4 Thiết kế giao thức truyền thông MQTT
Các chủ đề (Topics) được định nghĩa để trao đổi dữ liệu:
- `iot_camera/attendance/result`: Backend gửi dữ liệu nhận diện thành công (Payload JSON: `{"name": "Nguyen Van A", "time": "08:00:00"}`).
- `iot_camera/attendance/alert`: Backend gửi tín hiệu cảnh báo người lạ (Payload JSON: `{"status": "stranger"}`).
- `iot_camera/attendance/control`: Web Dashboard gửi lệnh điều khiển phần cứng từ xa (VD: Lệnh Xóa cấu hình WiFi `{"command": "reset_wifi"}` cho phép ESP32 tự động ngắt kết nối và phát ra mạng WiFi Access Point để người dùng cài đặt lại mạng mới mà không cần thao tác vật lý trên mạch).

---

## CHƯƠNG 4: TRIỂN KHAI VÀ ĐÁNH GIÁ KẾT QUẢ

### 4.1 Quá trình triển khai
- **Phần mềm:** Cài đặt môi trường Python 3.11, tải các thư viện dlib, opencv-python. Xây dựng cấu trúc thư mục chứa dataset hình ảnh. Giao diện Web được thiết kế theo phong cách hiện đại (Dark mode), có tính năng Responsive tương thích trên nhiều thiết bị.
- **Phần cứng:** Thực hiện đấu nối ESP32 với module LCD I2C (Lưu ý cấp nguồn 5V từ chân VIN cho LCD để đảm bảo độ sáng). Nạp firmware C++ thông qua Arduino IDE. Hệ thống sử dụng thư viện WiFiManager để cho phép người dùng dễ dàng cấu hình WiFi cho ESP32 qua điện thoại. Nếu mất kết nối, mạch tự động phát WiFi (`ESP32_IoT_Camera`) để chờ cài đặt lại. Đặc biệt, hệ thống hỗ trợ tính năng "Reset WiFi" từ xa qua giao diện Web Dashboard bằng bản tin MQTT. Khi nhận lệnh, ESP32 tự động xóa cấu hình mạng cũ và khởi động lại vào chế độ cài đặt mạng mới một cách tự động, an toàn và tiện lợi.

### 4.2 Kịch bản kiểm thử (Test cases)
- **Kịch bản 1 - Nhận diện nhân viên hợp lệ:** Đứng trước camera, hệ thống mất khoảng 0.2s để nhận diện. Tên nhân viên lập tức xuất hiện trên luồng Video Web, đồng thời ESP32 nhận lệnh làm màn hình LCD sáng lên hiển thị dòng chữ "Xin chao: [Tên]", còi kêu 1 tiếng bíp, đèn LED xanh sáng.
- **Kịch bản 2 - Xâm nhập bởi người lạ:** Một người chưa có trong CSDL đi qua. Màn hình máy tính khoanh đỏ khuôn mặt "Unknown". Lập tức ESP32 kích hoạt trạng thái báo động, LCD đổi sang trạng thái "! CANH BAO ! Phat Hien Nguoi La", còi hú lớn, đèn LED đỏ sáng. Quản trị viên ngồi từ xa bấm nút "Tắt Còi" trên Web, hệ thống phản hồi ngắt còi ngay lập tức.

### 4.3 Đánh giá kết quả đạt được
- Mô hình nhận diện khuôn mặt hoạt động vô cùng ổn định, có thể nhận diện đồng thời 3-5 khuôn mặt trong cùng một khung hình.
- Độ trễ (latency) khi truyền tín hiệu từ máy tính cảnh báo xuống ESP32 qua mạng MQTT cực kỳ ấn tượng, dao động từ 100ms - 300ms, tạo cảm giác tức thời.
- Giao diện quản trị hoạt động trơn tru, cho phép thao tác "Thêm khuôn mặt mới" trực tiếp qua Web mà không cần phải copy file thủ công. Hệ thống tự động học (retrain) mô hình trong tích tắc.
- Thiết kế phi-blocking (không dùng hàm `delay()`) ở ESP32 giúp thiết bị luôn phản hồi mượt mà, không bị treo kết nối MQTT.

---

## CHƯƠNG 5: KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN

### 5.1 Kết luận
Đề tài đã hoàn thành xuất sắc các mục tiêu đề ra ban đầu, tạo ra một sản phẩm công nghệ có độ hoàn thiện cao, kết hợp hài hòa giữa Trí Tuệ Nhân Tạo (AI) và Internet vạn vật (IoT). Hệ thống không chỉ dừng lại ở mức độ nghiên cứu mà đã mang tính ứng dụng thực tiễn cao, hoàn toàn có khả năng triển khai thực tế để phục vụ công tác an ninh, điểm danh tự động ở các doanh nghiệp quy mô vừa và nhỏ, trường học hoặc quản lý ra vào tại các khu vực hạn chế.

### 5.2 Hướng phát triển trong tương lai
Mặc dù hệ thống đã hoạt động tốt, vẫn còn nhiều tiềm năng để nâng cấp và mở rộng:
- **Tối ưu phần cứng xử lý AI:** Hiện tại hệ thống phụ thuộc vào sức mạnh của PC/Laptop máy chủ. Trong tương lai, có thể nhúng toàn bộ mô hình AI lên các vi mạch chuyên dụng như NVIDIA Jetson Nano hoặc Raspberry Pi để tạo thành một thiết bị All-in-One nhỏ gọn, dễ dàng lắp đặt ở mọi nơi.
- **Tích hợp cửa tự động (Access Control):** Đấu nối thêm Relay vào mạch ESP32 để kích hoạt mở khóa từ tính, cửa xoay (Turnstile) thay vì chỉ báo đèn và còi.
- **Nâng cấp CSDL và Báo cáo:** Tích hợp các hệ quản trị CSDL chuyên nghiệp (MySQL, PostgreSQL), thiết kế hệ thống báo cáo tính công tự động theo tháng, xuất file Excel để đồng bộ với bộ phận nhân sự.
- **Cảnh báo đa kênh:** Gửi ảnh người lạ chụp được (Snapshot) qua Telegram Bot hoặc Zalo OA theo thời gian thực tới điện thoại của bảo vệ/quản lý.

---
## TÀI LIỆU THAM KHẢO
1. Sách "Deep Learning for Computer Vision with Python" - Adrian Rosebrock.
2. Tài liệu kỹ thuật vi điều khiển ESP32 - Espressif Systems.
3. Tài liệu giao thức MQTT: mqtt.org.
4. Thư viện face_recognition - Adam Geitgey (GitHub).

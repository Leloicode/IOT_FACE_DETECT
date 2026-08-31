import cv2
import face_recognition
import pickle
import os

# Đường dẫn file lưu dữ liệu khuôn mặt
ENCODING_FILE = "dataset/encodings.pickle"

def train_from_video():
    print("[INFO] Bắt đầu quá trình lấy dữ liệu khuôn mặt...")
    name = input("Nhập tên người dùng (Không dấu, VD: Nguyen_Van_A): ")
    student_id = input("Nhập MSSV (VD: 123456): ")

    # Khởi tạo camera
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERROR] Không thể mở Webcam.")
        return

    print("[INFO] Vui lòng nhìn vào camera, quay các góc mặt khác nhau.")
    print("[INFO] Hệ thống sẽ tự động chụp 30 bức ảnh có khuôn mặt của bạn.")
    
    known_encodings = []
    known_names = []
    known_ids = []
    
    # Load existing data if any
    if os.path.exists(ENCODING_FILE):
        try:
            with open(ENCODING_FILE, "rb") as f:
                data = pickle.load(f)
                known_encodings = data.get("encodings", [])
                known_names = data.get("names", [])
                known_ids = data.get("ids", [])
        except Exception as e:
            print(f"[WARNING] Không thể đọc file encodings cũ: {e}")

    count = 0
    max_images = 30 # Chụp 30 góc/khung hình

    while count < max_images:
        ret, frame = cap.read()
        if not ret:
            print("[ERROR] Không thể đọc khung hình từ camera.")
            break

        # Chuyển đổi BGR (OpenCV) sang RGB (face_recognition)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Phát hiện khuôn mặt trong khung hình
        boxes = face_recognition.face_locations(rgb, model="hog")
        
        # Chỉ lấy mẫu nếu có đúng 1 khuôn mặt trong khung hình
        if len(boxes) == 1:
            # Tính toán encoding cho khuôn mặt đó
            encodings = face_recognition.face_encodings(rgb, boxes)
            
            if len(encodings) > 0:
                known_encodings.append(encodings[0])
                known_names.append(name)
                known_ids.append(student_id)
                count += 1
                
                print(f"[INFO] Đã thu thập {count}/{max_images} mẫu...")
                
                # Vẽ khung xanh để báo hiệu đang thu thập
                top, right, bottom, left = boxes[0]
                cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
        else:
            if len(boxes) > 1:
                cv2.putText(frame, "Phat hien nhieu hon 1 khuon mat!", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            else:
                cv2.putText(frame, "Khong tim thay khuon mat!", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        # Hiển thị số lượng đã thu thập
        cv2.putText(frame, f"Tiến độ: {count}/{max_images}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        cv2.imshow("Training Face", frame)

        # Nhấn 'q' để thoát sớm nếu muốn
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    if count > 0:
        # Lưu dữ liệu vào file pickle
        print("[INFO] Đang lưu dữ liệu mã hoá khuôn mặt...")
        data = {"encodings": known_encodings, "names": known_names, "ids": known_ids}
        with open(ENCODING_FILE, "wb") as f:
            pickle.dump(data, f)
        print(f"[INFO] Hoàn thành. Đã lưu dữ liệu cho người dùng: {name} - {student_id}")
    else:
        print("[WARNING] Không thu thập được dữ liệu khuôn mặt nào.")

if __name__ == "__main__":
    if not os.path.exists("dataset"):
        os.makedirs("dataset")
    train_from_video()

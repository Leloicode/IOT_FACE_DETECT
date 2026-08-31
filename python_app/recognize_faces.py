import cv2
import face_recognition
import pickle
import os
import paho.mqtt.client as mqtt
import json
from datetime import datetime
import time
import numpy as np

# Cấu hình MQTT
MQTT_BROKER = "broker.emqx.io"
MQTT_PORT = 1883
TOPIC_RESULT = "iot_camera/attendance/result"
TOPIC_ALERT = "iot_camera/attendance/alert"

# Khởi tạo MQTT Client
client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("[INFO] Đã kết nối tới MQTT Broker!")
    else:
        print(f"[ERROR] Lỗi kết nối MQTT, mã lỗi: {rc}")

client.on_connect = on_connect

print(f"[INFO] Đang kết nối tới MQTT Broker {MQTT_BROKER}...")
client.connect(MQTT_BROKER, MQTT_PORT, 60)
client.loop_start()

# Đường dẫn file dữ liệu
ENCODING_FILE = "dataset/encodings.pickle"

def recognize_faces():
    print("[INFO] Đang tải dữ liệu khuôn mặt...")
    if not os.path.exists(ENCODING_FILE):
        print("[ERROR] Không tìm thấy file dữ liệu (encodings.pickle). Vui lòng chạy train_faces.py trước!")
        return

    try:
        with open(ENCODING_FILE, "rb") as f:
            data = pickle.load(f)
    except Exception as e:
        print(f"[ERROR] Lỗi khi đọc file dữ liệu: {e}")
        return

    known_encodings = data.get("encodings", [])
    known_names = data.get("names", [])
    known_ids = data.get("ids", [])

    print("[INFO] Khởi động Webcam...")
    cap = cv2.VideoCapture(0)

    # Giảm độ phân giải để xử lý nhanh hơn (tuỳ chọn)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    # Cooldown riêng cho TỪNG người: không để người lạ chặn điểm danh người khác
    last_publish = {}          # key -> time bản tin cuối
    PER_PERSON_COOLDOWN = 5    # giây, giữa 2 lần gửi cho cùng 1 danh tính
    STRANGER_COOLDOWN = 10     # giây, giữa 2 lần cảnh báo người lạ (giảm spam)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Chuyển BGR sang RGB
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Tăng tốc: chỉ xử lý mỗi frame thứ 2 (skip frame để giảm tải CPU)
        if int(time.time() * 10) % 2 != 0:
            # vẫn hiển thị frame trước đó
            cv2.imshow("Nhan dien khuon mat", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
            continue

        # Phát hiện vị trí và mã hoá khuôn mặt trong frame
        # model="cnn" chính xác hơn nhưng chậm; "hog" nhanh hơn cho CPU thường
        boxes = face_recognition.face_locations(rgb, model="hog")
        encodings = face_recognition.face_encodings(rgb, boxes)

        names = []
        ids = []

        for encoding in encodings:
            matches = face_recognition.compare_faces(known_encodings, encoding, tolerance=0.5)
            name = "Nguoi La"
            student_id = "UNKNOWN"

            face_distances = face_recognition.face_distance(known_encodings, encoding)
            if len(face_distances) > 0:
                best_match_index = np.argmin(face_distances)
                if matches[best_match_index]:
                    name = known_names[best_match_index]
                    student_id = known_ids[best_match_index]

            names.append(name)
            ids.append(student_id)

        current_time = time.time()
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for ((top, right, bottom, left), name, student_id) in zip(boxes, names, ids):
            color = (0, 255, 0) if name != "Nguoi La" else (0, 0, 255)
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)

            y = top - 15 if top - 15 > 15 else top + 15
            cv2.putText(frame, name, (left, y), cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 2)

            # Cooldown riêng theo danh tính
            key = student_id if name != "Nguoi La" else "STRANGER"
            cooldown = PER_PERSON_COOLDOWN if name != "Nguoi La" else STRANGER_COOLDOWN
            last_time = last_publish.get(key, 0)

            if current_time - last_time >= cooldown:
                if name != "Nguoi La":
                    payload = {"name": name, "id": student_id, "time": time_str}
                    client.publish(TOPIC_RESULT, json.dumps(payload))
                    print(f"[MQTT] Đã gửi điểm danh: {name}")
                else:
                    payload = {"status": "stranger", "time": time_str}
                    client.publish(TOPIC_ALERT, json.dumps(payload))
                    print(f"[MQTT] Đã gửi cảnh báo người lạ!")
                last_publish[key] = current_time

        cv2.imshow("Nhan dien khuon mat", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    client.loop_stop()
    client.disconnect()

if __name__ == "__main__":
    recognize_faces()

"""
Webserver đầy đủ cho hệ thống điểm danh nhận diện khuôn mặt + cảnh báo IoT.

Chạy trên máy (local) nơi gắn camera:
  - Lưu lịch sử điểm danh & cảnh báo vào SQLite
  - Stream camera dạng MJPEG (/video_feed)
  - Subscribe MQTT để ghi log + đẩy realtime tới frontend
  - REST API để frontend (Vercel) lấy dữ liệu & gửi lệnh điều khiển IoT

Lưu ý: Vercel chỉ host frontend static. Backend này chạy local.
Nếu muốn frontend Vercel truy cập được camera/các API, máy local cần
public IP hoặc tunnel (ngrok/cloudflared). Cấu hình BACKEND_URL bên dưới.
"""

import json
import os
import pickle
import sqlite3
import threading
import time
from datetime import datetime

# Ép hệ điều hành CHỈ DÀNH ĐÚNG 1 NHÂN CPU CHO AI (Chống lag/treo máy do tranh giành tài nguyên)
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

import cv2
import face_recognition
import numpy as np
import paho.mqtt.client as mqtt
from flask import Flask, jsonify, render_template, request, Response
from flask_cors import CORS

# ----------------------------------------------------------------------
# Cấu hình
# ----------------------------------------------------------------------
DB_PATH = os.path.join(os.path.dirname(__file__), "attendance.db")

# URL public của backend (để frontend Vercel biết gọi vào đâu).
# Nếu máy local không public, để "" và dùng qua tunnel (ngrok).
BACKEND_URL = os.environ.get("BACKEND_URL", "")

MQTT_BROKER = os.environ.get("MQTT_BROKER", "broker.emqx.io")
MQTT_PORT = int(os.environ.get("MQTT_PORT", 1883))

TOPIC_RESULT = "iot_camera/attendance/result"
TOPIC_ALERT = "iot_camera/attendance/alert"
TOPIC_CONTROL = "iot_camera/attendance/control"
TOPIC_STATUS = "iot_camera/attendance/status"

# Camera index. 0 = webcam mặc định, hoặc URL RTSP/IP camera.
CAMERA_SOURCE = int(os.environ.get("CAMERA_SOURCE", 0))

# File dữ liệu khuôn mặt (đọc từ recognize_faces.py / train_faces.py)
ENCODING_FILE = os.path.join(os.path.dirname(__file__), "dataset", "encodings.pickle")

# ----------------------------------------------------------------------
# SQLite helpers
# ----------------------------------------------------------------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            student_id TEXT NOT NULL,
            time TEXT NOT NULL
        )
    """)
    # Thử thêm cột image (nếu bảng cũ chưa có)
    try:
        conn.execute("ALTER TABLE attendance ADD COLUMN image TEXT")
    except sqlite3.OperationalError:
        pass

    conn.execute("""
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            status TEXT NOT NULL,
            time TEXT NOT NULL,
            image TEXT
        )
    """)
    try:
        conn.execute("ALTER TABLE alerts ADD COLUMN image TEXT")
    except sqlite3.OperationalError:
        pass
    conn.execute("""
        CREATE TABLE IF NOT EXISTS controls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT NOT NULL,
            time TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def log_attendance(name, student_id, time_str, image_url=""):
    conn = get_db()
    conn.execute(
        "INSERT INTO attendance (name, student_id, time, image) VALUES (?, ?, ?, ?)",
        (name, student_id, time_str, image_url),
    )
    conn.commit()
    conn.close()


def log_alert(status, time_str, image_url=""):
    conn = get_db()
    conn.execute(
        "INSERT INTO alerts (status, time, image) VALUES (?, ?, ?)", 
        (status, time_str, image_url)
    )
    conn.commit()
    conn.close()


def log_control(action, time_str):
    conn = get_db()
    conn.execute("INSERT INTO controls (action, time) VALUES (?, ?)", (action, time_str))
    conn.commit()
    conn.close()


def already_attended_today(student_id):
    """Chống điểm danh trùng: 1 MSSV chỉ tính 1 lần / ngày."""
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM attendance WHERE student_id = ? AND time LIKE ?",
        (student_id, today + "%"),
    ).fetchone()
    conn.close()
    return row["c"] > 0


# ----------------------------------------------------------------------
# MQTT client (subscribe để ghi log + đẩy realtime)
# ----------------------------------------------------------------------
app = Flask(__name__)
CORS(app)

# Lưu trạng thái mới nhất để frontend poll nhanh (real-time bus bằng HTTP long-poll)
latest_events = []  # [{type: 'attendance'|'alert', payload: {...}}]
events_lock = threading.Lock()


def push_event(event):
    with events_lock:
        latest_events.append(event)
        if len(latest_events) > 200:  # giới hạn bộ nhớ
            latest_events.pop(0)


def on_mqtt_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode("utf-8"))
    except Exception:
        return

    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if msg.topic == TOPIC_RESULT:
        name = data.get("name", "Unknown")
        sid = data.get("id", "")
        image = data.get("image", "")
        # Chống trùng ngay tại backend (kể cả khi Python gửi 2 lần)
        if already_attended_today(sid):
            print(f"[INFO] {name} ({sid}) hôm nay đã điểm danh, bỏ qua.")
            return
        log_attendance(name, sid, time_str, image)
        event = {"type": "attendance", "payload": {**data, "time": time_str}}
        push_event(event)
        print(f"[LOG] Điểm danh: {name} - {sid} - {time_str}")

    elif msg.topic == TOPIC_ALERT:
        status = data.get("status", "stranger")
        image = data.get("image", "")
        log_alert(status, time_str, image)
        event = {"type": "alert", "payload": {**data, "time": time_str}}
        push_event(event)
        print(f"[LOG] Cảnh báo: {status} - {time_str}")


def mqtt_thread():
    client = mqtt.Client(client_id="flask_backend", clean_session=True)
    client.on_message = on_mqtt_message
    while True:
        try:
            client.connect(MQTT_BROKER, MQTT_PORT, 60)
            client.subscribe([(TOPIC_RESULT, 0), (TOPIC_ALERT, 0)])
            client.loop_forever()
        except Exception as e:
            print(f"[MQTT] Lỗi, thử lại sau 5s: {e}")
            time.sleep(5)
            # Tạo client mới vì paho không reconnect được sau exception nặng
            client = mqtt.Client(client_id="flask_backend", clean_session=True)
            client.on_message = on_mqtt_message


def start_mqtt():
    t = threading.Thread(target=mqtt_thread, daemon=True)
    t.start()


# ----------------------------------------------------------------------
# Camera: reader thread cung cấp frame duy nhất cho stream + nhận diện
# ----------------------------------------------------------------------
current_frame = None          # frame mới nhất (BGR)
current_frame_time = 0.0
cap = None
frame_lock = threading.Lock()
camera_restart_flag = False

# Kết quả nhận diện mới nhất để vẽ đè lên luồng stream nhanh
latest_faces = []
latest_faces_time = 0.0
faces_lock = threading.Lock()

def enhance_image(frame):
    """
    Tăng sáng toàn cục để làm rõ khuôn mặt bị ngược sáng.
    Không dùng CLAHE vì dễ sinh nhiễu làm nhiễu thuật toán HOG.
    """
    try:
        return cv2.convertScaleAbs(frame, alpha=1.2, beta=30)
    except Exception:
        return frame


def camera_reader():
    """Đọc liên tục từ camera vào buffer. Chạy nền, không chặn stream."""
    global current_frame, current_frame_time, cap, CAMERA_SOURCE, camera_restart_flag
    while True:
        # Sử dụng cv2.CAP_DSHOW để ép dùng DirectShow trên Windows, sửa lỗi "obsensor... Camera index out of range"
        cap = cv2.VideoCapture(CAMERA_SOURCE, cv2.CAP_DSHOW)
        # Ép camera không được lưu bộ đệm (giảm độ trễ/delay hình ảnh về 0)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if not cap.isOpened(): 
            time.sleep(1)
            continue
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        while not camera_restart_flag:
            ok, frame = cap.read()
            if not ok:
                time.sleep(0.05)
                continue
            with frame_lock:
                current_frame = frame
                current_frame_time = time.time()
                
        cap.release()
        camera_restart_flag = False


def grab_frame():
    """Lấy bản copy frame mới nhất (None nếu chưa có)."""
    with frame_lock:
        if current_frame is None:
            return None
        return current_frame.copy()


def gen_frames():
    fps = 0
    fps_start_time = time.time()
    fps_frames = 0
    while True:
        # Luôn lấy frame mới nhất từ camera (đảm bảo độ mượt 30FPS)
        frame = grab_frame()
        if frame is None:
            time.sleep(0.05)
            continue
            
        display_frame = frame.copy()

        # Tính toán FPS của luồng stream
        fps_frames += 1
        now = time.time()
        if now - fps_start_time >= 1.0:
            fps = fps_frames / (now - fps_start_time)
            fps_frames = 0
            fps_start_time = now

        # Vẽ thời gian và FPS
        time_str = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        cv2.putText(display_frame, f"{time_str} | FPS: {fps:.1f}", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        # Vẽ đè các khuôn mặt đã nhận diện (nếu dữ liệu chưa quá cũ)
        with faces_lock:
            if now - latest_faces_time < 1.5:  # Tăng thời gian giữ khung lên 1.5s để chống nháy
                for (left, top, right, bottom, name, color) in latest_faces:
                    # Viền rõ nét hơn (độ dày 2)
                    cv2.rectangle(display_frame, (left, top), (right, bottom), color, 2)
                    y = top - 15 if top - 15 > 15 else top + 15
                    # Font chữ rõ hơn
                    cv2.putText(display_frame, name, (left, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        ret, jpeg = cv2.imencode(".jpg", display_frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
        if not ret:
            time.sleep(0.01)
            continue
        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n")
        time.sleep(0.02)  # Giảm sleep để tăng FPS lên tối đa


# ----------------------------------------------------------------------
# Nhận diện & điểm danh (chạy trong backend, điều khiển từ web)
# ----------------------------------------------------------------------
recognizer_state = {
    "running": False,
    "message": "Chưa bật nhận diện.",
    "cooldown_seconds": 5,
    "stranger_cooldown": 10,
}
recognizer_lock = threading.Lock()


def _load_known_faces():
    """Đọc encodings.pickle, trả (encodings, names, ids)."""
    encodings, names, ids = [], [], []
    if os.path.exists(ENCODING_FILE):
        try:
            with open(ENCODING_FILE, "rb") as f:
                data = pickle.load(f)
            encodings = data.get("encodings", [])
            names = data.get("names", [])
            ids = data.get("ids", [])
        except Exception as e:
            print(f"[WARNING] Không đọc được encodings: {e}")
    return encodings, names, ids


def recognizer_loop():
    last_publish = {}
    frame_count = 0
    # Lưu lại danh sách nhân dạng lần trước để tái sử dụng cho các frame theo dõi (tracking)
    tracked_faces = [] 

    while True:
        with recognizer_lock:
            if not recognizer_state["running"]:
                time.sleep(0.2)
                continue
            cooldown = recognizer_state["cooldown_seconds"]
            stranger_cooldown = recognizer_state["stranger_cooldown"]

        known_encodings, known_names, known_ids = _load_known_faces()
        # Nếu chưa có dữ liệu khuôn mặt
        if not known_encodings:
            with recognizer_lock:
                recognizer_state["message"] = "Chưa có dữ liệu khuôn mặt. Hãy đăng ký nhân viên trước."
            update_overlay_no_face("Chua co du lieu khuon mat")
            time.sleep(2)
            continue

        frame = grab_frame()
        if frame is None:
            time.sleep(0.05)
            continue

        # Chống ngược sáng bằng cách tăng sáng cơ bản
        enhanced_frame = enhance_image(frame)

        # Thu nhỏ ảnh để tìm khuôn mặt nhanh và chính xác hơn với HOG
        small_frame = cv2.resize(enhanced_frame, (0, 0), fx=0.5, fy=0.5)
        rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
        rgb_small = np.ascontiguousarray(rgb_small, dtype=np.uint8)
        
        boxes_small = face_recognition.face_locations(rgb_small, model="hog")
        scaled_boxes = [(t*2, r*2, b*2, l*2) for (t, r, b, l) in boxes_small]

        now = time.time()
        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        faces_to_draw = []
        frame_count += 1

        # 2. Thuật toán Tracking: Chỉ trích xuất nhân dạng (RẤT CHẬM ~300ms) mỗi 3 frame
        # Hoặc khi số lượng khuôn mặt thay đổi
        if frame_count % 3 == 0 or len(scaled_boxes) != len(tracked_faces):
            rgb_full = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb_full = np.ascontiguousarray(rgb_full, dtype=np.uint8)
            encodings = face_recognition.face_encodings(rgb_full, scaled_boxes)

            new_tracked = []
            for i, (box, enc) in enumerate(zip(scaled_boxes, encodings)):
                # Ngưỡng (tolerance) mặc định là 0.6, giảm xuống 0.45 để cân bằng giữa
                # việc nhận ra người quen và không nhận nhầm người lạ.
                matches = face_recognition.compare_faces(known_encodings, enc, tolerance=0.45)
                name = "Nguoi La"
                student_id = "UNKNOWN"
                dists = face_recognition.face_distance(known_encodings, enc)
                if len(dists) > 0:
                    best = int(np.argmin(dists))
                    if matches[best]:
                        name = known_names[best]
                        student_id = known_ids[best]
                
                color = (0, 255, 0) if name != "Nguoi La" else (0, 0, 255)
                new_tracked.append({"box": box, "name": name, "id": student_id, "color": color})
                
                # Vẽ box
                t, r, b, l = box
                faces_to_draw.append((l, t, r, b, name, color))

                # Gửi tín hiệu điểm danh
                key = student_id if name != "Nguoi La" else "STRANGER"
                cd = cooldown if name != "Nguoi La" else stranger_cooldown
                last = last_publish.get(key, 0)
                if now - last >= cd:
                    # CẮT ẢNH KHUÔN MẶT ĐỂ HIỂN THỊ LÊN WEB
                    padding = 30
                    fh, fw, _ = frame.shape
                    pt = max(0, t - padding)
                    pb = min(fh, b + padding)
                    pl = max(0, l - padding)
                    pr = min(fw, r + padding)
                    face_crop = frame[pt:pb, pl:pr]
                    
                    filename = f"{key}_{int(now)}.jpg"
                    captures_dir = os.path.join(os.path.dirname(__file__), "static", "captures")
                    os.makedirs(captures_dir, exist_ok=True)
                    filepath = os.path.join(captures_dir, filename)
                    
                    # Sửa lỗi OpenCV không lưu được ảnh trên Windows nếu đường dẫn có dấu tiếng Việt
                    is_success, im_buf_arr = cv2.imencode(".jpg", face_crop)
                    if is_success:
                        with open(filepath, "wb") as f:
                            f.write(im_buf_arr)
                    
                    image_url = f"/static/captures/{filename}"

                    if name != "Nguoi La":
                        publish_client.publish(TOPIC_RESULT, json.dumps({"name": name, "id": student_id, "time": time_str, "image": image_url}))
                        print(f"[RECOG] Diem danh: {name} - {student_id}")
                    else:
                        publish_client.publish(TOPIC_ALERT, json.dumps({"status": "stranger", "time": time_str, "image": image_url}))
                        print(f"[RECOG] CANH BAO nguoi la")
                    last_publish[key] = now
            
            tracked_faces = new_tracked

        else:
            # FRAME THEO DÕI: Không phân tích AI, chỉ gán tên cũ cho khuôn mặt gần nhất
            available_tracked = tracked_faces.copy()
            for box in scaled_boxes:
                t, r, b, l = box
                cx = (l + r) / 2
                cy = (t + b) / 2
                
                best_match = None
                min_dist = 999999
                best_match_idx = -1
                for idx, tf in enumerate(available_tracked):
                    tt, tr, tb, tl = tf["box"]
                    tcx = (tl + tr) / 2
                    tcy = (tt + tb) / 2
                    dist = (cx - tcx)**2 + (cy - tcy)**2
                    if dist < min_dist:
                        min_dist = dist
                        best_match = tf
                        best_match_idx = idx
                
                if best_match and min_dist < 10000: # Nếu mặt di chuyển không quá xa
                    faces_to_draw.append((l, t, r, b, best_match["name"], best_match["color"]))
                    # Xóa mặt đã match để không gán nhầm tên 1 người cho 2 khuôn mặt đứng gần nhau
                    available_tracked.pop(best_match_idx)
                else:
                    faces_to_draw.append((l, t, r, b, "Dang quet...", (0, 255, 255)))

        # Cập nhật danh sách vẽ đè cho luồng stream
        with faces_lock:
            global latest_faces, latest_faces_time
            if len(faces_to_draw) > 0:
                latest_faces = faces_to_draw
                latest_faces_time = now
            elif now - latest_faces_time > 1.5:
                # Xóa sạch nếu đã quá 1.5 giây không tìm thấy mặt nào
                latest_faces = []

        # Giảm tải CPU, nhường tài nguyên cho luồng Camera Stream chạy mượt 30FPS
        time.sleep(0.03)

def update_overlay_no_face(msg):
    with faces_lock:
        global latest_faces, latest_faces_time
        latest_faces = [(10, 40, 10, 40, msg, (0, 0, 255))]
        latest_faces_time = time.time()


def start_recognizer():
    with recognizer_lock:
        recognizer_state["running"] = True
        recognizer_state["message"] = "Nhận diện đang chạy..."


def stop_recognizer():
    with recognizer_lock:
        recognizer_state["running"] = False
        recognizer_state["message"] = "Đã dừng nhận diện."
    with faces_lock:
        global latest_faces
        latest_faces = []


def start_camera_threads():
    threading.Thread(target=camera_reader, daemon=True).start()
    threading.Thread(target=recognizer_loop, daemon=True).start()


# ----------------------------------------------------------------------
# Đăng ký nhân viên mới (train từ camera của backend)
# ----------------------------------------------------------------------
# Trạng thái đăng ký đang chạy (ngăn 2 đăng ký cùng lúc)
register_state = {
    "running": False,
    "name": "",
    "student_id": "",
    "count": 0,
    "max": 30,
    "message": "",
    "done": False,
    "success": False,
}
register_lock = threading.Lock()
REGISTER_TIMEOUT = 30  # giây tối đa đợi đủ mẫu


def load_encodings():
    """Đọc encodings.pickle hiện có, trả (encodings, names, ids)."""
    encodings, names, ids = [], [], []
    if os.path.exists(ENCODING_FILE):
        try:
            with open(ENCODING_FILE, "rb") as f:
                data = pickle.load(f)
            encodings = data.get("encodings", [])
            names = data.get("names", [])
            ids = data.get("ids", [])
        except Exception as e:
            print(f"[WARNING] Không đọc được encodings cũ: {e}")
    return encodings, names, ids


def save_encodings(encodings, names, ids):
    os.makedirs(os.path.dirname(ENCODING_FILE), exist_ok=True)
    with open(ENCODING_FILE, "wb") as f:
        pickle.dump({"encodings": encodings, "names": names, "ids": ids}, f)


def _register_worker(name, student_id, max_images):
    try:
        # Nếu nhận diện đang chạy, tạm dừng để camera phục vụ đăng ký
        was_running = False
        with recognizer_lock:
            if recognizer_state["running"]:
                was_running = True
                recognizer_state["running"] = False
        with faces_lock:
            global latest_faces
            latest_faces = []

        encodings, names, ids = load_encodings()
        count = 0
        start = time.time()

        while count < max_images and (time.time() - start) < REGISTER_TIMEOUT:
            frame = grab_frame()
            if frame is None:
                time.sleep(0.05)
                continue

            time.sleep(0.15)  # giãn cách giữa các mẫu để quay góc khác nhau

            time.sleep(0.15)  # giãn cách giữa các mẫu để quay góc khác nhau

            # Tăng sáng để lấy nét khuôn mặt ngược sáng
            enhanced_frame = enhance_image(frame)

            # Thu nhỏ ảnh giúp thuật toán HOG bỏ qua nhiễu và tìm mặt dễ hơn
            small_frame = cv2.resize(enhanced_frame, (0, 0), fx=0.5, fy=0.5)
            rgb_small = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)
            rgb_small = np.ascontiguousarray(rgb_small, dtype=np.uint8)
            boxes_small = face_recognition.face_locations(rgb_small, model="hog")
            
            if len(boxes_small) == 1:
                scaled_boxes = [(t*2, r*2, b*2, l*2) for (t, r, b, l) in boxes_small]
                
                rgb_full = cv2.cvtColor(enhanced_frame, cv2.COLOR_BGR2RGB)
                rgb_full = np.ascontiguousarray(rgb_full, dtype=np.uint8)
                
                feats = face_recognition.face_encodings(rgb_full, scaled_boxes)
                if feats:
                    encodings.append(feats[0])
                    names.append(name)
                    ids.append(student_id)
                    count += 1
                    with register_lock:
                        register_state["count"] = count

        # Khôi phục nhận diện nếu trước đó đang chạy
        if was_running:
            with recognizer_lock:
                recognizer_state["running"] = True

        with register_lock:
            register_state["running"] = False
            register_state["done"] = True
            if count > 0:
                save_encodings(encodings, names, ids)
                register_state["success"] = True
                register_state["message"] = (
                    f"Đăng ký thành công: {name} ({student_id}) với {count} mẫu."
                )
            else:
                register_state["success"] = False
                register_state["message"] = (
                    "Không thu thập được khuôn mặt. Hãy nhìn thẳng vào camera, "
                    "một người, đủ ánh sáng."
                )
    except Exception as e:
        with register_lock:
            register_state["running"] = False
            register_state["done"] = True
            register_state["success"] = False
            register_state["message"] = f"Lỗi khi đăng ký: {e}"
        with recognizer_lock:
            recognizer_state["running"] = False


@app.route("/api/register", methods=["POST"])
def api_register():
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip()
    student_id = (body.get("student_id") or "").strip()

    if not name or not student_id:
        return jsonify({"ok": False, "error": "Thiếu name hoặc student_id"}), 400

    # Tên không dấu, thay khoảng trắng bằng dấu gạch dưới (khớp qui ước)
    name = " ".join(name.split()).replace(" ", "_")

    with register_lock:
        if register_state["running"]:
            return jsonify({"ok": False, "error": "Đang có một đăng ký chạy. Hãy chờ."}), 409
        register_state.update({
            "running": True,
            "name": name,
            "student_id": student_id,
            "count": 0,
            "max": int(body.get("samples", 30)),
            "message": "Đang khởi động camera...",
            "done": False,
            "success": False,
        })

    threading.Thread(
        target=_register_worker,
        args=(name, student_id, register_state["max"]),
        daemon=True,
    ).start()

    return jsonify({"ok": True, "message": "Đã bắt đầu đăng ký."})


@app.route("/api/register/status")
def api_register_status():
    with register_lock:
        return jsonify(dict(register_state))


@app.route("/api/employees")
def api_employees():
    """Lấy danh sách sinh viên/nhân viên đã đăng ký từ file pickle."""
    encodings, names, ids = load_encodings()
    employees = {}
    for name, sid in zip(names, ids):
        if sid not in employees:
            employees[sid] = {"name": name, "samples": 0}
        employees[sid]["samples"] += 1
        
    result = [{"student_id": sid, "name": data["name"], "samples": data["samples"]} for sid, data in employees.items()]
    return jsonify(result)


@app.route("/api/employees/<student_id>", methods=["DELETE"])
def api_delete_employee(student_id):
    """Xóa toàn bộ dữ liệu khuôn mặt của một nhân viên dựa trên MSSV."""
    encodings, names, ids = load_encodings()
    new_enc, new_names, new_ids = [], [], []
    found = False
    
    for enc, name, sid in zip(encodings, names, ids):
        if sid != student_id:
            new_enc.append(enc)
            new_names.append(name)
            new_ids.append(sid)
        else:
            found = True
            
    if not found:
        return jsonify({"ok": False, "error": "Không tìm thấy MSSV này."}), 404
        
    # Lưu lại file pickle (Ghi đè)
    save_encodings(new_enc, new_names, new_ids)
    return jsonify({"ok": True, "message": "Đã xóa thành công."})


# ----------------------------------------------------------------------
# REST API
# ----------------------------------------------------------------------
@app.route("/api/attendance")
def api_attendance():
    limit = min(int(request.args.get("limit", 50)), 500)
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM attendance ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/api/alerts")
def api_alerts():
    limit = min(int(request.args.get("limit", 50)), 500)
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM alerts ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])





@app.route("/api/events")
def api_events():
    """Trả các sự kiện mới nhất (polling đơn giản cho realtime)."""
    with events_lock:
        return jsonify(list(latest_events))





@app.route("/api/status")
def api_status():
    """Trạng thái hệ thống (từ ESP32 publish TOPIC_STATUS nếu có)."""
    with recognizer_lock:
        recog = dict(recognizer_state)
    return jsonify({
        "system": "online",
        "backend_url": BACKEND_URL,
        "recognizer": recog,
        "has_face_data": os.path.exists(ENCODING_FILE),
        "camera_source": CAMERA_SOURCE
    })


@app.route("/api/camera", methods=["POST"])
def api_set_camera():
    global CAMERA_SOURCE, camera_restart_flag
    body = request.get_json(silent=True) or {}
    try:
        source = int(body.get("source", 0))
    except ValueError:
        source = 0
    CAMERA_SOURCE = source
    camera_restart_flag = True
    return jsonify({"ok": True, "message": f"Đã chuyển sang Camera {source}"})


@app.route("/api/recognizer", methods=["POST"])
def api_recognizer():
    """Bật/tắt nhận diện: {action: 'start'|'stop'}."""
    body = request.get_json(silent=True) or {}
    action = body.get("action")

    if action == "start":
        if not os.path.exists(ENCODING_FILE):
            return jsonify({"ok": False, "error": "Chưa có dữ liệu khuôn mặt. Hãy đăng ký nhân viên trước."}), 400
        with register_lock:
            if register_state["running"]:
                return jsonify({"ok": False, "error": "Đang đăng ký nhân viên, chưa thể nhận diện."}), 409
        # Yêu cầu recognizer reload dữ liệu (không cần, nó load mỗi frame)
        start_recognizer()
        return jsonify({"ok": True, "message": "Đã bật nhận diện."})
    elif action == "stop":
        stop_recognizer()
        return jsonify({"ok": True, "message": "Đã dừng nhận diện."})
    else:
        return jsonify({"ok": False, "error": "Invalid action"}), 400


@app.route("/api/recognizer/status")
def api_recognizer_status():
    with recognizer_lock:
        return jsonify(dict(recognizer_state))


@app.route("/video_feed")
def video_feed():
    """MJPEG stream để dashboard giám sát camera trực tiếp."""
    return Response(gen_frames(), mimetype="multipart/x-mixed-replace; boundary=frame")


# ----------------------------------------------------------------------
# Publish client (để gửi lệnh điều khiển xuống ESP32)
# ----------------------------------------------------------------------
publish_client = mqtt.Client(client_id="flask_control", clean_session=True)


def start_publish():
    try:
        publish_client.connect(MQTT_BROKER, MQTT_PORT, 60)
        publish_client.loop_start()
    except Exception as e:
        print(f"[MQTT] Lỗi kết nối publish client: {e}")


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
if __name__ == "__main__":
    init_db()
    start_mqtt()
    start_publish()
    start_camera_threads()
    port = int(os.environ.get("PORT", 5000))
    # host='0.0.0.0' để truy cập từ mạng LAN
    print(f"[INFO] Webserver chạy tại http://0.0.0.0:{port}")
    print("[INFO] Camera stream:  http://<IP>:{}/video_feed".format(port))
    print("[INFO] API:            http://<IP>:{}/api/attendance".format(port))
    from waitress import serve
    serve(app, host="0.0.0.0", port=port, threads=16)

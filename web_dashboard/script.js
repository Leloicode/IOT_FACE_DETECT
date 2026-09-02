// ============================================================
// Cấu hình MQTT (WebSocket trên trình duyệt + Vercel static)
// ============================================================
const clientId = 'mqttjs_' + Math.random().toString(16).substr(2, 8);
const MQTT_HOST = 'wss://broker.emqx.io:8084/mqtt';

const TOPIC_RESULT = 'iot_camera/attendance/result';
const TOPIC_ALERT = 'iot_camera/attendance/alert';
const TOPIC_CONTROL = 'iot_camera/attendance/control';

// Backend URL (Flask local / tunnel). Lưu trong localStorage để cấu hình.
const BACKEND_KEY = 'attendance_backend_url';
let BACKEND_URL = localStorage.getItem(BACKEND_KEY) || 'http://localhost:5000';

// ============================================================
// LOGIN & BẢO MẬT (GOOGLE SHEETS)
// ============================================================
// Đã tự động điền URL Web App Google Apps Script của bạn
const GOOGLE_SCRIPT_URL = 'https://script.google.com/macros/s/AKfycbytui7F9qARt7BwDabZfxcsCt0sw_qCj1ICDQnmmai981HDEJ2G7VOkG3nMwJVY56Qy/exec'; 

const loginOverlay = document.getElementById('login-overlay');
const mainContainer = document.getElementById('main-app-container');
const btnLogin = document.getElementById('btn-login');
const loginKeyInput = document.getElementById('login-key');
const loginError = document.getElementById('login-error');

// Kiểm tra xem đã đăng nhập chưa
const sessionKey = localStorage.getItem('is_logged_in');
if (sessionKey === 'true') {
    // Đã đăng nhập trong phiên này -> Bỏ qua form login
    loginOverlay.style.display = 'none';
    mainContainer.style.display = 'block';
} else {
    // Chưa đăng nhập -> Hiện form login
    loginOverlay.classList.remove('hidden');
}

btnLogin.addEventListener('click', async () => {
    const key = loginKeyInput.value.trim();
    if (!key) {
        loginError.textContent = "Vui lòng nhập mã truy cập!";
        loginError.classList.remove('hidden');
        return;
    }

    // Hiển thị trạng thái đang tải
    btnLogin.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Đang kiểm tra...';
    btnLogin.disabled = true;
    loginError.classList.add('hidden');

    try {
        const response = await fetch(GOOGLE_SCRIPT_URL, {
            method: 'POST',
            body: JSON.stringify({ key: key, hwid: 'web-dashboard' }) 
            // Gửi chữ web-dashboard làm hwid giả để Apps Script tương thích với code cũ
        });
        
        const data = await response.json();
        
        if (data.status === 'success') {
            // Đăng nhập thành công
            localStorage.setItem('is_logged_in', 'true');
            
            // Hiệu ứng ẩn form login
            loginOverlay.classList.add('hidden');
            setTimeout(() => {
                loginOverlay.style.display = 'none';
                mainContainer.style.display = 'block';
            }, 500); // Đợi 0.5s cho animation mờ dần
            
        } else {
            // Key sai hoặc hết hạn
            loginError.textContent = data.message || "Key không hợp lệ hoặc đã hết hạn!";
            loginError.classList.remove('hidden');
        }
    } catch (error) {
        console.error("Lỗi xác thực:", error);
        loginError.textContent = "Không thể kết nối đến máy chủ xác thực. Kiểm tra lại mạng hoặc URL Apps Script.";
        loginError.classList.remove('hidden');
    } finally {
        // Khôi phục nút
        btnLogin.innerHTML = '<i class="fa-solid fa-right-to-bracket"></i> Xác Thực';
        btnLogin.disabled = false;
    }
});

// Cho phép nhấn Enter để đăng nhập
loginKeyInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        btnLogin.click();
    }
});

// ============================================================
// DOM
// ============================================================
const $ = (id) => document.getElementById(id);
const statusBadge = $('mqtt-status');
const backendBadge = $('backend-status');
const attendanceBody = $('attendance-body');
const attendanceBodyCamera = $('attendance-body-camera'); // Bảng điểm danh bên tab Camera
const totalCountEl = $('total-count');
const alertBox = $('alert-box');
const alertContent = $('alert-content');

let attendanceCount = 0;
let alertTimeout;
let cameraInterval;

// ============================================================
// MQTT client
// ============================================================
console.log('Connecting to MQTT broker...');
const client = mqtt.connect(MQTT_HOST, {
    clientId,
    clean: true,
    connectTimeout: 4000,
});

client.on('connect', () => {
    console.log('Connected to MQTT');
    statusBadge.className = 'status-badge connected';
    statusBadge.innerHTML = '<i class="fa-solid fa-circle-check"></i> Đã kết nối MQTT';
    client.subscribe([TOPIC_RESULT, TOPIC_ALERT]);
});

client.on('offline', () => {
    statusBadge.className = 'status-badge disconnected';
    statusBadge.innerHTML = '<i class="fa-solid fa-circle-xmark"></i> Mất kết nối MQTT';
});

client.on('message', (topic, message) => {
    try {
        const data = JSON.parse(message.toString());
        if (topic === TOPIC_RESULT) handleResult(data);
        else if (topic === TOPIC_ALERT) handleAlert(data);
    } catch (e) {
        console.error('Error parsing JSON:', e);
    }
});

// ============================================================
// Xử lý sự kiện
// ============================================================
function addAttendanceRow(name, id, time, imageUrl) {
    if (attendanceCount === 0) {
        attendanceBody.innerHTML = '';
        if (attendanceBodyCamera) attendanceBodyCamera.innerHTML = '';
    }

    attendanceCount++;
    totalCountEl.textContent = `${attendanceCount} người`;

    // Nếu không có ảnh, dùng ảnh mặc định rỗng
    const imgTag = imageUrl ? `<img src="${BACKEND_URL}${imageUrl}" style="width: 40px; height: 40px; border-radius: 50%; object-fit: cover; border: 2px solid #00f2fe; cursor: pointer; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.2)'" onmouseout="this.style.transform='scale(1)'" onclick="window.open('${BACKEND_URL}${imageUrl}', '_blank')">` : `<i class="fa-solid fa-user-tie" style="font-size: 24px; color: #888;"></i>`;

    // --- Cập nhật bảng Dashboard chính ---
    const tr1 = document.createElement('tr');
    tr1.className = 'new-row';
    tr1.innerHTML = `
        <td>${attendanceCount}</td>
        <td style="text-align: center;">${imgTag}</td>
        <td><strong>${escapeHtml(name)}</strong></td>
        <td>${escapeHtml(id)}</td>
        <td>${escapeHtml(time)}</td>
    `;
    attendanceBody.insertBefore(tr1, attendanceBody.firstChild);

    // --- Cập nhật bảng bên Tab Camera (ít cột hơn cho gọn) ---
    if (attendanceBodyCamera) {
        const tr2 = document.createElement('tr');
        tr2.className = 'new-row';
        tr2.innerHTML = `
            <td>${attendanceCount}</td>
            <td style="text-align: center;">${imgTag}</td>
            <td><strong>${escapeHtml(name)}</strong></td>
            <td>${escapeHtml(time)}</td>
        `;
        attendanceBodyCamera.insertBefore(tr2, attendanceBodyCamera.firstChild);
    }

    // Giới hạn hiển thị 100 dòng trên bảng realtime
    while (attendanceBody.children.length > 100) {
        attendanceBody.removeChild(attendanceBody.lastChild);
    }
    if (attendanceBodyCamera) {
        while (attendanceBodyCamera.children.length > 100) {
            attendanceBodyCamera.removeChild(attendanceBodyCamera.lastChild);
        }
    }
}

let attendedToday = new Set(); // Chống hiển thị trùng lặp trên bảng realtime

function handleResult(data) {
    if (attendedToday.has(data.id)) return; // Bỏ qua nếu đã hiện trên bảng
    attendedToday.add(data.id);
    addAttendanceRow(data.name, data.id, data.time, data.image);
}

function handleAlert(data) {
    if (data.status === 'stranger') {
        alertBox.classList.add('active-alert');
        alertContent.innerHTML = `
            <div class="icon-pulse">
                <i class="fa-solid fa-triangle-exclamation"></i>
            </div>
            <h3>CẢNH BÁO NGƯỜI LẠ!</h3>
            <p>Phát hiện đối tượng không xác định lúc ${escapeHtml(data.time)}</p>
        `;
        clearTimeout(alertTimeout);
        alertTimeout = setTimeout(resetAlertUI, 5000);
    }
}

function resetAlertUI() {
    alertBox.classList.remove('active-alert');
    alertContent.innerHTML = `
        <div class="icon-pulse">
            <i class="fa-solid fa-shield-halved"></i>
        </div>
        <h3>Hệ Thống An Toàn</h3>
        <p>Chưa phát hiện người lạ trong khu vực.</p>
    `;
}

function escapeHtml(str) {
    return String(str).replace(/[&<>"']/g, (c) => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
}

// ============================================================
// Điều khiển IoT (gửi 2 nơi: MQTT trực tiếp + API backend)
// ============================================================
function sendControl(action, label) {
    const statusEl = $('iot-control-status');
    const payload = JSON.stringify({ action });

    // Gửi qua MQTT (tới ESP32)
    if (client.connected) {
        client.publish(TOPIC_CONTROL, payload);
    }

    // Gửi qua backend (để log lịch sử điều khiển) — nếu có backend
    if (BACKEND_URL) {
        fetch(joinUrl(BACKEND_URL, '/api/control'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: payload,
        }).catch((err) => console.error('Backend control error:', err));
    }

    statusEl.textContent = `✅ Đã gửi lệnh "${label}" lúc ${new Date().toLocaleTimeString('vi-VN')}`;
    statusEl.className = 'iot-command-status ok';
    setTimeout(() => (statusEl.textContent = 'Chưa gửi lệnh.'), 4000);
}

$('btn-reset-alert').addEventListener('click', () => {
    resetAlertUI();
    sendControl('reset_buzzer', 'Tắt còi báo động');
});

// ============================================================
// Backend API helpers
// ============================================================
function joinUrl(base, path) {
    return base.replace(/\/+$/, '') + path;
}

async function loadBackendData() {
    if (!BACKEND_URL) {
        backendBadge.className = 'status-badge disconnected';
        backendBadge.innerHTML = '<i class="fa-solid fa-server"></i> Backend chưa cấu hình';
        return;
    }
    const base = BACKEND_URL;
    // Kiểm tra backend online
    try {
        const res = await fetch(joinUrl(base, '/api/status'));
        if (!res.ok) throw new Error(res.status);
        backendBadge.className = 'status-badge connected';
        backendBadge.innerHTML = '<i class="fa-solid fa-circle-check"></i> Backend online';
    } catch (e) {
        backendBadge.className = 'status-badge disconnected';
        backendBadge.innerHTML = '<i class="fa-solid fa-server"></i> Backend offline';
        return;
    }

    // Lịch sử điểm danh
    try {
        const res = await fetch(joinUrl(base, '/api/attendance?limit=100'));
        const rows = await res.json();
        const tbody = $('history-body');
        tbody.innerHTML = '';
        if (!rows.length) {
            tbody.innerHTML = '<tr class="empty-row"><td colspan="5">Chưa có dữ liệu.</td></tr>';
        } else {
            rows.forEach((item, index) => {
                const tr = document.createElement('tr');
                const imgTag = item.image ? `<img src="${BACKEND_URL}${item.image}" style="width: 40px; height: 40px; border-radius: 50%; object-fit: cover; border: 2px solid #00f2fe; cursor: pointer; transition: transform 0.2s;" onmouseover="this.style.transform='scale(1.2)'" onmouseout="this.style.transform='scale(1)'" onclick="window.open('${BACKEND_URL}${item.image}', '_blank')">` : `<i class="fa-solid fa-user-tie" style="font-size: 24px; color: #888;"></i>`;
                tr.innerHTML = `
                    <td>${index + 1}</td>
                    <td style="text-align: center;">${imgTag}</td>
                    <td><strong>${escapeHtml(item.name)}</strong></td>
                    <td>${escapeHtml(item.student_id)}</td>
                    <td>${escapeHtml(item.time)}</td>
                `;
                tbody.appendChild(tr);
            });
        }
    } catch (e) {
        console.error('Load attendance history error:', e);
    }

    // Lịch sử cảnh báo
    try {
        const res = await fetch(joinUrl(base, '/api/alerts?limit=100'));
        const rows = await res.json();
        const tbody = $('alerts-body');
        tbody.innerHTML = '';
        if (!rows.length) {
            tbody.innerHTML = '<tr class="empty-row"><td colspan="3">Chưa có dữ liệu.</td></tr>';
        } else {
            rows.forEach((r, i) => {
                const statusText = r.status === 'stranger' ? 'Người lạ' : r.status;
                tbody.innerHTML += `
                    <tr>
                        <td>${i + 1}</td>
                        <td><span class="alert-tag">${escapeHtml(statusText)}</span></td>
                        <td>${escapeHtml(r.time)}</td>
                    </tr>`;
            });
        }
    } catch (e) {
        console.error('Load alert history error:', e);
    }

    // Lịch sử điều khiển IoT
    try {
        const res = await fetch(joinUrl(base, '/api/controls?limit=100'));
        const rows = await res.json();
        const tbody = $('controls-body');
        tbody.innerHTML = '';
        if (!rows.length) {
            tbody.innerHTML = '<tr class="empty-row"><td colspan="3">Chưa có dữ liệu.</td></tr>';
        } else {
            rows.forEach((r, i) => {
                const actionText = r.action === 'reset_buzzer' ? 'Tắt còi báo động' : r.action;
                tbody.innerHTML += `
                    <tr>
                        <td>${i + 1}</td>
                        <td><span class="alert-tag" style="background:var(--primary); color:white">${escapeHtml(actionText)}</span></td>
                        <td>${escapeHtml(r.time)}</td>
                    </tr>`;
            });
        }
    } catch (e) {
        console.error('Load controls history error:', e);
    }
    
    // Tải danh sách nhân viên đã đăng ký
    loadEmployees();
}

// ============================================================
// Employee List & Delete
// ============================================================
async function loadEmployees() {
    if (!BACKEND_URL) return;
    try {
        const res = await fetch(joinUrl(BACKEND_URL, '/api/employees'));
        const rows = await res.json();
        const tbody = $('employees-body');
        if (!tbody) return;
        tbody.innerHTML = '';
        if (!rows.length) {
            tbody.innerHTML = '<tr class="empty-row"><td colspan="5">Chưa có nhân viên nào.</td></tr>';
        } else {
            rows.forEach((r, i) => {
                tbody.innerHTML += `
                    <tr>
                        <td>${i + 1}</td>
                        <td><strong>${escapeHtml(r.name)}</strong></td>
                        <td>${escapeHtml(r.student_id)}</td>
                        <td>${escapeHtml(r.samples.toString())} mẫu</td>
                        <td>
                            <button class="btn btn-primary" style="background:#e53e3e; padding:5px 10px; font-size:14px" onclick="deleteEmployee('${r.student_id}')">
                                <i class="fa-solid fa-trash"></i> Xóa
                            </button>
                        </td>
                    </tr>`;
            });
        }
    } catch (e) {
        console.error('Load employees error:', e);
    }
}

async function deleteEmployee(studentId) {
    if (!confirm('Bạn có chắc chắn muốn xóa dữ liệu khuôn mặt của nhân viên này?')) return;
    try {
        const res = await fetch(joinUrl(BACKEND_URL, '/api/employees/' + studentId), {
            method: 'DELETE'
        });
        const data = await res.json();
        if (data.ok) {
            alert('Đã xóa thành công!');
            loadEmployees(); // Tải lại bảng
        } else {
            alert('Lỗi: ' + data.error);
        }
    } catch (e) {
        alert('Lỗi kết nối khi xóa nhân viên.');
        console.error(e);
    }
}

// ============================================================
// Camera
// ============================================================
function toggleCamera() {
    const btn = $('btn-toggle-camera');
    const viewer = $('camera-viewer');

    if (cameraInterval) {
        // tắt
        clearInterval(cameraInterval);
        cameraInterval = null;
        btn.innerHTML = '<i class="fa-solid fa-play"></i> Bật Camera';
        viewer.innerHTML = `
            <div class="camera-placeholder">
                <i class="fa-solid fa-video-slash"></i>
                <p>Camera đã tắt.</p>
            </div>`;
        return;
    }

    if (!BACKEND_URL) {
        alert('Vui lòng cấu hình Backend URL trong tab Cấu Hình.');
        return;
    }

    // Bật: Bơm mjpeg stream liên tục bằng 1 thẻ img duy nhất
    viewer.innerHTML = `
        <img src="${joinUrl(BACKEND_URL, '/video_feed')}?t=${Date.now()}" alt="Camera stream" style="width: 100%; border-radius: 8px;"
             onerror="this.parentNode.innerHTML='<div class=\\'camera-placeholder\\'><i class=\\'fa-solid fa-video-slash\\'></i><p>Không lấy được luồng camera từ backend.</p></div>';">`;
             
    // Đánh dấu biến cameraInterval để biết camera đang bật (dùng chung logic tắt bật)
    cameraInterval = 'STREAMING';
    btn.innerHTML = '<i class="fa-solid fa-pause"></i> Tắt Camera';
}

$('btn-toggle-camera').addEventListener('click', toggleCamera);

// ============================================================
// Nhận diện & điểm danh (backend) — điều khiển từ web
// ============================================================
const recogStatusEl = $('recognizer-status');
const btnRecognizer = $('btn-toggle-recognizer');
let recognizerOn = false;
let recogPollTimer;

async function fetchStatus() {
    if (!BACKEND_URL) return;
    try {
        const res = await fetch(joinUrl(BACKEND_URL, '/api/status'));
        const st = await res.json();
        
        backendBadge.className = 'status-badge connected';
        backendBadge.innerHTML = '<i class="fa-solid fa-server"></i> Backend online';
        
        setRecognizerBadge(st.recognizer.running, st.recognizer.message);
        
        // Cập nhật giá trị camera select nếu có
        const camSelect = $('camera-source-select');
        if (camSelect && st.camera_source !== undefined) {
            camSelect.value = st.camera_source;
        }

    } catch (e) {
        backendBadge.className = 'status-badge disconnected';
        backendBadge.innerHTML = '<i class="fa-solid fa-server"></i> Backend offline';
    }
}

// ----------------------------------------------------------------------
// Lưu URL và Đổi Camera
// ----------------------------------------------------------------------
$('btn-save-backend').addEventListener('click', () => {
    const url = $('backend-url').value.trim();
    localStorage.setItem(BACKEND_KEY, url);
    BACKEND_URL = url;
    alert('Đã lưu URL! Đang kết nối lại...');
    initApp();
});

const btnSetCamera = $('btn-set-camera');
if (btnSetCamera) {
    btnSetCamera.addEventListener('click', async () => {
        if (!BACKEND_URL) {
            alert('Vui lòng cấu hình Backend URL trước.');
            return;
        }
        const source = $('camera-source-select').value;
        try {
            const res = await fetch(joinUrl(BACKEND_URL, '/api/camera'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ source: parseInt(source) }),
            });
            const data = await res.json();
            if (data.ok) {
                alert(data.message);
                // Khởi động lại luồng video nếu đang ở tab camera
                if (cameraInterval) {
                    toggleCamera(); // Tắt
                    setTimeout(toggleCamera, 1500); // Bật lại sau 1.5s
                }
            } else {
                alert('Lỗi: ' + data.error);
            }
        } catch (e) {
            alert('Không kết nối được với Backend: ' + e.message);
        }
    });
}

function setRecognizerBadge(running, message) {
    recognizerOn = running;
    if (running) {
        recogStatusEl.className = 'status-badge connected';
        recogStatusEl.innerHTML = '<i class="fa-solid fa-robot"></i> Nhận diện: bật';
    } else {
        recogStatusEl.className = 'status-badge disconnected';
        recogStatusEl.innerHTML = '<i class="fa-solid fa-robot"></i> Nhận diện: tắt';
    }
    btnRecognizer.innerHTML = running
        ? '<i class="fa-solid fa-circle-stop"></i> Dừng Nhận Diện'
        : '<i class="fa-solid fa-face-smile"></i> Bật Nhận Diện';
}

async function pollRecognizerStatus() {
    if (!BACKEND_URL) return;
    try {
        const res = await fetch(joinUrl(BACKEND_URL, '/api/recognizer/status'));
        const st = await res.json();
        setRecognizerBadge(st.running, st.message);
    } catch (e) {
        console.error('Poll recognizer status error:', e);
    }
}

btnRecognizer.addEventListener('click', async () => {
    if (!BACKEND_URL) {
        alert('Vui lòng cấu hình Backend URL trong tab Cấu Hình.');
        return;
    }
    const action = recognizerOn ? 'stop' : 'start';
    try {
        const res = await fetch(joinUrl(BACKEND_URL, '/api/recognizer'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action }),
        });
        const data = await res.json();
        if (!data.ok) {
            alert(data.error || 'Lỗi khi đổi trạng thái nhận diện.');
            return;
        }
        await pollRecognizerStatus();
    } catch (e) {
        alert('Lỗi khi gọi backend: ' + e.message);
    }
});

// Mỗi lần vào tab camera, poll trạng thái
let lastCamTab = 0;
function refreshRecognizer() {
    if (Date.now() - lastCamTab > 3000) {
        lastCamTab = Date.now();
        pollRecognizerStatus();
    }
}
document.querySelector('[data-tab="camera"]').addEventListener('click', refreshRecognizer);

// ============================================================
// Đăng ký nhân viên mới (train từ camera backend)
// ============================================================
let regPollTimer;

function setRegStatus(className, html) {
    const el = $('reg-status');
    el.className = 'reg-status ' + className;
    el.innerHTML = html;
}

function showProgress(count, max) {
    $('reg-progress-bar-wrap').classList.remove('hidden');
    const pct = max > 0 ? Math.min(100, Math.round((count / max) * 100)) : 0;
    $('reg-progress-bar').style.width = pct + '%';
    $('reg-count').textContent = `Đã thu thập ${count}/${max} mẫu khuôn mặt`;
}

$('btn-register').addEventListener('click', async () => {
    if (!BACKEND_URL) {
        alert('Vui lòng cấu hình Backend URL trong tab Cấu Hình trước.');
        return;
    }
    const name = $('reg-name').value.trim();
    const id = $('reg-id').value.trim();
    if (!name || !id) {
        alert('Vui lòng nhập đầy đủ Họ tên và MSSV.');
        return;
    }

    try {
        const res = await fetch(joinUrl(BACKEND_URL, '/api/register'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, student_id: id, samples: 30 }),
        });
        const data = await res.json();
        if (!data.ok) {
            alert(data.error || 'Không bắt đầu được đăng ký.');
            return;
        }
    } catch (e) {
        alert('Lỗi khi gọi backend: ' + e.message);
        return;
    }

    setRegStatus('active', `
        <i class="fa-solid fa-spinner fa-spin"></i>
        <p>Đăng ký đang chạy... Hãy đứng trước camera, nhìn thẳng, một người.</p>
    `);
    showProgress(0, 30);
    $('btn-register').disabled = true;

    // Hiển thị camera ngay lập tức khi bấm nút
    const camViewer = $('reg-camera-viewer');
    if (camViewer) {
        camViewer.innerHTML = `<img src="${joinUrl(BACKEND_URL, '/video_feed')}?t=${Date.now()}" style="width:100%; border-radius:8px;">`;
    }

    clearInterval(regPollTimer);
    regPollTimer = setInterval(pollRegisterStatus, 1000);
});

function stopRegPolling() {
    clearInterval(regPollTimer);
    $('btn-register').disabled = false;
}

async function pollRegisterStatus() {
    if (!BACKEND_URL) return;
    try {
        const res = await fetch(joinUrl(BACKEND_URL, '/api/register/status'));
        const st = await res.json();

        showProgress(st.count, st.max);

        // Inject camera stream
        const camViewer = $('reg-camera-viewer');
        if (!st.done && camViewer.innerHTML.indexOf('img') === -1) {
            camViewer.innerHTML = `<img src="${joinUrl(BACKEND_URL, '/video_feed')}?t=${Date.now()}" style="width:100%; border-radius:8px;">`;
        }

        if (st.done) {
            stopRegPolling();
            // Đã ẩn tính năng xóa camera: camViewer.innerHTML = ''; 
            if (st.success) {
                setRegStatus('success', `
                    <i class="fa-solid fa-circle-check"></i>
                    <p>${escapeHtml(st.message)}</p>
                    <p class="hint">Nhân viên đã được thêm và có thể nhận diện ngay.</p>
                `);
                $('reg-name').value = '';
                $('reg-id').value = '';
                $('reg-progress-bar-wrap').classList.add('hidden');
                $('reg-count').textContent = '';
                loadEmployees();
            } else {
                setRegStatus('error', `
                    <i class="fa-solid fa-triangle-exclamation"></i>
                    <p>${escapeHtml(st.message)}</p>
                `);
            }
        }
    } catch (e) {
        console.error('Poll register status error:', e);
    }
}

// ============================================================
// Tab navigation
// ============================================================
document.querySelectorAll('.tab-btn').forEach((btn) => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach((b) => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach((t) => t.classList.remove('active'));
        btn.classList.add('active');
        const tabName = btn.dataset.tab;
        const targetId = 'tab-' + tabName;
        $(targetId).classList.add('active');
        
        // Tự động bật camera soi gương nếu người dùng chuyển sang tab Đăng Ký
        const camViewer = $('reg-camera-viewer');
        if (targetId === 'tab-register' && BACKEND_URL) {
            if (camViewer && camViewer.innerHTML.indexOf('img') === -1) {
                camViewer.innerHTML = `<img src="${joinUrl(BACKEND_URL, '/video_feed')}?t=${Date.now()}" style="width:100%; border-radius:8px;">`;
            }
        } else if (camViewer) {
            camViewer.innerHTML = ''; // Tắt camera khi sang tab khác cho nhẹ máy
        }
    });
});

// ============================================================
// Settings (Backend URL)
// ============================================================
$('btn-save-backend').addEventListener('click', () => {
    BACKEND_URL = $('backend-url').value.trim().replace(/\/+$/, '');
    localStorage.setItem(BACKEND_KEY, BACKEND_URL);
    loadBackendData();
});

// ============================================================
// Tải backend lịch sử lúc khởi động
// ============================================================
$('backend-url').value = BACKEND_URL;
loadBackendData();

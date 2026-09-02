#include <WiFi.h>
#include <PubSubClient.h>
#include <LiquidCrystal_I2C.h>
#include <ArduinoJson.h>
#include <WiFiManager.h> // Thêm thư viện WiFiManager

// ============================================================
// Cấu hình WiFi (Đã chuyển sang WiFiManager, không cần hardcode)
// ============================================================

// ============================================================
// Cấu hình MQTT
// ============================================================
const char* mqtt_server = "broker.emqx.io";
const int mqtt_port = 1883;

const char* topic_result   = "iot_camera/attendance/result";
const char* topic_alert    = "iot_camera/attendance/alert";
const char* topic_control  = "iot_camera/attendance/control";
const char* topic_status   = "iot_camera/attendance/status";

WiFiClient espClient;
PubSubClient client(espClient);

// ============================================================
// Cấu hình Phần Cứng
// ============================================================
LiquidCrystal_I2C lcd(0x27, 16, 2);

const int BUZZER_PIN = 4;   // Còi báo điểm danh
const int LED_PIN = 5;      // Đèn LED báo người lạ (Đỏ)
const int LED_GREEN_PIN = 15; // Đèn LED điểm danh thành công (Xanh)
// ============================================================
// State machine không-blocking để LCD tự tắt, còi, cửa...
// Dùng millis() thay vì delay() tránh chặn client.loop()
// ============================================================
enum DisplayState { DISPLAY_NONE, DISPLAY_ATTEND, DISPLAY_ALERT, DISPLAY_RESET };
DisplayState displayState = DISPLAY_NONE;

unsigned long displayStartMs = 0;
const unsigned long DISPLAY_DURATION = 5000; // 5 giây hiển thị rồi xoá

bool buzzerHigh = false;
unsigned long buzzerToggleMs = 0;

bool ledHigh = false;
unsigned long ledToggleMs = 0;

bool ledGreenHigh = false;
unsigned long ledGreenToggleMs = 0;

// ============================================================
// Hàm tiện ích: hiển thị LCD có timeout
// ============================================================
void showLcd(const char* line1, const char* line2, DisplayState state) {
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print(line1);
  lcd.setCursor(0, 1);
  lcd.print(line2);
  displayState = state;
  displayStartMs = millis();
}

// Rút gọn chuỗi xuống maxLen ký tự (để vừa LCD 16 cột)
String truncateStr(const char* s, int maxLen) {
  String out(s);
  if (out.length() > maxLen) out = out.substring(0, maxLen);
  return out;
}

// ============================================================
// MQTT callback
// ============================================================
void callback(char* topic, byte* payload, unsigned int length) {
  String msg = "";
  for (unsigned int i = 0; i < length; i++) msg += (char)payload[i];
  String t = String(topic);

  JsonDocument doc;
  DeserializationError error = deserializeJson(doc, msg);
  if (error) {
    Serial.print("JSON parse failed: ");
    Serial.println(error.f_str());
    return;
  }

  if (t == String(topic_result)) {
    const char* name = doc["name"] | "Nguoi dung";
    String shortName = truncateStr(name, 16);

    showLcd("Xin chao:", shortName.c_str(), DISPLAY_ATTEND);

    // Buzzer kêu 1 tiếng bíp ngắn (100ms)
    digitalWrite(BUZZER_PIN, HIGH);
    buzzerHigh = true;
    buzzerToggleMs = millis() + 100;
    
    // Đèn LED Xanh bật sáng 2 giây báo hiệu thành công
    digitalWrite(LED_GREEN_PIN, HIGH);
    ledGreenHigh = true;
    ledGreenToggleMs = millis() + 2000;

    Serial.print("[LCD] Dien danh: ");
    Serial.println(msg);
  }
  else if (t == String(topic_alert)) {
    const char* status = doc["status"] | "";
    if (strcmp(status, "stranger") == 0) {
      showLcd("! CANH BAO !", "Phat Hien Nguoi La", DISPLAY_ALERT);
      // Đèn LED Đỏ sáng liên tục trong 5 giây
      digitalWrite(LED_PIN, HIGH);
      ledHigh = true;
      ledToggleMs = millis() + 5000;
      Serial.println("[LCD] CANH BAO NGUOI LA - BAT LED DO");
    }
  }
  else if (t == String(topic_control)) {
    const char* action = doc["action"] | "";
    if (strcmp(action, "reset_buzzer") == 0) {
      digitalWrite(BUZZER_PIN, LOW);
      buzzerHigh = false;
      showLcd("Bao dong da tat", "He thong binh thuong", DISPLAY_RESET);
      Serial.println("[LCD] Tat coi bao dong");
    }
  }
}

// ============================================================
// WiFi (Sử dụng WiFiManager để kết nối tự động/phát WiFi)
// ============================================================
void setup_wifi() {
  Serial.println();
  Serial.println("Dang khoi dong WiFiManager...");

  // Hiển thị lên LCD hướng dẫn người dùng
  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("Dang ket noi...");
  lcd.setCursor(0, 1);
  lcd.print("Hoac phat WiFi");

  // Khởi tạo WiFiManager
  WiFiManager wm;
  
  // Hàm này tự động được gọi khi ESP32 không tìm thấy mạng và bật chế độ phát WiFi
  wm.setAPCallback([](WiFiManager *myWiFiManager) {
    Serial.println("\n----------------------------------------------");
    Serial.println(">>> DA MAT KET NOI MANG CU <<<");
    Serial.println(">>> CHUYEN SANG CHE DO PHAT WIFI (ACCESS POINT) <<<");
    Serial.print("1. Dung dien thoai/laptop ket noi vao WiFi ten: ");
    Serial.println(myWiFiManager->getConfigPortalSSID());
    Serial.println("2. Trang cai dat se tu dong hien len (hoac vao IP: 192.168.4.1)");
    Serial.println("3. Chon WiFi nha ban va nhap Mat khau de ket noi lai!");
    Serial.println("----------------------------------------------\n");
    
    // Báo lên LCD để người dùng biết phải làm gì
    lcd.clear();
    lcd.setCursor(0, 0);
    lcd.print("Hay ket noi vao:");
    lcd.setCursor(0, 1);
    lcd.print("ESP32_IoT_Camera");
  });

  // Nếu không kết nối được WiFi cũ, nó sẽ tạo mạng tên ESP32_IoT_Camera
  // Hàm này sẽ chặn (block) cho đến khi người dùng nhập đúng WiFi qua điện thoại
  bool res = wm.autoConnect("ESP32_IoT_Camera");

  if (!res) {
    Serial.println("Ket noi that bai! ESP se tu dong khoi dong lai.");
    lcd.clear();
    lcd.print("Loi ket noi!");
    delay(3000);
    ESP.restart();
  }

  // Nếu chạy đến đây tức là đã kết nối WiFi thành công
  Serial.println("");
  Serial.print("WiFi da ket noi. IP: ");
  Serial.println(WiFi.localIP());

  lcd.clear();
  lcd.setCursor(0, 0);
  lcd.print("WiFi OK");
  lcd.setCursor(0, 1);
  lcd.print(WiFi.localIP().toString().c_str());
  delay(2000);
}

// ============================================================
// MQTT reconnect + publish trạng thái online
// ============================================================
void reconnect() {
  while (!client.connected()) {
    Serial.print("Ket noi MQTT Broker...");
    String clientId = "ESP32Client-";
    clientId += String(random(0xffff), HEX);

    if (client.connect(clientId.c_str())) {
      Serial.println(" Da ket noi!");
      client.subscribe(topic_result);
      client.subscribe(topic_alert);
      client.subscribe(topic_control);

      // Thông báo trạng thái online lên broker để backend/web biết
      JsonDocument st;
      st["device"] = "esp32";
      st["state"] = "online";
      st["ip"] = WiFi.localIP().toString().c_str();
      char buf[128];
      serializeJson(st, buf, sizeof(buf));
      client.publish(topic_status, buf);
    } else {
      Serial.print(" That bai, ma loi: ");
      Serial.print(client.state());
      Serial.println(" Thu lai sau 5s");
      delay(5000);
    }
  }
}

// ============================================================
// Xử lý phi-blocking trong loop
// ============================================================
void updateLcdTimer() {
  // Tự xoá màn hình sau DISPLAY_DURATION
  if (displayState != DISPLAY_NONE) {
    if (millis() - displayStartMs >= DISPLAY_DURATION) {
      lcd.clear();
      displayState = DISPLAY_NONE;
    }
  }
}

void updateHardware() {
  // Tắt buzzer sau khi hết thời gian kêu ngắn
  if (buzzerHigh && millis() >= buzzerToggleMs) {
    digitalWrite(BUZZER_PIN, LOW);
    buzzerHigh = false;
  }
  // Tắt LED đỏ sau khi hết thời gian cảnh báo
  if (ledHigh && millis() >= ledToggleMs) {
    digitalWrite(LED_PIN, LOW);
    ledHigh = false;
  }
  // Tắt LED xanh sau khi hết thời gian điểm danh
  if (ledGreenHigh && millis() >= ledGreenToggleMs) {
    digitalWrite(LED_GREEN_PIN, LOW);
    ledGreenHigh = false;
  }
}

// ============================================================
// Setup / Loop
// ============================================================
void setup() {
  Serial.begin(115200);

  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);

  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  
  pinMode(LED_GREEN_PIN, OUTPUT);
  digitalWrite(LED_GREEN_PIN, LOW);

  lcd.init();
  lcd.backlight();
  lcd.setCursor(0, 0);
  lcd.print("Khoi dong he");
  lcd.setCursor(0, 1);
  lcd.print("thong Diem Danh");

  setup_wifi();

  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  // Các tác vụ phi-blocking
  updateHardware();
  updateLcdTimer();

  delay(10);
}

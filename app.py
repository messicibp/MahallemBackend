import os
import firebase_admin
from firebase_admin import credentials, firestore, messaging
from flask import Flask, request, jsonify

# Firebase Admin SDK'sını başlat
# 'service-account.json' dosyasını Render'a daha sonra yükleyeceğiz.
cred = credentials.Certificate("service-account.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

# Flask web sunucusunu başlat
app = Flask(__name__)

@app.route("/")
def hello():
    return "Mahallem Bildirim Sunucusu Aktif!"

@app.route("/send-notification", methods=['POST'])
def send_notification():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Geçersiz istek"}), 400

    print(f"Bildirim isteği alındı: {data}")

    recipient_id = data.get('recipientId')
    title = data.get('title')
    body = data.get('body')

    if not all([recipient_id, title, body]):
        return jsonify({"error": "Eksik parametreler: recipientId, title, body gerekli"}), 400

    try:
        # Alıcının kullanıcı belgesini Firestore'dan al
        user_doc = db.collection('users').document(recipient_id).get()
        if not user_doc.exists:
            print(f"Alıcı bulunamadı: {recipient_id}")
            return jsonify({"error": "Alıcı bulunamadı"}), 404

        # Alıcının FCM token'ını al
        token = user_doc.to_dict().get('fcmToken')
        if not token:
            print(f"Alıcının token'ı yok: {recipient_id}")
            return jsonify({"error": "Alıcının token'ı yok"}), 404

        # Bildirim mesajını oluştur
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            token=token,
        )

        # Mesajı gönder
        response = messaging.send(message)
        print(f"Bildirim başarıyla gönderildi: {response}")
        return jsonify({"success": True, "message_id": response}), 200

    except Exception as e:
        print(f"Bildirim gönderilirken hata oluştu: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
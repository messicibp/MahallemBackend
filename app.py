import os
import firebase_admin
from firebase_admin import credentials, firestore, messaging
from flask import Flask, request, jsonify

# --- Kurulum Bölümü ---

# Firebase Admin SDK'sını, sunucuya yüklediğimiz anahtar dosyasıyla başlat.
# Bu dosyanın, app.py ile aynı dizinde olduğundan emin ol.
try:
    cred = credentials.Certificate("service-account.json")
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Firebase Admin SDK başarıyla başlatıldı.")
except Exception as e:
    print(f"Firebase Admin SDK başlatılırken KRİTİK HATA: {e}")
    db = None

# Flask web sunucusunu başlat.
app = Flask(__name__)


# --- Rota (Endpoint) Tanımlamaları ---

# Bu, sunucunun çalışıp çalışmadığını test etmek için bir "sağlık kontrolü" rotasıdır.
@app.route("/")
def hello():
    return "Mahallem Bildirim Sunucusu Aktif!"


# Asıl bildirim gönderme işini yapan ana rotamız.
@app.route("/send-notification", methods=['POST'])
def send_notification():
    # Veritabanı bağlantısı kurulamadıysa, hata döndür.
    if not db:
        return jsonify({"error": "Veritabanı bağlantısı yok"}), 500
        
    # Android uygulamasından gelen JSON verisini al.
    data = request.get_json()
    if not data:
        return jsonify({"error": "Geçersiz istek, JSON verisi eksik."}), 400

    print(f"Bildirim isteği alındı: {data}")

    # Gelen veriden gerekli parametreleri çıkar.
    recipient_id = data.get('recipientId')
    title = data.get('title')
    body = data.get('body')
    sender_id = data.get('senderId') # Mesajı gönderen kişinin ID'si

    # Gerekli parametrelerin hepsi var mı diye kontrol et.
    if not all([recipient_id, title, body, sender_id]):
        return jsonify({"error": "Eksik parametreler: recipientId, title, body, senderId gerekli."}), 400

    try:
        tokens_to_send = []
        
        # 1. SENARYO: Genel Sohbet Bildirimi
        if recipient_id == "all":
            print("Genel bildirim isteği alındı. Tüm kullanıcılara gönderilecek.")
            users_ref = db.collection('users')
            users_snapshot = users_ref.stream() # .stream() büyük koleksiyonlar için daha verimlidir.
            
            for user_doc in users_snapshot:
                user_data = user_doc.to_dict()
                # Kullanıcının token'ı varsa VE mesajı gönderen kendisi değilse, listeye ekle.
                if user_data.get('fcmToken') and user_doc.id != sender_id:
                    tokens_to_send.append(user_data.get('fcmToken'))
            print(f"Genel sohbet için {len(tokens_to_send)} adet token bulundu.")

        # 2. SENARYO: Özel Sohbet Bildirimi
        else:
            print(f"Özel bildirim isteği alındı. Alıcı: {recipient_id}")
            user_doc = db.collection('users').document(recipient_id).get()
            
            if not user_doc.exists:
                print(f"Alıcı bulunamadı: {recipient_id}")
                return jsonify({"error": "Alıcı kullanıcı bulunamadı."}), 404
            
            token = user_doc.to_dict().get('fcmToken')
            if token:
                tokens_to_send.append(token)
            
            print(f"Özel sohbet için token bulundu: {'Evet' if token else 'Hayır'}")


        # Bildirim gönderilecek kimse yoksa, işlemi sonlandır.
        if not tokens_to_send:
            print("Gönderilecek FCM token'ı bulunamadı.")
            return jsonify({"error": "Geçerli alıcı bulunamadı."}), 404

        # Çoklu hedefe bildirim göndermek için (liste tek elemanlı olsa bile çalışır).
        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            tokens=tokens_to_send,
        )

        # Mesajı Firebase'e gönder.
        response = messaging.send_multicast(message)
        
        print(f"Bildirim gönderme sonucu: {response.success_count} başarılı, {response.failure_count} başarısız.")
        
        if response.failure_count > 0:
            for i, resp in enumerate(response.responses):
                if not resp.success:
                    print(f"Hata detayı [{i}]: {resp.exception}")

        return jsonify({"success_count": response.success_count, "failure_count": response.failure_count}), 200

    except Exception as e:
        print(f"Bildirim gönderilirken kritik bir hata oluştu: {e}")
        return jsonify({"error": str(e)}), 500

# Bu bölüm, sunucunun Render.com'da doğru şekilde başlamasını sağlar.
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))

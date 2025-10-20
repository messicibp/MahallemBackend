@app.route("/send-notification", methods=['POST'])
def send_notification():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Geçersiz istek"}), 400

    print(f"Bildirim isteği alındı: {data}")

    recipient_id = data.get('recipientId')
    title = data.get('title')
    body = data.get('body')
    sender_id = data.get('senderId') # Yeni eklendi

    if not all([recipient_id, title, body]):
        return jsonify({"error": "Eksik parametreler"}), 400

    try:
        tokens = []
        if recipient_id == "all":
            # --- YENİ GENEL SOHBET MANTIĞI ---
            print("Genel bildirim isteği, herkese gönderilecek.")
            users_snapshot = db.collection('users').stream()
            for user_doc in users_snapshot:
                user_data = user_doc.to_dict()
                # Kullanıcının token'ı varsa ve mesajı gönderen kendisi değilse, listeye ekle
                if user_data.get('fcmToken') and user_doc.id != sender_id:
                    tokens.append(user_data.get('fcmToken'))
        else:
            # --- ESKİ ÖZEL SOHBET MANTIĞI ---
            print(f"Özel bildirim isteği, alıcı: {recipient_id}")
            user_doc = db.collection('users').document(recipient_id).get()
            if not user_doc.exists:
                return jsonify({"error": "Alıcı bulunamadı"}), 404
            
            token = user_doc.to_dict().get('fcmToken')
            if token:
                tokens.append(token)

        if not tokens:
            print("Gönderilecek token bulunamadı.")
            return jsonify({"error": "Gönderilecek token bulunamadı"}), 404

        # Çoklu token'a gönderme (multicast) için mesaj oluştur
        message = messaging.MulticastMessage(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            tokens=tokens,
        )

        response = messaging.send_multicast(message)
        print(f"{response.success_count} bildirim başarıyla gönderildi.")
        return jsonify({"success_count": response.success_count}), 200

    except Exception as e:
        print(f"Bildirim gönderilirken hata oluştu: {e}")
        return jsonify({"error": str(e)}), 500

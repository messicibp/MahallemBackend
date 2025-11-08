# app.py'nin en altına, diğer @app.route'ların yanına ekle

from firebase_admin import storage
import datetime

@app.route("/generate-upload-url", methods=['POST'])
def generate_upload_url():
    data = request.get_json()
    if not data or 'filename' not in data:
        return jsonify({"error": "Dosya adı eksik."}), 400

    filename = data['filename']
    
    try:
        # Firebase Storage'da dosyanın tam yolunu belirle
        bucket = storage.bucket("mahalletunacorum.firebasestorage.app") # Storage URL'nden kopyala
        blob = bucket.blob(f"videos/{filename}")

        # 15 dakika geçerli olacak, v4 imzalı bir URL oluştur
        signed_url = blob.generate_signed_url(
            version="v4",
            expiration=datetime.timedelta(minutes=15),
            method="PUT",
            content_type="video/mp4" # Yüklenecek dosyanın tipini belirt
        )

        print(f"İmzalı URL oluşturuldu: {filename}")
        return jsonify({"signedUrl": signed_url}), 200

    except Exception as e:
        print(f"İmzalı URL oluşturulurken hata: {e}")
        return jsonify({"error": str(e)}), 500

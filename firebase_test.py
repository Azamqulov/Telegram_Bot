import firebase_admin
from firebase_admin import credentials, firestore

# 1. Service account json faylni ulaymiz
cred = credentials.Certificate("service-account.json")  # Agar shu papkada bo‘lsa

# 2. Firebase ilovasini ishga tushuramiz
firebase_admin.initialize_app(cred)

# 3. Firestore clientni olamiz
db = firestore.client()

# 4. Test: Kurslar kolleksiyasini o‘qiymiz
print("📚 Kurslar ro'yxati:")
for doc in db.collection("courses").stream():
    print(f"- {doc.id}: {doc.to_dict()}")

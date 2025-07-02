import firebase_admin
from firebase_admin import credentials, firestore

# service-account.json birga bo‘lsa shuni ishlat
cred = credentials.Certificate("service-account.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

courses = [
    {
        "name": "Frontend",
        "duration_weeks": 10,
        "price": 300000,
    },
    {
        "name": "Python Dasturlash",
        "duration_weeks": 8,
        "price": 400000,
    },
    {
        "name": "Kompyuter Savodxonligi",
        "duration_weeks": 6,
        "price": 250000,
    },
    {
        "name": "Mobil Dasturlash (Flutter)",
        "duration_weeks": 12,
        "price": 500000,
    },
]

for course in courses:
    db.collection("courses").add(course)

print("✅ Kurslar muvaffaqiyatli yuklandi!")

import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
from io import StringIO

# Firebase başlat
if not firebase_admin._apps:
    cred = firebase_json = st.secrets["firebase_json"]
    cred_dict = json.load(StringIO(firebase_json))
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)
db = firestore.client()
    firebase_admin.initialize_app(cred)
db = firestore.client()

st.title("📦 Günlük Alımlar")


# Tüm alış kayıtlarını çek
docs = db.collection("purchases").stream()

for doc in docs:
    tarih = doc.id
    data = doc.to_dict()
    st.subheader(f"📅 {tarih}")

    if "items" in data:
        total = 0
        for item in data["items"]:
            st.write(f"- {item['product_id']} → {item['quantity']} adet → {item['total_price']}₺")
            total += item['total_price']
        st.write(f"**Toplam: {total}₺**")

    # Ödeme durumu
    if data.get("paid"):
        st.success("✅ Ödenmiş")
    else:
        if st.button(f" Ödendi olarak işaretle ({tarih})"):
            db.collection("purchases").document(tarih).update({"paid": True})
            st.experimental_rerun()

import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
from io import StringIO

# Firebase başlat
if not firebase_admin._apps:
    firebase_json = st.secrets["firebase_json"]
    cred_dict = json.load(StringIO(firebase_json))
    cred = credentials.Certificate(cred_dict)
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
        if st.button(f"💸 Ödendi olarak işaretle ({tarih})"):
            db.collection("purchases").document(tarih).update({"paid": True})
            st.rerun()





for product in products:
    pid = product.id
    pdata = product.to_dict()

    with st.expander(f"{pdata.get('name', 'Bilinmeyen')} - {pdata.get('price', 0)}₺"):
        new_name = st.text_input(f"Ad (ID: {pid})", value=pdata.get("name", ""), key=f"name_{pid}")
        new_price = st.number_input("Fiyat", value=pdata.get("price", 0.0), key=f"price_{pid}")
        new_category = st.text_input("Tür", value=pdata.get("category", ""), key=f"cat_{pid}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Güncelle", key=f"update_{pid}"):
                db.collection("products").document(pid).update({
                    "name": new_name,
                    "price": new_price,
                    "category": new_category
                })
                st.success("Güncellendi.")
                st.experimental_rerun()
        with col2:
            if st.button("🗑️ Sil", key=f"delete_{pid}"):
                db.collection("products").document(pid).delete()
                st.warning("Silindi.")
                st.rerun()

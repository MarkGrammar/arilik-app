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





st.title("Ürün Yönetimi")

# Ürün ekleme
with st.expander("add_product"):
    st.subheader("➕ Yeni Ürün Ekle")
    product_id = st.text_input("Ürün ID:")
    type = st.text_input("Ürün Türü")
    name = st.text_input("Ürün Adı:")
    unit_price = st.number_input("Birim Fiyat (₺)", min_value=0.0, step=0.1)
    submitted = st.form_submit_button("Ürünü Ekle")

    if submitted:
        if product_id and name:
            db.collection("products").document(product_id).set({
                "name": name,
                "unit_price": unit_price
                "category": category
            })
            st.success(f"{name} ({category}) eklendi.")
            st.rerun()
        else:
            st.error("Lütfen tüm alanları doldurun.")

# Ürünleri listele ve güncelle/sil
st.subheader("📋 Mevcut Ürünler")

products = db.collection("products").stream()

for product in products:
    pid = product.id
    pdata = product.to_dict()

    with st.expander(f"{pdata['name']} - {pdata['unit_price']}₺"):
        new_name = st.text_input(f"Ad (ID: {pid})", value=pdata["name"], key=f"name_{pid}")
        new_price = st.number_input(f"Fiyat", value=pdata["unit_price"], key=f"price_{pid}")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Güncelle", key=f"update_{pid}"):
                db.collection("products").document(pid).update({
                    "name": new_name,
                    "unit_price": new_price
                })
                st.success("Güncellendi.")
                st.experimental_rerun()
        with col2:
            if st.button("🗑️ Sil", key=f"delete_{pid}"):
                db.collection("products").document(pid).delete()
                st.warning("Silindi.")
                st.rerun()

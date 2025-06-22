import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import json
from io import StringIO
import datetime

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

# ➕ Ürün ekleme
with st.expander("➕ Yeni Ürün Ekle"):
    with st.form("urun_ekle_formu"):
        st.subheader("Yeni Ürün Ekle")

        product_id = st.text_input("Ürün ID:", key="id")
        name = st.text_input("Ürün Adı:", key="ad")
        price = st.number_input("Birim Fiyat (₺)", min_value=0.0, step=0.5, key="fiyat")
        category = st.text_input("Ürün Türü", key="kategori")

        submitted = st.form_submit_button("Ürünü Ekle")
        if submitted:
            db.collection("products").document(product_id).set({
                "name": name,
                "price": price,
                "category": category
            })
            st.success(f"{name} ({category}) eklendi.")
            st.rerun()

# 📋 Ürünleri listele ve güncelle/sil
st.subheader("📋 Mevcut Ürünler")

products = db.collection("products").stream()

for product in products:
    pid = product.id
    pdata = product.to_dict()

    pname = pdata.get("name", "Bilinmeyen")
    pprice = pdata.get("price", 0.0)
    pcat = pdata.get("category", "")

    with st.expander(f"{pname} - {pprice}₺"):
        new_name = st.text_input(f"Ad (ID: {pid})", value=pname, key=f"name_{pid}")
        new_price = st.number_input("Fiyat", value=pprice, key=f"price_{pid}")
        new_category = st.text_input("Tür", value=pcat, key=f"cat_{pid}")

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
                
                
                
                
                
                
st.title("🛒 Yeni Alışveriş Girişi")

# Tarih seçimi
tarih = st.date_input("Alışveriş Tarihi", value=datetime.date.today())
tarih_str = tarih.isoformat()

# Ürünleri firestore'dan al
urunler = db.collection("products").stream()
urun_listesi = {urun.id: urun.to_dict() for urun in urunler}

if not urun_listesi:
    st.warning("Henüz hiç ürün yok. Lütfen önce ürün ekleyin.")
else:
    with st.form("alisveris_formu"):
        st.subheader("Ürünler")

        secilen_urunler = []
        for pid, pdata in urun_listesi.items():
            miktar = st.number_input(f"{pdata['name']} ({pdata['price']}₺)", min_value=0.0, step=1.0, key=f"miktar_{pid}")
            if miktar > 0:
                secilen_urunler.append({
                    "product_id": pid,
                    "quantity": miktar,
                    "unit_price": pdata["price"],
                    "total_price": miktar * pdata["price"]
                })

        submitted = st.form_submit_button("Alışverişi Kaydet")
        if submitted:
            if secilen_urunler:
                db.collection("purchases").document(tarih_str).set({
                    "items": secilen_urunler,
                    "paid": False
                })
                st.success("Alışveriş kaydedildi!")
                st.rerun()
            else:
                st.warning("En az bir ürün miktarı girmelisiniz.")

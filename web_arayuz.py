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

        product_id = st.text_input("Ürün ID (benzersiz):", key="id")
        name = st.text_input("Ürün Adı:", key="ad")
        price = st.number_input("Birim Fiyat (₺)", min_value=0.0, step=0.5, key="fiyat")
        category = st.text_input("Ürün Türü (örnek: Ekmek, Temizlik...)", key="kategori")

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
                
                
                
                
                
                
st.header("Yeni Alışveriş Girişi")

# Tarih seçimi
tarih = st.date_input("Alışveriş Tarihi", value=datetime.date.today())
tarih_str = tarih.isoformat()

# Ürünleri çek
urunler = list(db.collection("products").stream())
urun_dict = {u.id: u.to_dict() for u in urunler}

# Alınan ürünler için liste
st.subheader("🧾 Alınan Ürünler")

urun_secimleri = []
for i in range(5):  # En fazla 5 ürün girişi
    st.markdown(f"**Ürün {i+1}**")
    cols = st.columns([3, 2, 2])
    with cols[0]:
        secilen_urun = st.selectbox(f"Ürün Seç", [""] + list(urun_dict.keys()), key=f"urun_{i}")
    if secilen_urun:
        with cols[1]:
            adet = st.number_input("Adet", min_value=0.0, step=0.5, key=f"adet_{i}")
        with cols[2]:
            fiyat = urun_dict[secilen_urun]["price"]
            toplam = fiyat * adet
            st.write(f"Toplam: {toplam:.2f}₺")
            urun_secimleri.append({
                "product_id": secilen_urun,
                "quantity": adet,
                "total_price": toplam
            })

# Kaydet
if st.button("💾 Alışverişi Kaydet"):
    if urun_secimleri:
        db.collection("purchases").document(tarih_str).set({
            "items": urun_secimleri,
            "paid": False
        })
        st.success(f"{tarih_str} alışverişi kaydedildi.")
        st.experimental_rerun()
    else:
        st.error("En az bir ürün seçmelisiniz.")

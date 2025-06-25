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

# 🔄 Ürün adlarını çek (ID → İsim)
product_docs = db.collection("products").stream()
product_dict = {
    doc.id: doc.to_dict().get("name", "Bilinmeyen Ürün")
    for doc in product_docs
}

# 📅 Tüm alışveriş kayıtlarını çek
docs = db.collection("purchases").stream()

total_unpaid = 0

for doc in docs:
    tarih = doc.id
    data = doc.to_dict()
    st.subheader(f"📅 {tarih}")

    if "items" in data:
        total = 0
        for item in data["items"]:
            product_id = item["product_id"]
            product_name = product_dict.get(product_id, product_id)
            miktar = item.get("quantity", "?")
            fiyat = item.get("total_price", "?")
            market = item.get("market", "?")
            st.write(f"- {product_name} ({market}) → {miktar} adet = {fiyat}₺")
            total += fiyat
        st.write(f"**Toplam: {total}₺**")
        if not data.get("paid"):
            total_unpaid += total

    if data.get("paid"):
        st.success("✅ Ödenmiş")
    else:
        if st.button(f"💸 Ödendi olarak işaretle ({tarih})"):
            db.collection("purchases").document(tarih).update({"paid": True})
            st.rerun()

st.markdown(f"Ödenmemiş Toplam: {total_unpaid}₺")

# ----------------- Ürün Yönetimi ---------------------
st.title("Ürün Yönetimi")

# ➕ Ürün ekleme
with st.expander("➕ Yeni Ürün Ekle"):
    with st.form("urun_ekle_formu"):
        st.subheader("Yeni Ürün Ekle")
        product_id = st.text_input("Ürün ID:", key="id")
        name = st.text_input("Ürün Adı:", key="ad")
        category = st.text_input("Genel Tür (örneğin: içecek)", key="kategori")
        subcategory = st.text_input("Alt Tür (örneğin: kola)", key="alt_tur")
        unit_type = st.selectbox("Miktar Türü", ["adet", "kg", "lt", "gr", "ml", "diğer"], key="birim")

        submitted = st.form_submit_button("Ürünü Ekle")
        if submitted:
            db.collection("products").document(product_id).set({
                "name": name,
                "category": category,
                "subcategory": subcategory,
                "unit": unit_type
            })
            st.success(f"{name} eklendi.")
            st.rerun()

# 📋 Ürünleri listele ve güncelle/sil
st.subheader("📋 Mevcut Ürünler")

products = db.collection("products").stream()
for product in products:
    pid = product.id
    pdata = product.to_dict()

    pname = pdata.get("name", "Bilinmeyen")
    pcat = pdata.get("category", "")
    psub = pdata.get("subcategory", "")
    punit = pdata.get("unit", "adet")

    with st.expander(f"{pname}"):
        new_name = st.text_input(f"Ad (ID: {pid})", value=pname, key=f"name_{pid}")
        new_category = st.text_input("Tür", value=pcat, key=f"cat_{pid}")
        new_subcat = st.text_input("Alt Tür", value=psub, key=f"subcat_{pid}")
        new_unit = st.selectbox("Miktar Türü", ["adet", "kg", "lt", "gr", "ml", "diğer"], index=0, key=f"unit_{pid}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Güncelle", key=f"update_{pid}"):
                db.collection("products").document(pid).update({
                    "name": new_name,
                    "category": new_category,
                    "subcategory": new_subcat,
                    "unit": new_unit
                })
                st.success("Güncellendi.")
                st.rerun()
        with col2:
            if st.button("🗑️ Sil", key=f"delete_{pid}"):
                db.collection("products").document(pid).delete()
                st.warning("Silindi.")
                st.rerun()

# ----------------- Alışveriş Girişi ---------------------
st.title("🛒 Yeni Alışveriş Girişi")

tarih = st.date_input("Alışveriş Tarihi", value=datetime.date.today())
tarih_str = tarih.isoformat()

urunler = db.collection("products").stream()
urun_listesi = {urun.id: urun.to_dict() for urun in urunler}

market_listesi = ["a101", "bim", "çağdaş", "gimatgross", "citygross", "ofisgross", "aytemiz", "opet", "petrol ofisi", "diğer"]
secilen_urunler = []

with st.form("alisveris_formu"):
    st.subheader("Ürünleri Seç")
    for pid, pdata in urun_listesi.items():
        urun_adı = pdata.get("name", "Bilinmeyen Ürün")

        with st.expander(f"{urun_adı}"):
            miktar = st.text_input(f"Miktar ({pdata.get('unit', 'adet')})", key=f"miktar_{pid}")
            fiyat = st.text_input("Toplam Fiyat (₺)", key=f"fiyat_{pid}")
            market = st.selectbox("Market", market_listesi, key=f"market_{pid}")

            if miktar and fiyat:
                try:
                    miktar_float = float(miktar)
                    fiyat_float = float(fiyat)
                    secilen_urunler.append({
                        "product_id": pid,
                        "quantity": miktar_float,
                        "total_price": fiyat_float,
                        "market": market
                    })
                except (TypeError, ValueError):
                    st.error(f"{urun_adı} için geçersiz miktar ya da fiyat.")

    submitted = st.form_submit_button("Alışverişi Kaydet")
    if submitted:
        if secilen_urunler:
            ref = db.collection("purchases").document(tarih_str)
            onceki = ref.get().to_dict()
            if onceki and "items" in onceki:
                secilen_urunler = onceki["items"] + secilen_urunler

            ref.set({
                "items": secilen_urunler,
                "paid": False
            })
            st.success("Alışveriş kaydedildi!")
            st.rerun()
        else:
            st.warning("En az bir ürün seçmelisiniz.")

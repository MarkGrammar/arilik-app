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

# 🔄 Tüm ürünlerin isim sözlüğünü al (ID → İsim)
product_docs = db.collection("products").stream()
product_dict = {
    doc.id: doc.to_dict().get("name", "Bilinmeyen Ürün")
    for doc in product_docs
}

# 📅 Tüm alışveriş kayıtlarını çek
docs = db.collection("purchases").stream()

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
            fiyat = item.get("price", "?")
            market = item.get("market", "?")
            try:
                miktar = float(miktar)
                fiyat = float(fiyat)
                toplam = miktar * fiyat
            except (TypeError, ValueError):
                st.error(f"{urun_adı} için geçersiz miktar ya da fiyat.")
                continue  # bu ürün atlanır, diğerleri işlenir
            st.write(f"- {product_name} → {miktar} × {fiyat}₺ → {toplam}₺ ({market})")
            total += toplam
        st.write(f"**Toplam: {total}₺**")

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
        category = st.text_input("Genel Tür (örn. Yiyecek, İçecek, Yakıt)", key="kategori")
        subcategory = st.text_input("Spesifik Tür (örn. Kola, Ayran, Ekmek)", key="subcat")
        unit_type = st.text_input("Miktar Türü (örn. adet, kg, lt)", key="unit")

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

# 📋 Ürünleri listele
st.subheader("📋 Mevcut Ürünler")
products = db.collection("products").stream()
for product in products:
    pid = product.id
    pdata = product.to_dict()

    pname = pdata.get("name", "Bilinmeyen")
    pcat = pdata.get("category", "")
    psubcat = pdata.get("subcategory", "")
    punit = pdata.get("unit", "")

    with st.expander(f"{pname} [{pcat}/{psubcat}] - {punit}"):
        new_name = st.text_input(f"Ad (ID: {pid})", value=pname, key=f"name_{pid}")
        new_category = st.text_input("Tür", value=pcat, key=f"cat_{pid}")
        new_subcategory = st.text_input("Alt Tür", value=psubcat, key=f"subcat_{pid}")
        new_unit = st.text_input("Miktar Türü", value=punit, key=f"unit_{pid}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Güncelle", key=f"update_{pid}"):
                db.collection("products").document(pid).update({
                    "name": new_name,
                    "category": new_category,
                    "subcategory": new_subcategory,
                    "unit": new_unit
                })
                st.success("Güncellendi.")
                st.experimental_rerun()
        with col2:
            if st.button("🗑️ Sil", key=f"delete_{pid}"):
                db.collection("products").document(pid).delete()
                st.warning("Silindi.")
                st.rerun()


st.title("🛒 Yeni Alışveriş Girişi")
tarih = st.date_input("Alışveriş Tarihi", value=datetime.date.today())
tarih_str = tarih.isoformat()

urunler = db.collection("products").stream()
urun_listesi = {urun.id: urun.to_dict() for urun in urunler}

if not urun_listesi:
    st.warning("Henüz hiç ürün yok. Lütfen önce ürün ekleyin.")
else:
    st.subheader("Ürün Seçimi")
    secilen_urunler = []
    marketler = ["A101", "BİM", "Çağdaş", "GimatGross", "CityGross", "OfisGross", "Aytemiz", "Opet", "Petrol Ofisi", "Diğer"]

    for pid, pdata in urun_listesi.items():
        with st.expander(f"{pdata['name']} [{pdata.get('category', '')} / {pdata.get('subcategory', '')}]"):
            miktar = st.number_input("Miktar", min_value=0.0, step=1.0, key=f"miktar_{pid}")
            fiyat = st.number_input("Fiyat (₺)", min_value=0.0, step=0.5, key=f"fiyat_{pid}")
            market = st.selectbox("Market", marketler, key=f"market_{pid}")

            if miktar > 0 and fiyat > 0:
                secilen_urunler.append({
                    "product_id": pid,
                    "quantity": miktar,
                    "price": fiyat,
                    "market": market
                })

    if st.button("💾 Alışverişi Kaydet"):
        if secilen_urunler:
            eski = db.collection("purchases").document(tarih_str).get()
            if eski.exists:
                onceki = eski.to_dict().get("items", [])
                yeni_items = onceki + secilen_urunler
            else:
                yeni_items = secilen_urunler

            db.collection("purchases").document(tarih_str).set({
                "items": yeni_items,
                "paid": False
            })
            st.success("Alışveriş kaydedildi!")
            st.rerun()
        else:
            st.warning("Lütfen en az bir ürün için miktar ve fiyat giriniz.")

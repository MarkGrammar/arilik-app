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
            st.write(f"- {product_name} → {item['quantity']} {item.get('unit', '')} → {item['total_price']}₺")
            total += item["total_price"]
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
        category = st.text_input("Genel Tür (örnek: Yiyecek, Temizlik...)", key="kategori")
        subcategory = st.text_input("Alt Tür (örnek: Kola, Ekmek...)", key="alt_tur")
        unit = st.text_input("Miktar Birimi (örnek: adet, kg, lt)", key="birim")

        submitted = st.form_submit_button("Ürünü Ekle")
        if submitted:
            db.collection("products").document(product_id).set({
                "name": name,
                "category": category,
                "subcategory": subcategory,
                "unit": unit
            })
            st.success(f"{name} ({category} - {subcategory}) eklendi.")
            st.rerun()

# 📋 Ürünleri listele ve güncelle/sil
st.subheader("📋 Mevcut Ürünler")

products = db.collection("products").stream()

for product in products:
    pid = product.id
    pdata = product.to_dict()

    pname = pdata.get("name", "Bilinmeyen")
    pcat = pdata.get("category", "")
    psubcat = pdata.get("subcategory", "")
    punit = pdata.get("unit", "")

    with st.expander(f"{pname} ({pcat} - {psubcat})"):
        new_name = st.text_input(f"Ad (ID: {pid})", value=pname, key=f"name_{pid}")
        new_category = st.text_input("Tür", value=pcat, key=f"cat_{pid}")
        new_subcategory = st.text_input("Alt Tür", value=psubcat, key=f"subcat_{pid}")
        new_unit = st.text_input("Birim", value=punit, key=f"unit_{pid}")

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
            miktar = st.number_input(f"{pdata['name']} ({pdata.get('unit', '')})", min_value=0.0, step=1.0, key=f"miktar_{pid}")
            fiyat = st.number_input(f"Fiyat (₺) - {pdata['name']}", min_value=0.0, step=0.5, key=f"fiyat_{pid}")
            if miktar > 0 and fiyat > 0:
                secilen_urunler.append({
                    "product_id": pid,
                    "quantity": miktar,
                    "unit": pdata.get("unit", ""),
                    "unit_price": fiyat,
                    "total_price": miktar * fiyat
                })

        submitted = st.form_submit_button("Alışverişi Kaydet")
        if submitted:
            if secilen_urunler:
                mevcut_veri = db.collection("purchases").document(tarih_str).get()
                onceki_items = mevcut_veri.to_dict().get("items", []) if mevcut_veri.exists else []
                yeni_items = onceki_items + secilen_urunler

                db.collection("purchases").document(tarih_str).set({
                    "items": yeni_items,
                    "paid": False
                })
                st.success("Alışveriş kaydedildi!")
                st.rerun()
            else:
                st.warning("En az bir ürün ve fiyat girmelisiniz.")

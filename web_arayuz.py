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

# Ürün ID → İsim sözlüğü
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
            pid = item["product_id"]
            pname = product_dict.get(pid, pid)
            miktar = item["quantity"]
            fiyat = item["unit_price"]
            market = item.get("market", "Bilinmiyor")
            toplam = item["total_price"]
            st.write(f"- {pname} → {miktar} → {fiyat}₺ → {market} → {toplam}₺")
            total += toplam
        st.write(f"**Toplam: {total}₺**")

    if data.get("paid"):
        st.success("✅ Ödenmiş")
    else:
        if st.button(f"💸 Ödendi olarak işaretle ({tarih})"):
            db.collection("purchases").document(tarih).update({"paid": True})
            st.rerun()

# ----------------------
st.title("📦 Ürün Yönetimi")

with st.expander("➕ Yeni Ürün Ekle"):
    with st.form("urun_ekle_formu"):
        st.subheader("Yeni Ürün Ekle")
        pid = st.text_input("Ürün ID")
        name = st.text_input("Ürün Adı")
        general_type = st.text_input("Genel Tür (örneğin: içecek, yiyecek, yakıt)")
        specific_type = st.text_input("Spesifik Tür (örneğin: ayran, ekmek, benzin)")
        unit_type = st.selectbox("Miktar Birimi", ["adet", "kg", "lt", "ml", "g", "paket", "kutu"])

        submitted = st.form_submit_button("Ürünü Ekle")
        if submitted:
            db.collection("products").document(pid).set({
                "name": name,
                "general_type": general_type,
                "specific_type": specific_type,
                "unit_type": unit_type
            })
            st.success("Ürün eklendi.")
            st.rerun()

st.subheader("📋 Mevcut Ürünler")

products = db.collection("products").stream()

for product in products:
    pid = product.id
    pdata = product.to_dict()

    with st.expander(f"{pdata.get('name', 'Bilinmeyen')} ({pdata.get('unit_type', '')})"):
        new_name = st.text_input("Ad", value=pdata.get("name", ""), key=f"name_{pid}")
        new_general = st.text_input("Genel Tür", value=pdata.get("general_type", ""), key=f"gen_{pid}")
        new_specific = st.text_input("Spesifik Tür", value=pdata.get("specific_type", ""), key=f"spec_{pid}")
        new_unit = st.selectbox("Miktar", ["adet", "kg", "lt", "ml", "g", "paket", "kutu"], index=0, key=f"unit_{pid}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Güncelle", key=f"update_{pid}"):
                db.collection("products").document(pid).update({
                    "name": new_name,
                    "general_type": new_general,
                    "specific_type": new_specific,
                    "unit_type": new_unit
                })
                st.success("Güncellendi.")
                st.rerun()
        with col2:
            if st.button("🗑️ Sil", key=f"delete_{pid}"):
                db.collection("products").document(pid).delete()
                st.warning("Silindi.")
                st.rerun()

# ----------------------
st.title("🛒 Yeni Alışveriş Girişi")

tarih = st.date_input("Alışveriş Tarihi", value=datetime.date.today())
tarih_str = tarih.isoformat()

urunler = db.collection("products").stream()
urun_dict = {urun.id: urun.to_dict() for urun in urunler}

if not urun_dict:
    st.warning("Henüz ürün yok.")
else:
    with st.form("alisveris_formu"):
        st.subheader("Ürünler")

        girilen_urunler = []
        for pid, pdata in urun_dict.items():
            miktar = st.number_input(f"{pdata['name']} - Miktar ({pdata.get('unit_type', '')})", min_value=0.0, step=1.0, key=f"qty_{pid}")
            fiyat = st.number_input(f"{pdata['name']} - Fiyat (₺)", min_value=0.0, step=0.5, key=f"price_{pid}")
            market = st.selectbox(f"{pdata['name']} - Market", ["a101", "bim", "çağdaş", "gimatgross", "citygross", "ofisgross", "aytemiz", "opet", "petrol ofisi", "diğer"], key=f"market_{pid}")
            if miktar > 0 and fiyat > 0:
                girilen_urunler.append({
                    "product_id": pid,
                    "quantity": miktar,
                    "unit_price": fiyat,
                    "market": market,
                    "total_price": miktar * fiyat
                })

        if st.form_submit_button("Kaydet"):
            if girilen_urunler:
                ref = db.collection("purchases").document(tarih_str)
                onceki = ref.get().to_dict() or {}
                eski_items = onceki.get("items", [])
                yeni_items = eski_items + girilen_urunler
                ref.set({
                    "items": yeni_items,
                    "paid": False
                })
                st.success("Alışveriş kaydedildi.")
                st.rerun()
            else:
                st.warning("Ürün miktarı ve fiyatı girilmeli.")

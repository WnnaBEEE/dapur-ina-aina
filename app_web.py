import streamlit as st
import mysql.connector
from mysql.connector import Error
import pandas as pd
from datetime import datetime, date

# 1. Streamlit Page Configuration
st.set_page_config(
    page_title="Restoran Dapur Ina Aina",
    page_icon="🍽️",
    layout="wide"
)

# 2. Database Connection using st.secrets
def get_connection():
    try:
        return mysql.connector.connect(
            host=st.secrets["mysql"]["host"],
            port=int(st.secrets["mysql"]["port"]),
            user=st.secrets["mysql"]["user"],
            password=st.secrets["mysql"]["password"],
            database=st.secrets["mysql"]["database"],
            connect_timeout=10
        )
    except Error as e:
        st.error(f"❌ Database Connection Error: {e}")
        return None

# 3. Session State Initialization
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'role' not in st.session_state:
    st.session_state.role = None
if 'username' not in st.session_state:
    st.session_state.username = None
if 'keranjang' not in st.session_state:
    st.session_state.keranjang = {}

# 4. Header & Top Right Login/Logout Section
head_col1, head_col2 = st.columns([5, 1.5])

with head_col1:
    st.title("🍽️ Restoran Dapur Ina Aina")

with head_col2:
    st.write("")  # Vertical spacing alignment
    if st.session_state.logged_in:
        st.markdown(f"👤 **{st.session_state.username}** (`{st.session_state.role}`)")
        if st.button("🚪 Logout", key="btn_logout_top", type="secondary", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.role = None
            st.session_state.username = None
            st.session_state.keranjang = {}
            st.rerun()
    else:
        st.caption("🔴 *Belum Login*")

st.divider()

# ==========================================
# 🔑 1. LOGIN FORM (WHEN NOT LOGGED IN)
# ==========================================
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("form_login"):
            st.subheader("🔑 Login System")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            role_pilihan = st.selectbox("Akses Sebagai", ["Admin", "Kasir"])
            btn_login = st.form_submit_button("Masuk / Login", type="primary", use_container_width=True)

            if btn_login:
                if role_pilihan == "Admin" and username == "admin" and password == "admin123":
                    st.session_state.logged_in = True
                    st.session_state.role = "Admin"
                    st.session_state.username = username
                    st.toast("Login Admin Berhasil!", icon="🎉")
                    st.rerun()
                elif role_pilihan == "Kasir" and username == "kasir" and password == "kasir123":
                    st.session_state.logged_in = True
                    st.session_state.role = "Kasir"
                    st.session_state.username = username
                    st.toast("Login Kasir Berhasil!", icon="🎉")
                    st.rerun()
                else:
                    st.error("❌ Username, Password, atau Akses Role tidak valid!")

# ==========================================
# 👨‍💼 2. ADMIN NAVIGATION
# ==========================================
elif st.session_state.role == "Admin":
    st.sidebar.title("👨‍💼 Panel Admin")
    menu_admin = st.sidebar.radio("Navigasi System", [
        "Dashboard Admin", 
        "Kelola Stok", 
        "Laporan Penjualan"
    ])

    if menu_admin == "Dashboard Admin":
        st.header("🏠 Dashboard Admin")
        conn = get_connection()
        if conn:
            try:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT COUNT(*) AS total_p FROM produk")
                p_count = cursor.fetchone()['total_p']
                
                cursor.execute("SELECT COUNT(*) AS total_tx, SUM(jumlah_bayar) AS total_omzet FROM pembayaran WHERE status='Berhasil'")
                tx_sum = cursor.fetchone()
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Jenis Produk", f"{p_count} Item")
                c2.metric("Total Transaksi", f"{tx_sum['total_tx'] or 0} Transaksi")
                c3.metric("Total Pendapatan", f"Rp{tx_sum['total_omzet'] or 0:,.2f}")
                cursor.close()
            except Error as e:
                st.error(f"Error Query: {e}")
            finally:
                conn.close()

    elif menu_admin == "Kelola Stok":
        st.header("📦 Kelola Stok")
        tab1, tab2 = st.tabs(["⚙️ Kelola Produk & Stok", "➕ Tambah Produk Baru"])

        with tab1:
            conn = get_connection()
            if conn:
                try:
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute("SELECT * FROM produk ORDER BY id_produk ASC")
                    semua_produk = cursor.fetchall()
                    cursor.close()

                    if semua_produk:
                        for p in semua_produk:
                            pid = p['id_produk']
                            c_id, c_nama, c_kat, c_harga, c_stok, c_aksi = st.columns([1, 3, 2, 2, 2, 3])
                            c_id.write(f"#{pid}")
                            c_nama.write(f"**{p['nama_produk']}**")
                            c_kat.caption(p['kategori_produk'])
                            c_harga.write(f"Rp{p['harga']:,.0f}")
                            
                            if p['status_stok'] == 'Tersedia':
                                c_stok.success("Tersedia")
                            else:
                                c_stok.error("Habis")

                            with c_aksi:
                                status_baru = "Habis" if p['status_stok'] == "Tersedia" else "Tersedia"
                                label_btn = "🔴 Set Habis" if p['status_stok'] == "Tersedia" else "🟢 Set Ada"
                                
                                if st.button(label_btn, key=f"toggle_{pid}", use_container_width=True):
                                    conn_up = get_connection()
                                    if conn_up:
                                        c_up = conn_up.cursor()
                                        c_up.execute("UPDATE produk SET status_stok = %s WHERE id_produk = %s", (status_baru, pid))
                                        conn_up.commit()
                                        conn_up.close()
                                        st.rerun()
                except Error as e:
                    st.error(f"Error Database: {e}")
                finally:
                    conn.close()

        with tab2:
            with st.form("form_tambah_produk", clear_on_submit=True):
                nama_p = st.text_input("Nama Produk")
                kategori_p = st.selectbox("Kategori", ["Makanan Utama", "Apetizer", "Minuman"])
                harga_p = st.number_input("Harga (Rp)", min_value=0.0, step=1000.0)
                status_p = st.selectbox("Status Awal", ["Tersedia", "Habis"])
                btn_simpan_p = st.form_submit_button("Simpan Produk Baru")

                if btn_simpan_p and nama_p.strip() != "":
                    conn = get_connection()
                    if conn:
                        try:
                            cursor = conn.cursor()
                            cursor.execute(
                                "INSERT INTO produk (nama_produk, kategori_produk, harga, status_stok) VALUES (%s, %s, %s, %s)",
                                (nama_p, kategori_p, harga_p, status_p)
                            )
                            conn.commit()
                            cursor.close()
                            st.success(f"Produk '{nama_p}' berhasil ditambahkan!")
                            st.rerun()
                        except Error as e:
                            st.error(f"Gagal menambah produk: {e}")
                        finally:
                            conn.close()

    elif menu_admin == "Laporan Penjualan":
        st.header("📊 Laporan Penjualan")
        col1, col2 = st.columns(2)
        with col1:
            tgl_awal = st.date_input("Tanggal Awal", date.today())
        with col2:
            tgl_akhir = st.date_input("Tanggal Akhir", date.today())

        if st.button("Generate Laporan", type="primary"):
            conn = get_connection()
            if conn:
                try:
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute("""
                        SELECT COUNT(id_bayar) AS total_tx, SUM(jumlah_bayar) AS total_omzet
                        FROM pembayaran
                        WHERE status = 'Berhasil' AND DATE(tgl_bayar) BETWEEN %s AND %s
                    """, (tgl_awal, tgl_akhir))
                    summary = cursor.fetchone()

                    total_omzet = float(summary['total_omzet']) if summary['total_omzet'] else 0.0
                    total_tx = summary['total_tx'] if summary['total_tx'] else 0

                    c1, c2 = st.columns(2)
                    c1.metric("Total Transaksi", f"{total_tx} Transaksi")
                    c2.metric("Total Pendapatan", f"Rp{total_omzet:,.2f}")
                    cursor.close()
                except Error as e:
                    st.error(f"Error Database: {e}")
                finally:
                    conn.close()

# ==========================================
# 🧑‍🍳 3. KASIR NAVIGATION
# ==========================================
elif st.session_state.role == "Kasir":
    st.sidebar.title("🧑‍🍳 Panel Kasir")
    menu_kasir = st.sidebar.radio("Navigasi Kasir", ["Dashboard Kasir", "Input Pesanan", "Pembayaran"])

    if menu_kasir == "Dashboard Kasir":
        st.header("🏠 Dashboard Kasir")
        st.info("💡 Gunakan menu **Input Pesanan** untuk mencatat pesanan baru, lalu lanjutkan ke menu **Pembayaran**.")

    elif menu_kasir == "Input Pesanan":
        st.header("🛒 Input Pesanan")
        conn = get_connection()
        if conn:
            try:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT * FROM produk WHERE status_stok = 'Tersedia'")
                daftar_produk = cursor.fetchall()
                cursor.close()

                if daftar_produk:
                    grid_cols = st.columns(3)
                    for idx, p in enumerate(daftar_produk):
                        with grid_cols[idx % 3]:
                            with st.container(border=True):
                                st.markdown(f"**{p['nama_produk']}**")
                                st.caption(f"🏷️ {p['kategori_produk']}")
                                st.markdown(f"### Rp{p['harga']:,.0f}")
                                
                                if st.button("➕ Tambah", key=f"add_{p['id_produk']}", use_container_width=True):
                                    pid = p['id_produk']
                                    if pid in st.session_state.keranjang:
                                        st.session_state.keranjang[pid]['jumlah'] += 1
                                        st.session_state.keranjang[pid]['subtotal'] = st.session_state.keranjang[pid]['jumlah'] * p['harga']
                                    else:
                                        st.session_state.keranjang[pid] = {
                                            'id_produk': p['id_produk'],
                                            'nama_produk': p['nama_produk'],
                                            'harga': float(p['harga']),
                                            'jumlah': 1,
                                            'subtotal': float(p['harga'])
                                        }
                                    st.toast(f"✅ {p['nama_produk']} masuk ke pesanan!", icon="🛒")

                    st.divider()
                    st.subheader("🛍️ Ringkasan Pesanan Sementara")
                    if st.session_state.keranjang:
                        df_keranjang = pd.DataFrame(list(st.session_state.keranjang.values()))
                        st.table(df_keranjang[['nama_produk', 'jumlah', 'subtotal']])
                    else:
                        st.info("Belum ada menu yang dipilih.")
            except Error as e:
                st.error(f"Error Database: {e}")
            finally:
                conn.close()

    elif menu_kasir == "Pembayaran":
        st.header("💳 Halaman Pembayaran")
        if not st.session_state.keranjang:
            st.warning("⚠️ Belum ada pesanan aktif. Silakan isi pesanan terlebih dahulu di menu 'Input Pesanan'.")
        else:
            df_keranjang = pd.DataFrame(list(st.session_state.keranjang.values()))
            st.table(df_keranjang[['nama_produk', 'jumlah', 'subtotal']])
            
            total_tagihan = df_keranjang['subtotal'].sum()
            st.markdown(f"### **Total Tagihan: Rp{total_tagihan:,.2f}**")

            metode_bayar = st.selectbox("Metode Pembayaran", ["Tunai", "Debit", "Kartu Kredit"])
            jumlah_bayar = st.number_input("Nominal Uang Diterima (Rp)", min_value=0.0, value=float(total_tagihan), step=5000.0)

            if st.button("✅ Bayar & Cetak Struk", type="primary", use_container_width=True):
                if jumlah_bayar < total_tagihan:
                    st.error("❌ Pembayaran Gagal: Uang yang diterima kurang!")
                else:
                    kembalian = jumlah_bayar - total_tagihan
                    conn = get_connection()
                    if conn:
                        try:
                            cursor = conn.cursor()
                            tgl_sekarang = datetime.now().strftime('%Y-%m-%d')
                            waktu_sekarang = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                            cursor.execute("INSERT INTO pesanan (tgl_pesanan, total_harga) VALUES (%s, %s)", (tgl_sekarang, total_tagihan))
                            id_pesanan = cursor.lastrowid

                            for pid, item in st.session_state.keranjang.items():
                                cursor.execute(
                                    "INSERT INTO rincian_item (id_pesanan, id_produk, jumlah, subtotal) VALUES (%s, %s, %s, %s)",
                                    (id_pesanan, item['id_produk'], item['jumlah'], item['subtotal'])
                                )

                            cursor.execute("""
                                INSERT INTO pembayaran (id_pesanan, metode_bayar, jumlah_bayar, status, kembalian, tgl_bayar)
                                VALUES (%s, %s, %s, 'Berhasil', %s, %s)
                            """, (id_pesanan, metode_bayar, jumlah_bayar, kembalian, waktu_sekarang))

                            conn.commit()
                            cursor.close()

                            st.balloons()
                            st.success(f"🎉 Pembayaran Berhasil! Kembalian: Rp{kembalian:,.2f}")
                            st.session_state.keranjang = {}
                        except Error as e:
                            conn.rollback()
                            st.error(f"Gagal memproses transaksi: {e}")
                        finally:
                            conn.close()
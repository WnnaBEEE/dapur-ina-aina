import streamlit as st
import mysql.connector
from mysql.connector import Error
import pandas as pd
import altair as alt
from datetime import datetime, date
from io import BytesIO
from html import escape
from PIL import Image, ImageDraw, ImageFont

# 1. Konfigurasi Halaman Streamlit
st.set_page_config(
    page_title="Restoran Dapur Ina Aina",
    layout="wide"
)

# 2. Fungsi Koneksi Database
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
        st.error(f"Koneksi Database Gagal: {e}")
        return None


def build_receipt_html(receipt):
    item_rows = "".join(
        f"<tr><td>{escape(item['nama_produk'])}</td>"
        f"<td class='center'>{item['jumlah']}</td>"
        f"<td class='right'>Rp{item['subtotal']:,.0f}</td></tr>"
        for item in receipt["items"]
    )
    return f"""<!doctype html>
<html><head><meta charset='utf-8'><title>Struk #{receipt['id_pesanan']}</title>
<style>
body {{ background: #eeeeee; font-family: Arial, sans-serif; margin: 0; }}
.receipt {{ background: white; box-sizing: border-box; margin: 24px auto; padding: 24px; width: 380px; }}
h1 {{ font-size: 20px; margin: 0; text-align: center; }}
p {{ font-size: 12px; margin: 5px 0; }}
table {{ border-collapse: collapse; font-size: 12px; margin: 18px 0; width: 100%; }}
td {{ border-bottom: 1px dashed #999; padding: 7px 0; }}
.center {{ text-align: center; }} .right {{ text-align: right; }}
.total {{ border-top: 2px solid #111; font-weight: bold; font-size: 15px; }}
.footer {{ border-top: 1px dashed #999; margin-top: 18px; padding-top: 12px; text-align: center; }}
@media print {{ body {{ background: white; }} .receipt {{ margin: 0; width: 100%; }} }}
</style></head><body><main class='receipt'>
<h1>RESTORAN DAPUR INA AINA</h1>
<p style='text-align:center'>Struk Pembayaran</p>
<p>ID Pesanan: <b>#{receipt['id_pesanan']}</b></p>
<p>Tanggal: {escape(receipt['waktu'])}</p>
<table><thead><tr><th style='text-align:left'>Menu</th><th>Qty</th><th style='text-align:right'>Subtotal</th></tr></thead>
<tbody>{item_rows}</tbody>
<tfoot><tr><td colspan='2' class='total'>TOTAL</td><td class='right total'>Rp{receipt['total']:,.0f}</td></tr>
<tr><td colspan='2'>Metode Bayar</td><td class='right'>{escape(receipt['metode'])}</td></tr>
<tr><td colspan='2'>Dibayar</td><td class='right'>Rp{receipt['dibayar']:,.0f}</td></tr>
<tr><td colspan='2'>Kembalian</td><td class='right'>Rp{receipt['kembalian']:,.0f}</td></tr></tfoot></table>
<p class='footer'>Terima kasih atas kunjungan Anda.</p>
</main></body></html>"""


def build_receipt_image(receipt):
    try:
        small_font = ImageFont.truetype("DejaVuSans.ttf", 16)
        bold_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 20)
    except OSError:
        small_font = bold_font = ImageFont.load_default()

    line_height = 32
    image_height = 420 + len(receipt["items"]) * line_height
    image = Image.new("RGB", (700, image_height), "white")
    draw = ImageDraw.Draw(image)
    y = 24

    def center(text, selected_font):
        width = draw.textbbox((0, 0), text, font=selected_font)[2]
        draw.text(((700 - width) / 2, y), text, fill="black", font=selected_font)

    center("RESTORAN DAPUR INA AINA", bold_font)
    y += 34
    center("STRUK PEMBAYARAN", small_font)
    y += 38
    draw.text((30, y), f"ID Pesanan: #{receipt['id_pesanan']}", fill="black", font=small_font)
    y += 25
    draw.text((30, y), receipt["waktu"], fill="black", font=small_font)
    y += 32
    draw.line((30, y, 670, y), fill="black", width=2)
    y += 14

    for item in receipt["items"]:
        draw.text((30, y), item["nama_produk"][:28], fill="black", font=small_font)
        draw.text((430, y), f"x{item['jumlah']}", fill="black", font=small_font)
        draw.text((530, y), f"Rp{item['subtotal']:,.0f}", fill="black", font=small_font)
        y += line_height

    draw.line((30, y, 670, y), fill="black", width=2)
    y += 14
    for label, value in [("TOTAL", receipt["total"]), ("DIBAYAR", receipt["dibayar"]), ("KEMBALIAN", receipt["kembalian"])]:
        draw.text((30, y), label, fill="black", font=bold_font if label == "TOTAL" else small_font)
        amount = f"Rp{value:,.0f}"
        width = draw.textbbox((0, 0), amount, font=small_font)[2]
        draw.text((670 - width, y), amount, fill="black", font=small_font)
        y += 30
    draw.text((30, y + 12), f"Metode: {receipt['metode']}", fill="black", font=small_font)
    y += 42
    footer = "Terima kasih atas kunjungan Anda."
    width = draw.textbbox((0, 0), footer, font=small_font)[2]
    draw.text(((700 - width) / 2, y), footer, fill="black", font=small_font)

    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()

# =========================================================
# PERSISTENSI SESSION ON REFRESH (QUERY PARAMS)
# =========================================================
q_params = st.query_params

if "logged_in" in q_params and q_params["logged_in"] == "true":
    st.session_state.logged_in = True
    st.session_state.role = q_params.get("role", None)
    st.session_state.username = q_params.get("username", None)
else:
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'role' not in st.session_state:
        st.session_state.role = None
    if 'username' not in st.session_state:
        st.session_state.username = None

if 'keranjang' not in st.session_state:
    st.session_state.keranjang = {}

saved_menu = q_params.get("menu", None)

if 'menu_admin' not in st.session_state:
    st.session_state.menu_admin = saved_menu if saved_menu else "Dashboard Admin"
if 'menu_kasir' not in st.session_state:
    st.session_state.menu_kasir = saved_menu if saved_menu else "Dashboard Kasir"

# =========================================================
# HEADER & LOGOUT
# =========================================================
head_col1, head_col2 = st.columns([5, 1.5])

with head_col1:
    st.title("Restoran Dapur Ina Aina")

with head_col2:
    st.write("") 
    if st.session_state.logged_in:
        st.markdown(f"**{st.session_state.username}** (`{st.session_state.role}`)")
        if st.button("Logout", key="btn_logout_top", type="secondary", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.role = None
            st.session_state.username = None
            st.session_state.keranjang = {}
            st.session_state.menu_admin = "Dashboard Admin"
            st.session_state.menu_kasir = "Dashboard Kasir"
            st.query_params.clear()
            st.rerun()
    else:
        st.caption("*Belum Login*")

st.divider()

# ==========================================
# 1. HALAMAN LOGIN
# ==========================================
if not st.session_state.logged_in:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("form_login"):
            st.subheader("Form Login Sistem")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            btn_login = st.form_submit_button("Masuk / Login", type="primary", use_container_width=True)

            if btn_login:
                conn = get_connection()
                if conn:
                    try:
                        cursor = conn.cursor(dictionary=True)
                        cursor.execute(
                            "SELECT * FROM user WHERE username=%s AND password=%s",
                            (username, password),
                        )
                        user = cursor.fetchone()
                        cursor.close()

                        if user:
                            st.session_state.logged_in = True
                            st.session_state.role = user['role']
                            st.session_state.username = user['username']
                            
                            if user['role'] == "Admin":
                                st.session_state.menu_admin = "Dashboard Admin"
                                st.query_params["menu"] = "Dashboard Admin"
                            else:
                                st.session_state.menu_kasir = "Dashboard Kasir"
                                st.query_params["menu"] = "Dashboard Kasir"
                                
                            st.query_params["logged_in"] = "true"
                            st.query_params["role"] = user['role']
                            st.query_params["username"] = user['username']
                            st.toast(f"Login {user['role']} Berhasil!", icon="")
                            st.rerun()
                        else:
                            st.error("Username atau Password tidak cocok!")
                    except Error as e:
                        st.error(f"Error Database: {e}")
                    finally:
                        conn.close()

# ==========================================
# 2. NAVIGASI ADMIN
# ==========================================
elif st.session_state.role == "Admin":
    st.sidebar.title("Panel Admin")
    st.sidebar.markdown("---")

    list_menu_admin = [
        ("Dashboard Admin", "Dashboard Admin"),
        ("Kelola Stok", "Kelola Stok"),
        ("Laporan Penjualan", "Laporan Penjualan")
    ]

    for label, key_val in list_menu_admin:
        is_active = (st.session_state.menu_admin == key_val)
        if st.sidebar.button(
            label, 
            key=f"nav_admin_{key_val}", 
            type="primary" if is_active else "secondary", 
            use_container_width=True
        ):
            st.session_state.menu_admin = key_val
            st.query_params["menu"] = key_val
            st.rerun()

    menu_admin = st.session_state.menu_admin

    if menu_admin == "Dashboard Admin":
        st.header("Dashboard Admin")
        conn = get_connection()
        if conn:
            try:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT COUNT(*) AS total_p FROM produk")
                p_count = cursor.fetchone()['total_p']
                
                cursor.execute("""
                    SELECT COUNT(DISTINCT pb.id_bayar) AS total_tx,
                           COALESCE(SUM(ps.total_harga), 0) AS total_omzet
                    FROM pembayaran pb
                    JOIN pesanan ps ON pb.id_pesanan = ps.id_pesanan
                    WHERE pb.status = 'Berhasil'
                """)
                tx_sum = cursor.fetchone()

                cursor.execute("""
                    SELECT DATE(pb.tgl_bayar) AS tanggal,
                           COUNT(DISTINCT pb.id_bayar) AS total_transaksi,
                           COALESCE(SUM(ps.total_harga), 0) AS total_omzet
                    FROM pembayaran pb
                    JOIN pesanan ps ON pb.id_pesanan = ps.id_pesanan
                    WHERE pb.status = 'Berhasil'
                    GROUP BY DATE(pb.tgl_bayar)
                    ORDER BY tanggal
                """)
                daily_sales = pd.DataFrame(cursor.fetchall())

                cursor.execute("""
                    SELECT p.nama_produk,
                           SUM(r.jumlah) AS total_terjual,
                           COALESCE(SUM(r.subtotal), 0) AS total_penjualan
                    FROM rincian_item r
                    JOIN pesanan ps ON r.id_pesanan = ps.id_pesanan
                    JOIN pembayaran pb ON ps.id_pesanan = pb.id_pesanan
                    JOIN produk p ON r.id_produk = p.id_produk
                    WHERE pb.status = 'Berhasil'
                    GROUP BY p.id_produk, p.nama_produk
                    ORDER BY total_penjualan DESC
                    LIMIT 10
                """)
                product_sales = pd.DataFrame(cursor.fetchall())
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Total Jenis Produk", f"{p_count} Item")
                c2.metric("Total Transaksi", f"{tx_sum['total_tx'] or 0} Transaksi")
                c3.metric("Total Pendapatan", f"Rp{float(tx_sum['total_omzet'] or 0):,.2f}")

                if not daily_sales.empty or not product_sales.empty:
                    st.divider()
                    chart_col1, chart_col2 = st.columns(2)

                    with chart_col1:
                        st.subheader("Pendapatan Per Hari")
                        if daily_sales.empty:
                            st.info("Belum ada data penjualan.")
                        else:
                            revenue_chart = alt.Chart(daily_sales).mark_line(
                                point=True
                            ).encode(
                                x=alt.X("tanggal:T", title="Tanggal"),
                                y=alt.Y("total_omzet:Q", title="Pendapatan (Rp)"),
                                tooltip=[
                                    alt.Tooltip("tanggal:T", title="Tanggal"),
                                    alt.Tooltip("total_omzet:Q", title="Pendapatan", format=",.2f"),
                                    alt.Tooltip("total_transaksi:Q", title="Transaksi"),
                                ],
                            ).properties(height=350).interactive()
                            st.altair_chart(revenue_chart, use_container_width=True)

                    with chart_col2:
                        st.subheader("Produk Terlaris")
                        if product_sales.empty:
                            st.info("Belum ada data produk terjual.")
                        else:
                            product_chart = alt.Chart(product_sales).mark_bar().encode(
                                x=alt.X("total_penjualan:Q", title="Penjualan (Rp)"),
                                y=alt.Y("nama_produk:N", sort="-x", title="Produk"),
                                tooltip=[
                                    alt.Tooltip("nama_produk:N", title="Produk"),
                                    alt.Tooltip("total_terjual:Q", title="Jumlah Terjual"),
                                    alt.Tooltip("total_penjualan:Q", title="Penjualan", format=",.2f"),
                                ],
                            ).properties(height=350).interactive()
                            st.altair_chart(product_chart, use_container_width=True)

                cursor.close()
            except Error as e:
                st.error(f"Error Database: {e}")
            finally:
                conn.close()

    elif menu_admin == "Kelola Stok":
        st.header("Kelola Stok Produk")
        tab1, tab2 = st.tabs(["Edit Jumlah Stok", "Tambah Produk Baru"])

        with tab1:
            # Inisialisasi State Pengurutan
            if 'sort_col' not in st.session_state:
                st.session_state.sort_col = 'id_produk'
            if 'sort_dir' not in st.session_state:
                st.session_state.sort_dir = 'ASC'

            def toggle_sort(column_name):
                if st.session_state.sort_col == column_name:
                    st.session_state.sort_dir = 'DESC' if st.session_state.sort_dir == 'ASC' else 'ASC'
                else:
                    st.session_state.sort_col = column_name
                    st.session_state.sort_dir = 'ASC'

            # 1. TOMBOL PENGURUTAN PADA HEADER
            h_col1, h_col2, h_col3, h_col4, h_col5, h_col6 = st.columns([1, 3, 2, 2, 2, 2])
            
            # Kotak Biru (Urutan Ditambahkan / ID)
            lbl_id = " Urutan ⬆" if st.session_state.sort_col == 'id_produk' and st.session_state.sort_dir == 'ASC' else (" Urutan ⬇" if st.session_state.sort_col == 'id_produk' else " Urutan ⇅")
            if h_col1.button(lbl_id, key="sort_id", use_container_width=True):
                toggle_sort('id_produk')
                st.rerun()

            # Kotak Hijau (Nama Produk)
            lbl_nama = " Nama Produk ⬆" if st.session_state.sort_col == 'nama_produk' and st.session_state.sort_dir == 'ASC' else (" Nama Produk ⬇" if st.session_state.sort_col == 'nama_produk' else " Nama Produk ⇅")
            if h_col2.button(lbl_nama, key="sort_nama", use_container_width=True):
                toggle_sort('nama_produk')
                st.rerun()

            # Kotak Kuning (Kategori)
            lbl_kat = " Kategori ⬆" if st.session_state.sort_col == 'kategori_produk' and st.session_state.sort_dir == 'ASC' else (" Kategori ⬇" if st.session_state.sort_col == 'kategori_produk' else " Kategori ⇅")
            if h_col3.button(lbl_kat, key="sort_kat", use_container_width=True):
                toggle_sort('kategori_produk')
                st.rerun()

            # Kotak Ungu (Harga)
            lbl_harga = " Harga ⬆" if st.session_state.sort_col == 'harga' and st.session_state.sort_dir == 'ASC' else (" Harga ⬇" if st.session_state.sort_col == 'harga' else " Harga ⇅")
            if h_col4.button(lbl_harga, key="sort_harga", use_container_width=True):
                toggle_sort('harga')
                st.rerun()

            lbl_stok = " Jumlah Stok ⬆" if st.session_state.sort_col == 'stok' and st.session_state.sort_dir == 'ASC' else (" Jumlah Stok ⬇" if st.session_state.sort_col == 'stok' else " Jumlah Stok ⇅")
            if h_col5.button(lbl_stok, key="sort_stok", use_container_width=True):
                toggle_sort('stok')
                st.rerun()


            st.markdown("---")

            # Query Data Berdasarkan Pengurutan Aktif
            conn = get_connection()
            semua_produk = []
            if conn:
                try:
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute(f"SELECT * FROM produk ORDER BY {st.session_state.sort_col} {st.session_state.sort_dir}")
                    semua_produk = cursor.fetchall()
                    cursor.close()
                except Error as e:
                    st.error(f"Error Database: {e}")
                finally:
                    conn.close()

            # 2. FORM EDIT BATCH DENGAN TOMBOL SIMPAN SEMUA (KOTAK MERAH)
            if semua_produk:
                with st.form("form_batch_stok"):
                    # Kotak Merah: Tombol Simpan Semua
                    btn_simpan_semua = st.form_submit_button(" Simpan Semua Perubahan", type="primary", use_container_width=True)
                    st.markdown("---")

                    input_stok_dict = {}

                    for p in semua_produk:
                        pid = p['id_produk']
                        c_id, c_nama, c_kat, c_harga, c_stok, c_empty = st.columns([1, 3, 2, 2, 2, 2])
                        c_id.write(f"#{pid}")
                        c_nama.write(f"**{p['nama_produk']}**")
                        c_kat.caption(p['kategori_produk'])
                        c_harga.write(f"Rp{float(p['harga']):,.0f}")
                        
                        stok_val = c_stok.number_input(
                            f"Stok_{pid}", 
                            min_value=0, 
                            value=int(p['stok']), 
                            key=f"input_stok_{pid}", 
                            label_visibility="collapsed"
                        )
                        input_stok_dict[pid] = stok_val

                    # Eksekusi Pembaruan Ke Database Saat Tombol Ditekan
                    if btn_simpan_semua:
                        conn_up = get_connection()
                        if conn_up:
                            try:
                                cursor_up = conn_up.cursor()
                                for pid_up, stok_baru in input_stok_dict.items():
                                    cursor_up.execute("UPDATE produk SET stok = %s WHERE id_produk = %s", (stok_baru, pid_up))
                                conn_up.commit()
                                cursor_up.close()
                                st.toast("Semua perubahan stok berhasil disimpan!", icon="")
                                st.rerun()
                            except Error as e:
                                st.error(f"Gagal mengupdate stok: {e}")
                            finally:
                                conn_up.close()

        with tab2:
            with st.form("form_tambah_produk", clear_on_submit=True):
                nama_p = st.text_input("Nama Produk")
                kategori_p = st.selectbox("Kategori", ["Makanan Utama", "Apetizer", "Minuman"])
                harga_p = st.number_input("Harga (Rp)", min_value=0.0, step=1000.0)
                stok_p = st.number_input("Jumlah Stok Awal", min_value=0, value=1, step=1)
                btn_simpan_p = st.form_submit_button("Simpan Produk Baru")

                if btn_simpan_p and nama_p.strip() != "":
                    conn = get_connection()
                    if conn:
                        try:
                            cursor = conn.cursor()
                            cursor.execute(
                                "INSERT INTO produk (nama_produk, kategori_produk, harga, stok) VALUES (%s, %s, %s, %s)",
                                (nama_p, kategori_p, harga_p, stok_p)
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
        st.header("Laporan Penjualan")
        col1, col2, col3 = st.columns(3)
        with col1:
            tgl_awal = st.date_input("Tanggal Awal", date.today())
        with col2:
            tgl_akhir = st.date_input("Tanggal Akhir", date.today())
        with col3:
            periode_lap = st.selectbox("Periode", ["Mingguan", "Bulanan"])

        if st.button("Generate Laporan", type="primary"):
            if tgl_awal > tgl_akhir:
                st.error("Tanggal awal tidak boleh lebih besar dari tanggal akhir.")
            else:
                conn = get_connection()
                if conn:
                    try:
                        cursor = conn.cursor(dictionary=True)
                        date_params = (tgl_awal, tgl_akhir)

                        cursor.execute("""
                            SELECT COUNT(DISTINCT pb.id_bayar) AS total_tx,
                                   COALESCE(SUM(ps.total_harga), 0) AS total_omzet
                            FROM pembayaran pb
                            JOIN pesanan ps ON pb.id_pesanan = ps.id_pesanan
                            WHERE pb.status = 'Berhasil'
                              AND DATE(pb.tgl_bayar) BETWEEN %s AND %s
                        """, date_params)
                        summary = cursor.fetchone()

                        cursor.execute("""
                            SELECT DATE(pb.tgl_bayar) AS tanggal,
                                   COUNT(DISTINCT pb.id_bayar) AS total_transaksi,
                                   COALESCE(SUM(ps.total_harga), 0) AS total_omzet
                            FROM pembayaran pb
                            JOIN pesanan ps ON pb.id_pesanan = ps.id_pesanan
                            WHERE pb.status = 'Berhasil'
                              AND DATE(pb.tgl_bayar) BETWEEN %s AND %s
                            GROUP BY DATE(pb.tgl_bayar)
                            ORDER BY tanggal
                        """, date_params)
                        daily_rows = cursor.fetchall()

                        cursor.execute("""
                            SELECT pb.id_bayar AS id_pembayaran,
                                   ps.id_pesanan,
                                   pb.tgl_bayar,
                                   pb.metode_bayar,
                                   p.nama_produk,
                                   p.kategori_produk,
                                   r.jumlah,
                                   r.subtotal,
                                   ps.total_harga AS total_tagihan,
                                   pb.jumlah_bayar,
                                   pb.kembalian
                            FROM pembayaran pb
                            JOIN pesanan ps ON pb.id_pesanan = ps.id_pesanan
                            JOIN rincian_item r ON ps.id_pesanan = r.id_pesanan
                            JOIN produk p ON r.id_produk = p.id_produk
                            WHERE pb.status = 'Berhasil'
                              AND DATE(pb.tgl_bayar) BETWEEN %s AND %s
                            ORDER BY pb.tgl_bayar, pb.id_bayar, p.nama_produk
                        """, date_params)
                        detail_rows = cursor.fetchall()
                        cursor.close()

                        st.session_state.laporan_data = {
                            "ringkasan": {
                                "total_tx": summary["total_tx"] or 0,
                                "total_omzet": float(summary["total_omzet"] or 0),
                            },
                            "harian": pd.DataFrame(daily_rows),
                            "detail": pd.DataFrame(detail_rows),
                            "tgl_awal": tgl_awal,
                            "tgl_akhir": tgl_akhir,
                        }
                    except Error as e:
                        st.error(f"Error Database: {e}")
                    finally:
                        conn.close()

        laporan_data = st.session_state.get("laporan_data")
        if laporan_data:
            ringkasan = laporan_data["ringkasan"]
            c1, c2 = st.columns(2)
            c1.metric("Total Transaksi", f"{ringkasan['total_tx']} Transaksi")
            c2.metric("Total Pendapatan", f"Rp{ringkasan['total_omzet']:,.2f}")

            st.subheader("Ringkasan Per Hari")
            if laporan_data["harian"].empty:
                st.info("Tidak ada transaksi berhasil pada rentang tanggal tersebut.")
            else:
                st.dataframe(laporan_data["harian"], use_container_width=True, hide_index=True)

            st.subheader("Isi Billing")
            if laporan_data["detail"].empty:
                st.info("Tidak ada detail billing pada rentang tanggal tersebut.")
            else:
                st.dataframe(laporan_data["detail"], use_container_width=True, hide_index=True)

            csv_data = laporan_data["detail"].to_csv(index=False).encode("utf-8-sig")
            download_col1, download_col2 = st.columns(2)
            with download_col1:
                st.download_button(
                    "Download Detail CSV",
                    data=csv_data,
                    file_name=f"laporan_{laporan_data['tgl_awal']}_{laporan_data['tgl_akhir']}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )

            with download_col2:
                excel_file = BytesIO()
                try:
                    with pd.ExcelWriter(excel_file, engine="openpyxl") as writer:
                        laporan_data["detail"].to_excel(writer, sheet_name="Isi Billing", index=False)
                    st.download_button(
                        "Download Laporan Excel",
                        data=excel_file.getvalue(),
                        file_name=f"laporan_{laporan_data['tgl_awal']}_{laporan_data['tgl_akhir']}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                    )
                except ImportError:
                    st.info("Export Excel memerlukan package openpyxl. CSV tetap tersedia.")

# ==========================================
# 3. NAVIGASI KASIR
# ==========================================
elif st.session_state.role == "Kasir":
    st.sidebar.title("Panel Kasir")
    st.sidebar.markdown("---")

    list_menu_kasir = [
        ("Dashboard Kasir", "Dashboard Kasir"),
        ("Input Pesanan", "Input Pesanan"),
        ("Halaman Pembayaran", "Pembayaran")
    ]

    for label, key_val in list_menu_kasir:
        is_active = (st.session_state.menu_kasir == key_val)
        if st.sidebar.button(
            label, 
            key=f"nav_kasir_{key_val}", 
            type="primary" if is_active else "secondary", 
            use_container_width=True
        ):
            st.session_state.menu_kasir = key_val
            st.query_params["menu"] = key_val
            st.rerun()

    menu_kasir = st.session_state.menu_kasir

    if menu_kasir == "Dashboard Kasir":
        st.header("Dashboard Kasir")
        st.info("Gunakan menu **Input Pesanan** untuk mencatat pesanan baru, lalu lanjutkan ke menu **Pembayaran**.")
        st.info("Mari buat pemilik resto ina aina kaya! 💰💰💰")

    elif menu_kasir == "Input Pesanan":
        st.header("Input Pesanan")

        filter_col1, filter_col2 = st.columns([2, 1])
        with filter_col1:
            cari_menu = st.text_input(
                "Cari Menu",
                placeholder="Ketik nama menu...",
                key="cari_menu",
            )

        conn = get_connection()
        daftar_produk = []
        if conn:
            try:
                cursor = conn.cursor(dictionary=True)
                cursor.execute("""
                    SELECT DISTINCT kategori_produk
                    FROM produk
                    ORDER BY kategori_produk
                """)
                daftar_kategori = [row["kategori_produk"] for row in cursor.fetchall()]

                with filter_col2:
                    kategori_menu = st.selectbox(
                        "Kategori",
                        ["Semua Kategori"] + daftar_kategori,
                        key="kategori_menu",
                    )

                query_produk = "SELECT * FROM produk WHERE stok > 0"
                query_params = []
                if cari_menu.strip():
                    query_produk += " AND nama_produk LIKE %s"
                    query_params.append(f"%{cari_menu.strip()}%")
                if kategori_menu != "Semua Kategori":
                    query_produk += " AND kategori_produk = %s"
                    query_params.append(kategori_menu)
                query_produk += " ORDER BY nama_produk"

                cursor.execute(query_produk, tuple(query_params))
                daftar_produk = cursor.fetchall()
                cursor.close()
            except Error as e:
                st.error(f"Error Database: {e}")
            finally:
                conn.close()

        if daftar_produk:
            stok_produk = {p['id_produk']: int(p['stok']) for p in daftar_produk}
            grid_cols = st.columns(3)
            for idx, p in enumerate(daftar_produk):
                pid = p['id_produk']
                stok_tersedia = p['stok']
                
                with grid_cols[idx % 3]:
                    with st.container(border=True):
                        st.markdown(f"**{p['nama_produk']}**")
                        st.caption(f"{p['kategori_produk']} | Stok: **{stok_tersedia}**")
                        st.markdown(f"### Rp{float(p['harga']):,.0f}")
                        
                        jumlah_di_keranjang = st.session_state.keranjang.get(pid, {}).get('jumlah', 0)
                        
                        if jumlah_di_keranjang >= stok_tersedia:
                            st.button("Stok Tidak Cukup", key=f"add_{pid}", disabled=True, use_container_width=True)
                        else:
                            if st.button("Tambah Ke Pesanan", key=f"add_{pid}", use_container_width=True):
                                if pid in st.session_state.keranjang:
                                    st.session_state.keranjang[pid]['jumlah'] += 1
                                    st.session_state.keranjang[pid]['subtotal'] = st.session_state.keranjang[pid]['jumlah'] * float(p['harga'])
                                else:
                                    st.session_state.keranjang[pid] = {
                                        'id_produk': p['id_produk'],
                                        'nama_produk': p['nama_produk'],
                                        'harga': float(p['harga']),
                                        'jumlah': 1,
                                        'subtotal': float(p['harga'])
                                    }
                                st.toast(f"{p['nama_produk']} ditambahkan!")
                                st.rerun()

            st.divider()
            st.subheader("Ringkasan Pesanan Sementara")
            if st.session_state.keranjang:
                for pid, item in list(st.session_state.keranjang.items()):
                    item_col1, item_col2, item_col3, item_col4, item_col5 = st.columns([3, 1.5, 1.5, 1, 1])
                    item_col1.write(f"**{item['nama_produk']}**")
                    item_col1.caption(f"Rp{item['harga']:,.0f} per item")

                    stok_maks = stok_produk.get(pid, int(item['jumlah']))
                    jumlah_edit = item_col2.number_input(
                        "Jumlah",
                        min_value=1,
                        max_value=max(stok_maks, int(item['jumlah'])),
                        value=int(item['jumlah']),
                        step=1,
                        key=f"cart_quantity_{pid}",
                    )
                    item_col3.write(f"Rp{item['subtotal']:,.0f}")

                    if item_col4.button("Simpan", key=f"edit_cart_{pid}"):
                        if pid not in stok_produk:
                            st.error(f"Stok produk '{item['nama_produk']}' sudah habis.")
                        elif jumlah_edit > stok_maks:
                            st.error(f"Jumlah maksimal untuk '{item['nama_produk']}' adalah {stok_maks}.")
                        else:
                            item['jumlah'] = jumlah_edit
                            item['subtotal'] = jumlah_edit * item['harga']
                            st.session_state.keranjang[pid] = item
                            st.rerun()

                    if item_col5.button("Hapus", key=f"delete_cart_{pid}"):
                        del st.session_state.keranjang[pid]
                        st.rerun()
            else:
                st.info("Belum ada menu yang dipilih.")
        elif conn:
            st.info("Tidak ada menu yang cocok dengan pencarian atau kategori tersebut.")

    elif menu_kasir == "Pembayaran":
        st.header("Halaman Pembayaran")
        st.markdown(
            """
            <style>
            div[data-testid="stNumberInput"] input {
                font-size: 28px !important;
                font-weight: 600 !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        receipt = st.session_state.get("receipt")
        if receipt:
            st.subheader("Struk Pembayaran")
            receipt_html = build_receipt_html(receipt)
            st.download_button(
                "Download Struk untuk Dicetak",
                data=receipt_html.encode("utf-8"),
                file_name=f"struk_{receipt['id_pesanan']}.html",
                mime="text/html",
                use_container_width=True,
            )
            st.download_button(
                "Download Struk sebagai Gambar",
                data=build_receipt_image(receipt),
                file_name=f"struk_{receipt['id_pesanan']}.png",
                mime="image/png",
                use_container_width=True,
            )
            st.components.v1.html(receipt_html, height=560, scrolling=False)

        if not st.session_state.keranjang:
            st.warning("Belum ada pesanan aktif. Silakan isi pesanan terlebih dahulu di menu 'Input Pesanan'.")
        else:
            df_keranjang = pd.DataFrame(list(st.session_state.keranjang.values()))
            st.subheader("Detail Item Pesanan")
            st.table(df_keranjang[['nama_produk', 'jumlah', 'subtotal']])
            
            total_tagihan = float(df_keranjang['subtotal'].sum())
            st.markdown(f"### **Total Tagihan: Rp{total_tagihan:,.2f}**")

            metode_bayar = st.selectbox("Metode Pembayaran", ["Tunai", "Debit", "Kartu Kredit"])
            jumlah_bayar = st.number_input("Nominal Uang Diterima (Rp)", min_value=0.0, value=total_tagihan, step=5000.0)

            if st.button("Bayar & Cetak Struk", type="primary", use_container_width=True):
                if float(jumlah_bayar) < total_tagihan:
                    st.error("Pembayaran Gagal: Uang yang diterima kurang!")
                else:
                    kembalian = float(jumlah_bayar) - total_tagihan
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
                                cursor.execute(
                                    "UPDATE produk SET stok = stok - %s WHERE id_produk = %s",
                                    (item['jumlah'], item['id_produk'])
                                )

                            cursor.execute("""
                                INSERT INTO pembayaran (id_pesanan, metode_bayar, jumlah_bayar, status, kembalian, tgl_bayar)
                                VALUES (%s, %s, %s, 'Berhasil', %s, %s)
                            """, (id_pesanan, metode_bayar, jumlah_bayar, kembalian, waktu_sekarang))

                            conn.commit()
                            cursor.close()

                            st.session_state.receipt = {
                                "id_pesanan": id_pesanan,
                                "waktu": waktu_sekarang,
                                "items": [
                                    {
                                        "nama_produk": item["nama_produk"],
                                        "jumlah": int(item["jumlah"]),
                                        "subtotal": float(item["subtotal"]),
                                    }
                                    for item in st.session_state.keranjang.values()
                                ],
                                "total": total_tagihan,
                                "metode": metode_bayar,
                                "dibayar": float(jumlah_bayar),
                                "kembalian": kembalian,
                            }
                            st.success(f" Pembayaran Berhasil! Kembalian: Rp{kembalian:,.2f}")
                            st.session_state.keranjang = {}
                            st.rerun()
                        except Error as e:
                            conn.rollback()
                            st.error(f"Gagal memproses transaksi: {e}")
                        finally:
                            conn.close()
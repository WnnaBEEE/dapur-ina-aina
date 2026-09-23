import mysql.connector
from mysql.connector import Error
from datetime import datetime

# ==========================================
# 1. KONEKSI DATABASE & ERROR HANDLING
# ==========================================
def create_connection():
    """Membangun koneksi ke database MySQL dengan penanganan error."""
    try:
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Apismabar12@",
            database="resto"
        )
        if conn.is_connected():
            return conn
    except Error as e:
        print(f"\n[ERROR SYSTEM] Gagal terhubung ke MySQL: {e}")
        print("Pastikan service MySQL berjalan dan kredensial benar.")
        return None

# ==========================================
# 2. PARADIGMA OOP: CLASS PRODUK (KELOLA STOK)
# ==========================================
class Produk:
    @staticmethod
    def tampilkan_menu():
        conn = create_connection()
        if not conn: return []
        
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM produk")
            baris = cursor.fetchall()
            return baris
        except Error as e:
            print(f"[ERROR DB] Gagal mengambil data produk: {e}")
            return []
        finally:
            conn.close()

    @staticmethod
    def input_produk_baru(nama, kategori, harga, status):
        """Input data stok makanan/minuman baru"""
        conn = create_connection()
        if not conn: return
        
        try:
            cursor = conn.cursor()
            query = "INSERT INTO produk (nama_produk, kategori_produk, harga, status_stok) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (nama, kategori, harga, status))
            conn.commit()
            print(f"\n[SUKSES] Produk '{nama}' berhasil ditambahkan ke database!")
        except Error as e:
            print(f"\n[ERROR DB] Gagal menyimpan produk: {e}")
        finally:
            conn.close()

    @staticmethod
    def update_status_stok(id_produk, status_baru):
        """Update data stok berdasarkan kriteria"""
        conn = create_connection()
        if not conn: return
        
        try:
            cursor = conn.cursor()
            query = "UPDATE produk SET status_stok = %s WHERE id_produk = %s"
            cursor.execute(query, (status_baru, id_produk))
            conn.commit()
            if cursor.rowcount > 0:
                print(f"\n[SUKSES] Status stok ID {id_produk} berhasil diubah menjadi '{status_baru}'.")
            else:
                print(f"\n[ERROR] ID Produk {id_produk} tidak ditemukan.")
        except Error as e:
            print(f"\n[ERROR DB] Gagal update stok: {e}")
        finally:
            conn.close()

# ==========================================
# 3. PARADIGMA OOP: CLASS TRANSAKSI & BILLING
# ==========================================
class Transaksi:
    def __init__(self):
        self.keranjang = []
        self.total_harga = 0.0

    def tambah_pesanan(self, produk, jumlah):
        subtotal = float(produk['harga']) * jumlah
        self.keranjang.append({
            'id_produk': produk['id_produk'],
            'nama_produk': produk['nama_produk'],
            'harga': float(produk['harga']),
            'jumlah': jumlah,
            'subtotal': subtotal
        })
        self.total_harga += subtotal

    def simpan_dan_bayar(self):
        if not self.keranjang:
            print("\n[INFO] Keranjang kosong, transaksi dibatalkan.")
            return

        print(f"\nTotal Tagihan: Rp{self.total_harga:,.2f}")
        print("Pilih Metode Pembayaran:")
        print("1. Tunai\n2. Debit\n3. Kartu Kredit")
        
        pilihan_bayar = input("Pilihan (1/2/3): ")
        metode_map = {"1": "Tunai", "2": "Debit", "3": "Kartu Kredit"}
        metode = metode_map.get(pilihan_bayar, "Tunai")

        try:
            uang_diterima = float(input("Masukkan nominal uang yang diterima: Rp"))
            if uang_diterima < self.total_harga:
                print("\n[ERROR LOGIC] Transaksi Gagal: Uang pembayaran kurang dari total tagihan!")
                return
            
            kembalian = uang_diterima - self.total_harga
            
            # Simpan ke Database
            conn = create_connection()
            if not conn: return
            
            cursor = conn.cursor()
            tgl_sekarang = datetime.now().strftime('%Y-%m-%d')
            waktu_sekarang = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # 1. Insert Pesanan
            cursor.execute("INSERT INTO pesanan (tgl_pesanan, total_harga) VALUES (%s, %s)", (tgl_sekarang, self.total_harga))
            id_pesanan = cursor.lastrowid

            # 2. Insert Rincian Item
            for item in self.keranjang:
                cursor.execute("INSERT INTO rincian_item (id_pesanan, id_produk, jumlah, subtotal) VALUES (%s, %s, %s, %s)",
                               (id_pesanan, item['id_produk'], item['jumlah'], item['subtotal']))

            # 3. Insert Pembayaran
            cursor.execute("""
                INSERT INTO pembayaran (id_pesanan, metode_bayar, jumlah_bayar, status, kembalian, tgl_bayar) 
                VALUES (%s, %s, %s, 'Berhasil', %s, %s)
            """, (id_pesanan, metode, uang_diterima, kembalian, waktu_sekarang))

            conn.commit()
            
            self.cetak_billing(id_pesanan, metode, uang_diterima, kembalian)

        except ValueError:
            print("\n[ERROR INPUT] Nominal uang harus berupa angka! Transaksi dibatalkan.")
        except Error as e:
            print(f"\n[ERROR DB] Gagal menyimpan transaksi: {e}")
        finally:
            if 'conn' in locals() and conn.is_connected():
                conn.close()

    def cetak_billing(self, id_pesanan, metode, bayar, kembali):
        print("\n" + "="*45)
        print("          BILLING - DAPUR INA AINA         ")
        print("="*45)
        print(f"ID Pesanan   : #{id_pesanan}")
        print("---------------------------------------------")
        for item in self.keranjang:
            print(f"{item['nama_produk']:<20} x{item['jumlah']:<2} Rp{item['subtotal']:,.2f}")
        print("---------------------------------------------")
        print(f"TOTAL TAGIHAN : Rp{self.total_harga:,.2f}")
        print(f"METODE BAYAR  : {metode}")
        print(f"UANG DITERIMA : Rp{bayar:,.2f}")
        print(f"KEMBALIAN     : Rp{kembali:,.2f}")
        print("="*45 + "\n")

def rekap_penjualan(tgl_awal, tgl_akhir, periode="Mingguan"):
    """
    Merekap hasil penjualan berdasarkan rentang tanggal,
    menampilkan rincian produk terjual, total omzet,
    serta menyimpan hasilnya ke tabel laporan.
    """
    conn = create_connection()
    if not conn:
        return

    try:
        cursor = conn.cursor(dictionary=True)

        query_total = """
            SELECT 
                COUNT(id_bayar) AS total_transaksi,
                SUM(jumlah_bayar) AS total_pendapatan
            FROM pembayaran
            WHERE status = 'Berhasil' 
              AND DATE(tgl_bayar) BETWEEN %s AND %s
        """
        cursor.execute(query_total, (tgl_awal, tgl_akhir))
        ringkasan = cursor.fetchone()

        total_transaksi = ringkasan['total_transaksi'] if ringkasan['total_transaksi'] else 0
        total_pendapatan = float(ringkasan['total_pendapatan']) if ringkasan['total_pendapatan'] else 0.0

        query_rincian = """
            SELECT 
                p.nama_produk,
                p.kategori_produk,
                SUM(r.jumlah) AS total_terjual,
                SUM(r.subtotal) AS total_penjualan
            FROM rincian_item r
            JOIN pesanan ps ON r.id_pesanan = ps.id_pesanan
            JOIN pembayaran pb ON ps.id_pesanan = pb.id_pesanan
            JOIN produk p ON r.id_produk = p.id_produk
            WHERE pb.status = 'Berhasil'
              AND DATE(pb.tgl_bayar) BETWEEN %s AND %s
            GROUP BY p.id_produk, p.nama_produk, p.kategori_produk
            ORDER BY total_terjual DESC
        """
        cursor.execute(query_rincian, (tgl_awal, tgl_akhir))
        rincian_produk = cursor.fetchall()

        # 3. Menyimpan hasil rekapitulasi ke dalam tabel 'laporan'
        query_simpan_laporan = """
            INSERT INTO laporan (periode_laporan, total_pendapatan, tgl_awal, tgl_akhir)
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(query_simpan_laporan, (periode, total_pendapatan, tgl_awal, tgl_akhir))
        conn.commit()

        # 4. Menampilkan tampilan rekapitulasi penjualan di layar
        print("\n==================================================================")
        print("                REKAPITULASI HASIL PENJUALAN                      ")
        print("                   RESTORAN DAPUR INA AINA                        ")
        print("==================================================================")
        print(f"Periode Laporan  : {periode}")
        print(f"Rentang Tanggal  : {tgl_awal} s/d {tgl_akhir}")
        print(f"Total Transaksi  : {total_transaksi} Transaksi Berhasil")
        print("------------------------------------------------------------------")
        print(f"{'Nama Produk':<22} | {'Kategori':<14} | {'Terjual':<8} | {'Total Omzet'}")
        print("------------------------------------------------------------------")
        
        if not rincian_produk:
            print("Tidak ada transaksi berhasil pada rentang tanggal tersebut.")
        else:
            for item in rincian_produk:
                print(f"{item['nama_produk']:<22} | {item['kategori_produk']:<14} | {item['total_terjual']:<8} | Rp{item['total_penjualan']:,.2f}")

        print("------------------------------------------------------------------")
        print(f"TOTAL PENDAPATAN : Rp{total_pendapatan:,.2f}")
        print("==================================================================\n")
        print("[SUKSES] Data rekapitulasi berhasil disimpan ke database (tabel laporan).")

    except Error as e:
        conn.rollback()
        print(f"[ERROR DB] Gagal melakukan rekapitulasi penjualan: {e}")
    finally:
        conn.close()

# Example usage:
# rekap_penjualan('2026-09-01', '2026-09-30', 'Bulanan')

# ==========================================
# 4. MENU UTAMA (APLIKASI)
# ==========================================
def main():
    while True:
        print("\n=== SISTEM RESTORAN DAPUR INA AINA ===")
        print("1. Kasir - Buat Transaksi Pesanan")
        print("2. Admin - Input Data Produk Baru")
        print("3. Admin - Update Status Stok")
        print("4. Admin - Rekap Penjualan")
        print("0. Keluar")
        
        menu = input("Pilih menu: ")
        
        if menu == "1":
            menu_kasir()
        elif menu == "2":
            menu_input_produk()
        elif menu == "3":
            menu_update_stok()
        elif menu == "4":
            print("\n--- REKAP PENJUALAN ---")
            tgl_awal = input("Masukkan Tanggal Awal (YYYY-MM-DD): ")
            tgl_akhir = input("Masukkan Tanggal Akhir (YYYY-MM-DD): ")
            periode = input("Masukkan Periode Laporan (misal: Mingguan/Bulanan): ")
            rekap_penjualan(tgl_awal, tgl_akhir, periode)
        elif menu == "0":
            print("Program selesai.")
            break
        else:
            print("[ERROR] Pilihan menu tidak valid!")

def menu_kasir():
    produk_list = Produk.tampilkan_menu()
    tersedia = [p for p in produk_list if p['status_stok'] == 'Tersedia']
    
    if not tersedia:
        print("\n[INFO] Tidak ada menu yang tersedia saat ini.")
        return

    transaksi = Transaksi()
    
    while True:
        print("\n--- DAFTAR MENU TERSEDIA ---")
        for i, p in enumerate(tersedia, 1):
            print(f"{i}. [{p['kategori_produk']}] {p['nama_produk']} - Rp{p['harga']:,.2f}")
        
        try:
            pilihan = int(input("\nPilih nomor menu (0 untuk bayar): "))
            if pilihan == 0:
                break
            if 1 <= pilihan <= len(tersedia):
                jumlah = int(input("Masukkan jumlah pesanan: "))
                if jumlah <= 0:
                    print("[ERROR] Jumlah harus lebih dari 0!")
                    continue
                
                transaksi.tambah_pesanan(tersedia[pilihan-1], jumlah)
                print(f"[+] {tersedia[pilihan-1]['nama_produk']} ditambahkan ke pesanan.")
            else:
                print("[ERROR] Nomor menu tidak valid!")
        except ValueError:
            print("\n[ERROR EXCEPTION] Input yang Anda masukkan bukan angka!")

    transaksi.simpan_dan_bayar()

def menu_input_produk():
    print("\n--- INPUT PRODUK BARU ---")
    nama = input("Nama Produk: ")
    
    print("Kategori (1. Makanan Utama, 2. Apetizer, 3. Minuman)")
    kat_input = input("Pilih Kategori (1/2/3): ")
    kat_map = {"1": "Makanan Utama", "2": "Apetizer", "3": "Minuman"}
    kategori = kat_map.get(kat_input, "Makanan Utama")
    
    try:
        harga = float(input("Harga Produk: Rp"))
        Produk.input_produk_baru(nama, kategori, harga, 'Tersedia')
    except ValueError:
        print("\n[ERROR EXCEPTION] Harga harus berupa angka!")

def menu_update_stok():
    produk_list = Produk.tampilkan_menu()
    print("\n--- UPDATE STOK PRODUK ---")
    print(f"{'ID':<4} | {'Nama Produk':<20} | {'Status Saat Ini'}")
    print("-" * 45)
    for p in produk_list:
        print(f"{p['id_produk']:<4} | {p['nama_produk']:<20} | {p['status_stok']}")
    
    try:
        id_prod = int(input("\nMasukkan ID Produk yang akan diupdate: "))
        print("Pilih Status Baru (1. Tersedia, 2. Habis)")
        stat_input = input("Pilihan (1/2): ")
        status_baru = "Habis" if stat_input == "2" else "Tersedia"
        
        Produk.update_status_stok(id_prod, status_baru)
    except ValueError:
        print("\n[ERROR EXCEPTION] ID harus berupa angka!")

if __name__ == "__main__":
    main()
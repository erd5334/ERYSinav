# ERYSınav - Sınav Yönetim Sistemi

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![CustomTkinter](https://img.shields.io/badge/GUI-CustomTkinter-5C85D6)](https://github.com/TomSchimansky/CustomTkinter)
[![SQLAlchemy](https://img.shields.io/badge/ORM-SQLAlchemy-red)](https://sqlalchemy.org)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

**ERYSınav**, Recep Tayyip Erdoğan Üniversitesi için geliştirilmiş, modern ve kullanımı kolay bir **Sınav Yönetim Sistemi** masaüstü uygulamasıdır.

![Uygulama Ekranı](data/images/screenshot.png)

---

## 🚀 Özellikler

- 📝 **Soru Bankası Yönetimi** – Soru ekleme, düzenleme, silme; görsel ve OCR desteği
- 📄 **Sınav Oluşturma** – Otomatik Word belgesi çıktısı, cevap anahtarı üretimi
- 📚 **Ders Yönetimi** – Dersler ve bölümler bazında soru havuzu
- 📊 **İstatistikler** – Soru kullanım istatistikleri ve grafikler
- ⚙️ **Ayarlar** – Tema (koyu/açık), yedekleme, Tesseract OCR yapılandırması
- 🔒 **Otomatik Yedekleme** – Çıkışta ve belirli aralıklarla SQLite veritabanını yedekler
- 📥 **Toplu İçe Aktarma** – Word/PDF dosyalarından soru ayrıştırma

---

## 🛠 Kurulum

### Gereksinimler

- Python **3.10** veya üzeri
- [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki) (isteğe bağlı, OCR özelliği için)

### Adımlar

```bash
# Repoyu klonla
git clone https://github.com/KULLANICI_ADI/ERYSinav.git
cd ERYSinav

# Sanal ortam oluştur (önerilir)
python -m venv .venv
.venv\Scripts\activate      # Windows
# veya
source .venv/bin/activate   # Linux/macOS

# Bağımlılıkları kur
pip install -r requirements.txt

# Uygulamayı başlat
python main.py
```

---

## 📦 Bağımlılıklar

| Paket | Açıklama |
|---|---|
| `customtkinter` | Modern Tkinter GUI çerçevesi |
| `Pillow` | Görsel işleme |
| `SQLAlchemy` | Veritabanı ORM |
| `pandas` | Veri analizi ve dışa aktarma |
| `openpyxl` | Excel desteği |
| `python-docx` | Word belgesi oluşturma |
| `pytesseract` | OCR (Optik Karakter Tanıma) |
| `pypdf` | PDF okuma ve ayrıştırma |

---

## 📁 Proje Yapısı

```
ERYSinav/
├── main.py               # Giriş noktası
├── config.py             # Uygulama ayarları
├── requirements.txt      # Python bağımlılıkları
├── gui/
│   ├── main_window.py    # Ana pencere
│   ├── questions_page.py # Soru yönetimi sayfası
│   ├── exams_page.py     # Sınav sayfası
│   ├── courses_page.py   # Ders sayfası
│   ├── statistics_page.py# İstatistik sayfası
│   ├── settings_page.py  # Ayarlar sayfası
│   └── ...
├── database/
│   ├── models.py         # SQLAlchemy modelleri
│   └── database.py       # Veritabanı yöneticisi
├── services/
│   └── word_generator.py # Word belgesi üretici
├── utils/
│   ├── document_parser.py# Word/PDF ayrıştırıcı
│   ├── image_handler.py  # Görsel işlemleri
│   └── ocr_helper.py     # OCR yardımcısı
└── data/
    ├── templates/        # Word şablonları
    ├── exports/          # Dışa aktarılan dosyalar
    └── backups/          # Veritabanı yedekleri
```

---

## ⚙️ Tesseract OCR Kurulumu (İsteğe Bağlı)

OCR özelliğini kullanmak için Tesseract'ı yükleyin:

1. [Tesseract İndir](https://github.com/UB-Mannheim/tesseract/wiki) (Windows için)
2. Kurulumdan sonra Ayarlar sayfasından Tesseract yolunu belirtin.

---

## 🤝 Katkıda Bulunma

Pull request'ler memnuniyetle karşılanır. Büyük değişiklikler için lütfen önce bir issue açın.

---

## 👨‍💻 Geliştirici

**Er Yazılım** – [eryazilimci.com](https://eryazilimci.com/)

---

## 📜 Lisans

Bu proje [MIT Lisansı](LICENSE) altında dağıtılmaktadır.

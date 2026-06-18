"""
Veritabanına örnek veri ekler:
  - 3 ders
  - Her derse 120 soru (40 Vize, 40 Final, 40 Genel)
  - Zorluk: kolay/orta/zor karışık

Çalıştır: py seed_data.py
"""
import sys
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import config
from database.models import Base, Course, Question
from database import db_manager

# ─────────────────────────────────────────────────────────────────
# Ders tanımları
# ─────────────────────────────────────────────────────────────────
COURSES = [
    {
        "code":       "VYP101",
        "name":       "Veri Yapıları ve Algoritmalar",
        "department": "Bilgisayar Mühendisliği",
        "instructor": "Dr. Ahmet Yılmaz",
    },
    {
        "code":       "NYP201",
        "name":       "Nesne Yönelimli Programlama",
        "department": "Bilgisayar Mühendisliği",
        "instructor": "Dr. Ayşe Kaya",
    },
    {
        "code":       "VTY301",
        "name":       "Veritabanı Yönetim Sistemleri",
        "department": "Bilgisayar Mühendisliği",
        "instructor": "Dr. Mehmet Demir",
    },
]

# ─────────────────────────────────────────────────────────────────
# Soru şablonları — her ders için ayrı
# ─────────────────────────────────────────────────────────────────

def vyp_question(i: int, q_type: str, difficulty: str) -> dict:
    """Veri Yapıları ve Algoritmalar sorusu üret."""
    topics_vize = [
        "Diziler ve Listeler", "Yığın (Stack)", "Kuyruk (Queue)",
        "Bağlı Liste", "Çift Yönlü Liste", "Zaman Karmaşıklığı"
    ]
    topics_final = [
        "İkili Arama Ağacı", "AVL Ağacı", "Heap Yapısı",
        "Graf Teorisi", "BFS / DFS", "Dinamik Programlama"
    ]
    topics_genel = [
        "Sıralama Algoritmaları", "Arama Algoritmaları",
        "Öz Yinelemeli Fonksiyonlar", "Big-O Notasyonu"
    ]
    topic_pool = (topics_vize if q_type == "Vize"
                  else topics_final if q_type == "Final"
                  else topics_genel)
    topic = random.choice(topic_pool)

    all_answers = ["A", "B", "C", "D"]
    correct = random.choice(all_answers)

    base_options = {
        "A": f"O(1)",
        "B": f"O(n)",
        "C": f"O(n log n)",
        "D": f"O(n²)",
    }

    q_templates = {
        "Diziler ve Listeler": f"Bir dizi yapısında {i}. indisteki elemana erişimin zaman karmaşıklığı nedir?",
        "Yığın (Stack)": f"LIFO ilkesine göre çalışan yığın ({i}. soru): Push işleminin ortalama karmaşıklığı nedir?",
        "Kuyruk (Queue)": f"Dairesel kuyrukta ({i}. soru) silme işleminin zaman karmaşıklığı nedir?",
        "Bağlı Liste": f"Tekil bağlı listede ({i}. soru) sona ekleme işleminin karmaşıklığı nedir?",
        "Çift Yönlü Liste": f"Çift yönlü bağlı listede ({i}. soru) baştan silmenin karmaşıklığı nedir?",
        "Zaman Karmaşıklığı": f"Bir döngü içinde başka bir döngü varsa ({i}. soru) toplam karmaşıklık nedir?",
        "İkili Arama Ağacı": f"İkili arama ağacında ({i}. soru) en iyi durum arama karmaşıklığı nedir?",
        "AVL Ağacı": f"AVL ağacında ({i}. soru) ekleme işlemi sonrası denge sağlama karmaşıklığı nedir?",
        "Heap Yapısı": f"Max-Heap'te ({i}. soru) en büyük elemanı bulma karmaşıklığı nedir?",
        "Graf Teorisi": f"Komşuluk listesiyle temsil edilen bir grafta ({i}. soru) DFS'nin karmaşıklığı nedir?",
        "BFS / DFS": f"BFS algoritması ({i}. soru) hangi veri yapısını kullanır?",
        "Dinamik Programlama": f"Fibonacci sayısının DP yöntemiyle hesaplanmasında ({i}. soru) zaman karmaşıklığı nedir?",
        "Sıralama Algoritmaları": f"Merge Sort algoritmasının ({i}. soru) ortalama karmaşıklığı nedir?",
        "Arama Algoritmaları": f"Sıralı dizide ikili arama ({i}. soru) en kötü durumda kaç adım alır?",
        "Öz Yinelemeli Fonksiyonlar": f"n! hesaplayan özyinelemeli fonksiyonun ({i}. soru) alan karmaşıklığı nedir?",
        "Big-O Notasyonu": f"f(n) = 3n² + 2n + 1 fonksiyonunun ({i}. soru) Big-O notasyonu nedir?",
    }
    q_text = q_templates.get(topic, f"Veri yapıları ve algoritmalar sorusu #{i} — {topic}")

    option_pool = {
        "BFS / DFS": {
            "A": "Kuyruk (Queue)", "B": "Yığın (Stack)",
            "C": "Ağaç (Tree)", "D": "Bağlı Liste",
        },
    }
    options = option_pool.get(topic, base_options)
    correct_answer = random.choice(list(options.keys()))
    return {
        "question_text": q_text,
        "option_a": options.get("A", "O(1)"),
        "option_b": options.get("B", "O(n)"),
        "option_c": options.get("C", "O(n log n)"),
        "option_d": options.get("D", "O(n²)"),
        "correct_answer": correct_answer,
        "difficulty": difficulty,
        "question_type": q_type,
        "topic": topic,
        "tags": f"{q_type.lower()},{difficulty}",
    }


def nyp_question(i: int, q_type: str, difficulty: str) -> dict:
    """Nesne Yönelimli Programlama sorusu üret."""
    topics_vize = [
        "Sınıf ve Nesne", "Kapsülleme", "Yapıcı Metotlar",
        "Erişim Belirleyiciler", "Metot Aşırı Yükleme"
    ]
    topics_final = [
        "Kalıtım", "Çok Biçimlilik", "Soyut Sınıflar",
        "Arayüzler (Interface)", "Tasarım Desenleri"
    ]
    topics_genel = [
        "UML Diyagramları", "Yazılım Geliştirme İlkeleri",
        "SOLID Prensipleri", "Nesne Ömrü"
    ]
    topic_pool = (topics_vize if q_type == "Vize"
                  else topics_final if q_type == "Final"
                  else topics_genel)
    topic = random.choice(topic_pool)

    q_templates = {
        "Sınıf ve Nesne": f"Aşağıdakilerden hangisi ({i}. soru) sınıf ile nesne arasındaki temel farkı doğru ifade eder?",
        "Kapsülleme": f"Kapsülleme ({i}. soru) hangi temel amacı gerçekleştirir?",
        "Yapıcı Metotlar": f"Python'da __init__ metodu ({i}. soru) hangi durumda çağrılır?",
        "Erişim Belirleyiciler": f"'private' erişim belirleyicisi ({i}. soru) hangi kapsamda erişim sağlar?",
        "Metot Aşırı Yükleme": f"Aşırı yükleme (overloading) ile ({i}. soru) ne sağlanır?",
        "Kalıtım": f"Bir alt sınıf ({i}. soru) üst sınıftan hangi öğeleri miras alır?",
        "Çok Biçimlilik": f"Çok biçimlilik (polymorphism) ({i}. soru) hangi avantajı sağlar?",
        "Soyut Sınıflar": f"Soyut sınıf ({i}. soru) hangi özelliğe sahiptir?",
        "Arayüzler (Interface)": f"Bir arayüz ({i}. soru) hangi zorunluluğu getirir?",
        "Tasarım Desenleri": f"Singleton deseni ({i}. soru) hangi problemi çözer?",
        "UML Diyagramları": f"UML sınıf diyagramında '{i}. bağlantı' hangi ilişkiyi gösterir?",
        "Yazılım Geliştirme İlkeleri": f"DRY (Don't Repeat Yourself) prensibi ({i}. soru) ne anlama gelir?",
        "SOLID Prensipleri": f"Tek Sorumluluk Prensibi (SRP) ({i}. soru) için hangisi doğrudur?",
        "Nesne Ömrü": f"Bir nesnenin ({i}. soru) bellekten temizlenmesi hangi mekanizma ile gerçekleşir?",
    }
    q_text = q_templates.get(topic, f"Nesne yönelimli programlama sorusu #{i} — {topic}")

    options_pool = {
        "Sınıf ve Nesne": {
            "A": "Sınıf, bellek alanıdır; nesne, şablondur",
            "B": "Sınıf, şablondur; nesne, sınıfın örneğidir",
            "C": "Her ikisi de aynı şeydir",
            "D": "Nesne, birden fazla sınıf içerebilir",
        },
        "Kapsülleme": {
            "A": "Verinin gizlenmesi ve dışarıdan erişimin kontrol edilmesi",
            "B": "Kalıtımla yeni sınıf türetmek",
            "C": "Aynı metodun farklı parametrelerle kullanımı",
            "D": "Bir nesnenin birden fazla türde davranması",
        },
        "Kalıtım": {
            "A": "Yalnızca public metotlar",
            "B": "Yalnızca private alanlar",
            "C": "Üst sınıftaki tüm üyeler (erişim belirleyiciye göre)",
            "D": "Hiçbir şey miras alınmaz",
        },
        "Singleton deseni": {
            "A": "Birden fazla nesne oluşturmak",
            "B": "Yalnızca bir nesne örneği oluşturulmasını garanti eder",
            "C": "Nesnelerin kopyalanması",
            "D": "Bağımlılıkları çözmek",
        },
    }
    options = options_pool.get(topic, {
        "A": f"Seçenek A — {topic} #{i}",
        "B": f"Seçenek B — {topic} #{i}",
        "C": f"Seçenek C — {topic} #{i}",
        "D": f"Seçenek D — {topic} #{i}",
    })
    # Doğru cevaplar (ilk seçenek veya rastgele)
    correct_map = {
        "Sınıf ve Nesne": "B",
        "Kapsülleme": "A",
        "Kalıtım": "C",
    }
    correct_answer = correct_map.get(topic, random.choice(["A", "B", "C", "D"]))
    return {
        "question_text": q_text,
        "option_a": options.get("A", f"A şıkkı {i}"),
        "option_b": options.get("B", f"B şıkkı {i}"),
        "option_c": options.get("C", f"C şıkkı {i}"),
        "option_d": options.get("D", f"D şıkkı {i}"),
        "correct_answer": correct_answer,
        "difficulty": difficulty,
        "question_type": q_type,
        "topic": topic,
        "tags": f"{q_type.lower()},{difficulty}",
    }


def vty_question(i: int, q_type: str, difficulty: str) -> dict:
    """Veritabanı Yönetim Sistemleri sorusu üret."""
    topics_vize = [
        "İlişkisel Model", "SQL Temelleri", "DDL Komutları",
        "DML Komutları", "Normalizasyon (1NF-2NF)", "Anahtarlar"
    ]
    topics_final = [
        "Normalizasyon (3NF-BCNF)", "Transaction Yönetimi",
        "İndeksleme", "Stored Procedure", "Trigger", "View"
    ]
    topics_genel = [
        "DBMS Mimarisi", "Varlık-İlişki Modeli",
        "Veri Bütünlüğü", "Yedekleme ve Kurtarma"
    ]
    topic_pool = (topics_vize if q_type == "Vize"
                  else topics_final if q_type == "Final"
                  else topics_genel)
    topic = random.choice(topic_pool)

    q_templates = {
        "İlişkisel Model": f"İlişkisel modelde ({i}. soru) bir 'tuple' neyi ifade eder?",
        "SQL Temelleri": f"SELECT sorgusunda ({i}. soru) WHERE ve HAVING farkı nedir?",
        "DDL Komutları": f"CREATE TABLE komutu ({i}. soru) hangi kategoriye girer?",
        "DML Komutları": f"INSERT, UPDATE ve DELETE komutları ({i}. soru) hangi kategoridedir?",
        "Normalizasyon (1NF-2NF)": f"1NF kuralına göre ({i}. soru) bir tabloda ne olmamalıdır?",
        "Anahtarlar": f"Primary Key ile Unique Key arasındaki ({i}. soru) temel fark nedir?",
        "Normalizasyon (3NF-BCNF)": f"3NF'de ({i}. soru) hangi bağımlılık ortadan kaldırılır?",
        "Transaction Yönetimi": f"ACID özelliklerinden ({i}. soru) 'Isolation' ne anlama gelir?",
        "İndeksleme": f"B-Tree indeksi ({i}. soru) hangi durumlarda performansı artırır?",
        "Stored Procedure": f"Stored Procedure ile ({i}. soru) ne kazanılır?",
        "Trigger": f"AFTER INSERT trigger ({i}. soru) ne zaman tetiklenir?",
        "View": f"View ile ({i}. soru) neyin elde edilmesi amaçlanır?",
        "DBMS Mimarisi": f"Üç katmanlı DBMS mimarisinde ({i}. soru) hangi katman kullanıcıya en yakındır?",
        "Varlık-İlişki Modeli": f"ER diyagramında zayıf varlık ({i}. soru) nasıl gösterilir?",
        "Veri Bütünlüğü": f"Referans bütünlüğü ({i}. soru) hangi kısıt türüyle sağlanır?",
        "Yedekleme ve Kurtarma": f"Tam yedekleme ile artımlı yedekleme ({i}. soru) arasındaki fark nedir?",
    }
    q_text = q_templates.get(topic, f"Veritabanı sorusu #{i} — {topic}")

    options_pool = {
        "DDL Komutları": {
            "A": "Data Manipulation Language",
            "B": "Data Definition Language",
            "C": "Data Control Language",
            "D": "Data Query Language",
        },
        "DML Komutları": {
            "A": "Data Definition Language",
            "B": "Data Control Language",
            "C": "Data Manipulation Language",
            "D": "Data Query Language",
        },
        "Transaction Yönetimi": {
            "A": "İşlemlerin kalıcı olması",
            "B": "İşlemlerin birbirinden bağımsız yürütülmesi",
            "C": "İşlemlerin atomik olması",
            "D": "Veritabanının tutarlı kalması",
        },
    }
    options = options_pool.get(topic, {
        "A": f"Seçenek A — {topic} #{i}",
        "B": f"Seçenek B — {topic} #{i}",
        "C": f"Seçenek C — {topic} #{i}",
        "D": f"Seçenek D — {topic} #{i}",
    })
    correct_map = {
        "DDL Komutları": "B",
        "DML Komutları": "C",
        "Transaction Yönetimi": "B",
    }
    correct_answer = correct_map.get(topic, random.choice(["A", "B", "C", "D"]))
    return {
        "question_text": q_text,
        "option_a": options.get("A", f"A şıkkı {i}"),
        "option_b": options.get("B", f"B şıkkı {i}"),
        "option_c": options.get("C", f"C şıkkı {i}"),
        "option_d": options.get("D", f"D şıkkı {i}"),
        "correct_answer": correct_answer,
        "difficulty": difficulty,
        "question_type": q_type,
        "topic": topic,
        "tags": f"{q_type.lower()},{difficulty}",
    }


QUESTION_GENERATORS = {
    "VYP101": vyp_question,
    "NYP201": nyp_question,
    "VTY301": vty_question,
}

DIFFICULTIES = ["easy", "easy", "medium", "medium", "medium", "hard"]


def generate_questions(course_code: str, course_id: int, count_per_type: int = 40):
    """Her tür için count_per_type adet soru üret, toplam 3×count_per_type."""
    generator = QUESTION_GENERATORS[course_code]
    questions = []
    global_i = 1
    for q_type in ["Vize", "Final", "Genel"]:
        for j in range(count_per_type):
            difficulty = random.choice(DIFFICULTIES)
            data = generator(global_i, q_type, difficulty)
            questions.append(Question(
                course_id=course_id,
                question_text=data["question_text"],
                option_a=data["option_a"],
                option_b=data["option_b"],
                option_c=data["option_c"],
                option_d=data["option_d"],
                correct_answer=data["correct_answer"],
                difficulty=data["difficulty"],
                question_type=data["question_type"],
                topic=data["topic"],
                tags=data["tags"],
                is_active=True,
            ))
            global_i += 1
    return questions


def main():
    print("=" * 60)
    print("ERYSinav -- Seed Data")
    print("=" * 60)

    total_added = 0
    total_skipped = 0

    with db_manager.session_scope() as session:
        for course_def in COURSES:
            # Dersi ekle ya da var olanı bul
            existing = session.query(Course).filter_by(code=course_def["code"]).first()
            if existing:
                course = existing
                print(f"  [VAR] Ders zaten var: {course.code} -- {course.name}")
            else:
                course = Course(
                    code=course_def["code"],
                    name=course_def["name"],
                    department=course_def["department"],
                    instructor=course_def["instructor"],
                    is_active=True,
                )
                session.add(course)
                session.flush()  # id almak için
                print(f"  [YEN] Ders eklendi: {course.code} -- {course.name}")

            # Bu derse ait mevcut soru sayısı
            existing_count = session.query(Question).filter_by(
                course_id=course.id, is_active=True
            ).count()
            print(f"    Mevcut soru sayisi: {existing_count}")

            if existing_count >= 120:
                print(f"    [ATLA] Yeterli soru var, atlanıyor.")
                total_skipped += 120
                continue

            # Soruları üret ve ekle
            questions = generate_questions(course.code, course.id, count_per_type=40)
            for q in questions:
                session.add(q)
            print(f"    [OK] {len(questions)} soru eklendi (40 Vize + 40 Final + 40 Genel)")
            total_added += len(questions)

    print()
    print(f"Toplam eklenen soru : {total_added}")
    print(f"Toplam atlanan soru : {total_skipped}")
    print("Islem tamamlandi.")


if __name__ == "__main__":
    main()

import fitz  # PyMuPDF
import os
import cv2
import numpy as np

class PDFConverter:
    @staticmethod
    def score_angle(thresh_img, angle):
        (h, w) = thresh_img.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        rotated = cv2.warpAffine(thresh_img, M, (w, h), flags=cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))
        proj = np.sum(rotated, axis=1)
        return np.var(proj)

    @staticmethod
    def deskew(image):
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray_inv = cv2.bitwise_not(gray)
        thresh = cv2.threshold(gray_inv, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]
        
        # Sizin asıl algoritmanız: Projeksiyon Varyans Analizi. (Bu Hough Lines'tan optik formlar için 10 kat daha hassastır)
        coarse_angles = np.arange(-5.0, 5.0, 0.5)
        best_coarse = 0
        max_score = 0
        for a in coarse_angles:
            score = PDFConverter.score_angle(thresh, a)
            if score > max_score:
                max_score = score
                best_coarse = a
                
        fine_angles = np.arange(best_coarse - 0.5, best_coarse + 0.5, 0.05)
        best_angle = 0
        max_score = 0
        for a in fine_angles:
            score = PDFConverter.score_angle(thresh, a)
            if score > max_score:
                max_score = score
                best_angle = a
                
        # Eğer çok çok küçükse resmin kalitesi bozulmasın diye hiç elleme
        if abs(best_angle) <= 0.01:
            return image
            
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, best_angle, 1.0)
        # BORDER_REPLICATE ile kenarlarda siyah boşlukları önle
        rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        return rotated

    @staticmethod
    def convert_to_images(pdf_path, output_dir, dpi=300, engine=None, omr_params=None, on_progress=None):
        """PDF sayfalarını yüksek çözünürlüklü resimlere dönüştürür ve otomatik eğiklik düzeltme (deskew) uygular."""
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        image_paths = []
        
        for i in range(total_pages):
            page = doc.load_page(i)
            
            # Yüksek kalite için Matrix/DPI ayarı
            zoom = dpi / 72
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)
            
            # PyMuPDF Pixmap verisini Numpy ve OpenCV formatına çevir
            img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            
            if pix.n == 4:
                img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
            elif pix.n == 3:
                img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            else:
                img_cv = cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)

            # Daha güçlü ve akıllı eğiklik düzeltme uygula!
            corrected_img = PDFConverter.deskew(img_cv)
            
            # Öğrenci numarasına göre isim belirleme
            student_no = None
            if engine and omr_params:
                try:
                    student_no = engine.identify_student_no(corrected_img, *omr_params)
                except:
                    student_no = None
            
            if student_no:
                output_filename = f"{student_no}.jpg"
            else:
                output_filename = os.path.basename(pdf_path).replace(".pdf", f"_{i+1}.jpg")
                
            output_path = os.path.join(output_dir, output_filename)
            
            # Düzeltilmiş resmi kaydet
            is_success, buffer = cv2.imencode(".jpg", corrected_img)
            if is_success:
                with open(output_path, "wb") as f:
                    f.write(buffer.tobytes())
            
            image_paths.append(output_path)
            
            if on_progress:
                on_progress(int((i + 1) / total_pages * 100))
            
        doc.close()
        return image_paths

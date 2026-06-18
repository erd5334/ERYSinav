import logging
from pathlib import Path
from PIL import Image
import shutil
import config

logger = logging.getLogger(__name__)

class ImageHandler:
    """Resim işleme sınıfı"""

    @staticmethod
    def save_image(source_path, course_code, question_number, image_type='question'):
        try:
            source = Path(source_path)
            if not source.exists():
                raise FileNotFoundError(f"Resim bulunamadı: {source_path}")
                
            file_size_mb = source.stat().st_size / 1048576
            if file_size_mb > config.IMAGE_SETTINGS['max_file_size_mb']:
                raise ValueError(
                    f"Resim boyutu çok büyük: {file_size_mb:.2f}MB. Maksimum: {config.IMAGE_SETTINGS['max_file_size_mb']}MB"
                )
                
            if source.suffix.lower() not in config.IMAGE_SETTINGS['allowed_formats']:
                raise ValueError(
                    f"Desteklenmeyen resim formatı: {source.suffix}. İzin verilen formatlar: {', '.join(config.IMAGE_SETTINGS['allowed_formats'])}"
                )
                
            target_dir = config.IMAGES_DIR / course_code
            target_dir.mkdir(parents=True, exist_ok=True)
            
            filename = f"{question_number}_{image_type}{source.suffix.lower()}"
            target_path = target_dir / filename
            
            counter = 1
            while target_path.exists():
                filename = f"{question_number}_{image_type}_{counter}{source.suffix.lower()}"
                target_path = target_dir / filename
                counter += 1
                
            with Image.open(source) as img:
                img = ImageHandler._fix_orientation(img)
                if img.mode in ('RGBA', 'LA', 'P'):
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
                    
                img.save(
                    target_path,
                    quality=config.IMAGE_SETTINGS['compress_quality'],
                    optimize=True
                )
                
            logger.info(f"Resim kaydedildi: {target_path}")
            return str(target_path)
        except Exception as e:
            logger.error(f"Resim kaydetme hatası: {e}")
            raise

    @staticmethod
    def _fix_orientation(img):
        try:
            from PIL import ExifTags
            orientation = None
            for key in ExifTags.TAGS.keys():
                if ExifTags.TAGS[key] == 'Orientation':
                    orientation = key
                    break
                    
            exif = img._getexif()
            if exif and orientation is not None:
                orientation_value = exif.get(orientation)
                if orientation_value == 3:
                    img = img.rotate(180, expand=True)
                elif orientation_value == 6:
                    img = img.rotate(270, expand=True)
                elif orientation_value == 8:
                    img = img.rotate(90, expand=True)
            return img
        except (AttributeError, KeyError, IndexError):
            return img

    @staticmethod
    def create_thumbnail(image_path, size=None):
        if size is None:
            size = config.IMAGE_SETTINGS['thumbnail_size']
        try:
            with Image.open(image_path) as img:
                img = ImageHandler._fix_orientation(img)
                img.thumbnail(size, Image.Resampling.LANCZOS)
                return img.copy()
        except Exception as e:
            logger.error(f"Thumbnail oluşturma hatası: {e}")
            return None

    @staticmethod
    def delete_image(image_path):
        try:
            path = Path(image_path)
            if path.exists():
                path.unlink()
                logger.info(f"Resim silindi: {image_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Resim silme hatası: {e}")
            return False

    @staticmethod
    def get_image_info(image_path):
        try:
            with Image.open(image_path) as img:
                return {
                    'size': img.size,
                    'format': img.format,
                    'mode': img.mode,
                    'file_size': Path(image_path).stat().st_size
                }
        except Exception as e:
            logger.error(f"Resim bilgisi alma hatası: {e}")
            return None

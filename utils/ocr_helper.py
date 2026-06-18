import os
import subprocess
import logging
from pathlib import Path
import config

logger = logging.getLogger(__name__)

class OCRHelper:
    """Windows 10/11 yerel OCR motorunu kullanan yardımcı sınıf"""
    _ps_script_path = None

    @classmethod
    def _ensure_script_exists(cls):
        """PowerShell OCR betiğinin diskte mevcut olmasını sağlar"""
        if cls._ps_script_path and Path(cls._ps_script_path).exists():
            return cls._ps_script_path
            
        script_dir = config.DATA_DIR / 'scripts'
        script_dir.mkdir(parents=True, exist_ok=True)
        cls._ps_script_path = script_dir / 'win_ocr.ps1'
        
        script_content = (
            "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8\n"
            "$imagePath = $args[0]\n"
            "if (-not (Test-Path $imagePath)) {\n"
            "    Write-Error \"File not found: $imagePath\"\n"
            "    exit 1\n"
            "}\n\n"
            "try {\n"
            "    # WinRT bileşenlerini yükle\n"
            "    Add-Type -AssemblyName System.Drawing\n"
            "    [void][System.Reflection.Assembly]::LoadWithPartialName(\"System.Runtime.WindowsRuntime\")\n"
            "    [void][Windows.Storage.Streams.IRandomAccessStream, Windows.Storage, ContentType=WindowsRuntime]\n"
            "    [void][Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType=WindowsRuntime]\n"
            "    [void][Windows.Graphics.Imaging.SoftwareBitmap, Windows.Graphics.Imaging, ContentType=WindowsRuntime]\n"
            "    [void][Windows.Media.Ocr.OcrEngine, Windows.Media.Ocr, ContentType=WindowsRuntime]\n"
            "    [void][Windows.Globalization.Language, Windows.Globalization, ContentType=WindowsRuntime]\n"
            "    \n"
            "    # AsTask generic metodunu al\n"
            "    $asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | \n"
            "        Where-Object { \n"
            "            $_.Name -eq 'AsTask' -and \n"
            "            $_.GetParameters().Count -eq 1 -and \n"
            "            $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' \n"
            "        })[0]\n\n"
            "    function Await-WinRT {\n"
            "        param($WinRtTask, [type]$ResultType)\n"
            "        $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)\n"
            "        $netTask = $asTask.Invoke($null, @($WinRtTask))\n"
            "        $netTask.Wait(-1) | Out-Null\n"
            "        return $netTask.Result\n"
            "    }\n"
            "    \n"
            "    # GDI+ ile resmi aç\n"
            "    $fullPath = [System.IO.Path]::GetFullPath($imagePath)\n"
            "    $bitmap_gdi = [System.Drawing.Bitmap]::FromFile($fullPath)\n"
            "    \n"
            "    # MemoryStream'e kaydet (PNG olarak)\n"
            "    $ms = New-Object System.IO.MemoryStream\n"
            "    $bitmap_gdi.Save($ms, [System.Drawing.Imaging.ImageFormat]::Png)\n"
            "    $ms.Position = 0\n"
            "    $bitmap_gdi.Dispose()\n"
            "    \n"
            "    # .NET stream'den WinRT RandomAccessStream oluştur (Senkron)\n"
            "    $randomAccessStream = [System.IO.WindowsRuntimeStreamExtensions]::AsRandomAccessStream($ms)\n"
            "    \n"
            "    # Bitmap olarak çöz (Asenkron)\n"
            "    $asyncDecoder = [Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($randomAccessStream)\n"
            "    $decoder = Await-WinRT $asyncDecoder ([Windows.Graphics.Imaging.BitmapDecoder])\n"
            "    \n"
            "    # SoftwareBitmap al (Asenkron)\n"
            "    $asyncBitmap = $decoder.GetSoftwareBitmapAsync()\n"
            "    $bitmap = Await-WinRT $asyncBitmap ([Windows.Graphics.Imaging.SoftwareBitmap])\n"
            "    \n"
            "    # Türkçe dil desteğini kontrol et, yoksa varsayılan\n"
            "    $lang = New-Object Windows.Globalization.Language(\"tr-TR\")\n"
            "    if ([Windows.Media.Ocr.OcrEngine]::IsLanguageSupported($lang)) {\n"
            "        $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage($lang)\n"
            "    } else {\n"
            "        $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()\n"
            "    }\n"
            "    \n"
            "    if ($engine -eq $null) {\n"
            "        Write-Error \"OCR motoru oluşturulamadı.\"\n"
            "        exit 1\n"
            "    }\n"
            "    \n"
            "    # Metni tanı (Asenkron)\n"
            "    $asyncOcr = $engine.RecognizeAsync($bitmap)\n"
            "    $result = Await-WinRT $asyncOcr ([Windows.Media.Ocr.OcrResult])\n"
            "    \n"
            "    # Sonucu ekrana yaz\n"
            "    Write-Output $result.Text\n"
            "} catch {\n"
            "    Write-Error $_.Exception.Message\n"
            "    exit 1\n"
            "}\n"
        )
        
        with open(cls._ps_script_path, 'w', encoding='utf-8') as f:
            f.write(script_content)
            
        return cls._ps_script_path

    @classmethod
    def get_text_from_image(cls, image_path) -> str:
        """Resim dosyasından metin okur (OCR)"""
        try:
            image_path_str = str(Path(image_path).resolve())
            if not os.path.exists(image_path_str):
                logger.error(f"OCR resmi bulunamadı: {image_path_str}")
                return ""
                
            script_path = cls._ensure_script_exists()
            cmd = [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script_path),
                image_path_str
            ]
            
            logger.info(f"OCR başlatılıyor: {image_path_str}")
            
            creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                creationflags=creationflags
            )
            
            if result.returncode != 0:
                logger.error(f"PowerShell OCR hatası: {result.stderr}")
                return ""
                
            ocr_text = result.stdout.strip()
            logger.info("OCR başarılı şekilde metin okudu.")
            return ocr_text
        except Exception as e:
            logger.error(f"OCR çalıştırılırken hata oluştu: {e}")
            return ""

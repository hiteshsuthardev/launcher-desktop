import os
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QFileIconProvider
from PySide6.QtCore import QFileInfo

def extract_icon_win32(exe_path: str, output_png_path: str) -> bool:
    """Extracts icon from exe using pywin32 and saves it to a temp BMP, then QPixmap saves to PNG."""
    try:
        import win32gui
        import win32ui
        import win32con
        import win32api
        
        import ctypes

        def _get_hicons(path, size):
            phicon = (ctypes.c_void_p * 1)()
            piconid = (ctypes.c_uint * 1)()
            ret = ctypes.windll.user32.PrivateExtractIconsW(path, 0, size, size, phicon, piconid, 1, 0)
            if ret > 0 and phicon[0]:
                return [phicon[0]]
            return []

        # Try to extract a high-res (256x256) icon first, fallback to standard sizes
        hicons = _get_hicons(exe_path, 256)
        if not hicons:
            hicons = _get_hicons(exe_path, 48)
        if not hicons:
            hicons = _get_hicons(exe_path, 32)

        if not hicons:
            return False

        hicon = hicons[0]
        
        # Determine size
        info = win32gui.GetIconInfo(hicon)
        width, height = 256, 256
        if info[4]: # hbmColor
            bmp_info = win32gui.GetObject(info[4])
            width = bmp_info.bmWidth
            height = bmp_info.bmHeight

        # Get device context of desktop and create a memory DC
        hdc = win32gui.GetDC(0)
        src_dc = win32ui.CreateDCFromHandle(hdc)
        mem_dc = src_dc.CreateCompatibleDC()

        # Create compatible bitmap
        hbmp = win32ui.CreateBitmap()
        hbmp.CreateCompatibleBitmap(src_dc, width, height)
        mem_dc.SelectObject(hbmp)

        # Draw the icon into the memory DC
        win32gui.DrawIconEx(mem_dc.GetSafeHdc(), 0, 0, hicon, width, height, 0, None, win32con.DI_NORMAL)

        # Save to temporary BMP file
        temp_bmp = output_png_path + ".temp.bmp"
        hbmp.SaveBitmapFile(mem_dc, temp_bmp)

        # Cleanup win32 objects
        mem_dc.DeleteDC()
        src_dc.DeleteDC()
        win32gui.ReleaseDC(0, hdc)
        win32gui.DestroyIcon(hicon)

        # Load BMP using QPixmap and save as PNG
        if os.path.exists(temp_bmp):
            pixmap = QPixmap(temp_bmp)
            os.remove(temp_bmp)
            if not pixmap.isNull():
                os.makedirs(os.path.dirname(output_png_path), exist_ok=True)
                pixmap.save(output_png_path, "PNG")
                return True
        return False

    except Exception as e:
        print(f"pywin32 extraction failed for {exe_path}: {e}")
        return False

def extract_icon(exe_path: str, output_png_path: str) -> bool:
    """Extracts icon from exe. Tries pywin32 first, then falls back to QFileIconProvider."""
    # Ensure folder path exists
    os.makedirs(os.path.dirname(output_png_path), exist_ok=True)
    
    # 1. Try pywin32 first
    if extract_icon_win32(exe_path, output_png_path):
        return True
        
    # 2. Fallback to QFileIconProvider
    try:
        provider = QFileIconProvider()
        icon = provider.icon(QFileInfo(exe_path))
        if not icon.isNull():
            pixmap = icon.pixmap(256, 256)
            if not pixmap.isNull():
                pixmap.save(output_png_path, "PNG")
                return True
    except Exception as e:
        print(f"Fallback QFileIconProvider failed: {e}")

    return False

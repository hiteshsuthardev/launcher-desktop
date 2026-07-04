from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QColor

class QRCodeWidget(QWidget):
    def __init__(self, data_str: str = "", parent=None):
        super().__init__(parent)
        self.data_str = data_str
        self.matrix = []
        self.setFixedSize(200, 200)  # Standard square dimensions
        self.update_data(data_str)

    def update_data(self, data_str: str):
        """Generates the boolean module matrix for the given data string."""
        self.data_str = data_str
        if not data_str:
            self.matrix = []
            self.update()
            return
            
        try:
            import qrcode
            # Create QR Code object with minimal border
            qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=1, border=1)
            qr.add_data(data_str)
            qr.make(fit=True)
            self.matrix = qr.get_matrix()
        except Exception as e:
            print(f"[QR CODE ERROR] Failed to generate QR matrix: {e}")
            self.matrix = []
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        
        rect = self.rect()
        
        # Draw a clean, rounded white card background (ensures high contrast scan)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor("#ffffff"))
        painter.drawRoundedRect(rect, 16, 16)
        
        if not self.matrix:
            # Draw placeholder error string
            painter.setPen(QColor("#ef4444"))
            painter.drawText(rect, Qt.AlignCenter, "QR Code Generation Error")
            return
            
        rows = len(self.matrix)
        cols = len(self.matrix[0])
        
        # Calculate padding to center and scale the QR matrix inside the widget
        padding = 12
        usable_w = self.width() - (padding * 2)
        usable_h = self.height() - (padding * 2)
        
        cell_w = usable_w / cols
        cell_h = usable_h / rows
        
        # Draw the black blocks
        painter.setBrush(QColor("#0a0b0d"))  # Dark charcoal QR modules
        for r in range(rows):
            for c in range(cols):
                if self.matrix[r][c]:
                    x = padding + c * cell_w
                    y = padding + r * cell_h
                    # Draw rect with a 0.1px overlap to prevent subpixel rendering grid gaps
                    painter.drawRect(QRectF(x, y, cell_w + 0.1, cell_h + 0.1))

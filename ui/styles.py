APP_STYLE = r"""
QMainWindow {
    background: #f5f7fb;
}

QWidget {
    font-family: "Segoe UI";
    font-size: 10pt;
    color: #172033;
}

QFrame#Card {
    background: white;
    border: 1px solid #e5e9f2;
    border-radius: 18px;
}

QLabel#Title {
    font-size: 25px;
    font-weight: 700;
    color: #101828;
}

QLabel#Subtitle {
    color: #667085;
    font-size: 11pt;
}

QLabel#SectionTitle {
    font-size: 13pt;
    font-weight: 700;
    color: #101828;
}

QLabel#DropTitle {
    font-size: 15pt;
    font-weight: 700;
}

QLabel#DropSubtitle {
    color: #667085;
}

QFrame#DropZone {
    background: #f8faff;
    border: 2px dashed #b8c4dc;
    border-radius: 15px;
}

QFrame#DropZone[dragging="true"] {
    border: 2px dashed #4f46e5;
    background: #eef2ff;
}

QPushButton {
    min-height: 40px;
    border-radius: 9px;
    padding: 0 18px;
    font-weight: 600;
}

QPushButton#Primary {
    background: #4f46e5;
    color: white;
    border: none;
}

QPushButton#Primary:hover {
    background: #4338ca;
}

QPushButton#Primary:disabled {
    background: #a5b4fc;
}

QPushButton#Secondary {
    background: #f2f4f7;
    color: #344054;
    border: 1px solid #d0d5dd;
}

QPushButton#Secondary:hover {
    background: #e4e7ec;
}

QComboBox {
    min-height: 38px;
    border: 1px solid #d0d5dd;
    border-radius: 8px;
    padding: 0 10px;
    background: white;
}

QComboBox:hover {
    border: 1px solid #98a2b3;
}

QComboBox:focus {
    border: 1px solid #4f46e5;
}

QProgressBar {
    min-height: 12px;
    max-height: 12px;
    border: none;
    border-radius: 6px;
    background: #eaecf0;
    text-align: center;
}

QProgressBar::chunk {
    border-radius: 6px;
    background: #4f46e5;
}

QTextEdit#Log,
QPlainTextEdit#Log {
    background: #101828;
    color: #d1d5db;
    border: none;
    border-radius: 10px;
    padding: 8px;
    font-family: Consolas;
    font-size: 9pt;
}

QLabel#Muted {
    color: #667085;
}

QLabel#Success {
    color: #027a48;
    font-weight: 600;
}

QLabel#Error {
    color: #b42318;
    font-weight: 600;
}
"""
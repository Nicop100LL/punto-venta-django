import base64
from barcode import Code128
from barcode.writer import SVGWriter
from io import BytesIO


def code128_svg_base64(code):
    buffer = BytesIO()
    Code128(code, writer=SVGWriter()).write(buffer)

    svg_bytes = buffer.getvalue()

    return base64.b64encode(svg_bytes).decode("utf-8")

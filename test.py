from flask import Flask, Response
from PIL import Image, ImageDraw
import io
import time

app = Flask(__name__)

COLORS = [
    ("blue", (0, 0, 255)),
    ("red", (255, 0, 0)),
    ("green", (0, 255, 0)),
]


def create_frame(color_name, rgb):
    img = Image.new("RGB", (640, 480), rgb)

    draw = ImageDraw.Draw(img)
    draw.text((260, 220), color_name.upper(), fill=(255, 255, 255))

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()


def video_stream():
    index = 0

    while True:
        color_name, rgb = COLORS[index]
        frame = create_frame(color_name, rgb)

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" +
            frame +
            b"\r\n"
        )

        index = (index + 1) % len(COLORS)
        time.sleep(1)


@app.route("/")
def home():
    return """
    <html>
      <body>
        <h2>Fake Video Stream</h2>
        <img src="/video_feed" width="640" height="480">
      </body>
    </html>
    """


@app.route("/video_feed")
def video_feed():
    return Response(
        video_stream(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
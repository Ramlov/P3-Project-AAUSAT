from flask import Flask, Response
import cv2

app = Flask(__name__)

def generate_frames():
    # Use your provided RTSP URL
    rtsp_url = 'rtsp://studuser:Studentspace@localhost:5000/h264Preview_01_main'
    cap = cv2.VideoCapture(rtsp_url)

    while True:
        success, frame = cap.read()
        if not success:
            break
        else:
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


@app.route('/video_feed')
def video_feed():
    # Replace 'your_rtsp_stream_url' with your actual RTSP stream URL
    return Response(generate_frames('your_rtsp_stream_url'),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/')
def index():
    # Returns a simple HTML template that displays the video stream
    return """
    <html>
    <body>
        <h1>RTSP Stream</h1>
        <img src="/video_feed" width="640" height="480" />
    </body>
    </html>
    """

if __name__ == '__main__':
    app.run(debug=True, threaded=True, port=50001)
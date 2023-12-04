from flask import Response, Flask, render_template
import threading
import argparse 
import datetime, time
import imutils
import cv2

outputFrame = None
lock = threading.Lock()
 
app = Flask(__name__)
 
source = "rtsp://studuser:Studentspace@roof-aausat.space.aau.dk:554/h264Preview_01_main"
cap = cv2.VideoCapture(source)
time.sleep(2.0)

@app.route("/")
def index():
    # return the rendered template
    return render_template("index.html")

def stream(frameCount):
    global outputFrame, lock
    if cap.isOpened():
        # cv2.namedWindow(('IP camera DEMO'), cv2.WINDOW_AUTOSIZE)
        while True:
            ret_val, frame = cap.read()
            if frame.shape:
                frame = cv2.resize(frame, (640,360))
                with lock:
                    outputFrame = frame.copy()
            else:
                continue 
    else:
        print('camera open failed')

def generate():
    # grab global references to the output frame and lock variables
    global outputFrame, lock
 
    # loop over frames from the output stream
    while True:
        # wait until the lock is acquired
        with lock:
            # check if the output frame is available, otherwise skip
            # the iteration of the loop
            if outputFrame is None:
                continue
 
            # encode the frame in JPEG format
            (flag, encodedImage) = cv2.imencode(".jpg", outputFrame)
 
            # ensure the frame was successfully encoded
            if not flag:
                continue
 
        # yield the output frame in the byte format
        yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
            bytearray(encodedImage) + b'\r\n')

@app.route("/video_feed")
def video_feed():
    return Response(generate(),
        mimetype = "multipart/x-mixed-replace; boundary=frame")

if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument("-i", "--ip", type=str, required=False, default='192.168.2.226',
        help="ip address of the device")
    ap.add_argument("-o", "--port", type=int, required=False, default=8000, 
        help="ephemeral port number of the server (1024 to 65535)")
    ap.add_argument("-f", "--frame-count", type=int, default=32,
        help="# of frames used to construct the background model")
    args = vars(ap.parse_args())

    t = threading.Thread(target=stream, args=(args["frame_count"],))
    t.daemon = True
    t.start()
 
    # start the flask app
    app.run(host=args["ip"], port=args["port"], debug=True,
        threaded=True, use_reloader=False)
 
# release the video stream pointer
cap.release()
cv2.destroyAllWindows()
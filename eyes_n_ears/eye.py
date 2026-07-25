import cv2
from picamera2 import Picamera2


class Eye:
    def __init__(self, on_frame):
        """
        Initialize the Eye module.

        Args:
            on_frame: callback(frame: bytes) - called with each compressed JPEG frame
        """
        self.on_frame = on_frame

        self.camera = Picamera2()
        config = self.camera.create_video_configuration(
            main={"size": (320, 240), "format": "RGB888"}
        )
        self.camera.configure(config)

        self.is_running = False
        print("Eye initialized.")

    def start(self):
        self.is_running = True
        self.camera.start()
        print("Eye started.")

        try:
            while self.is_running:
                frame = self.camera.capture_array()
                _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 30])
                self.on_frame(jpeg.tobytes())

        except Exception as e:
            print(f"Error in Eye: {e}")
        finally:
            self.camera.stop()
            print("Eye stopped.")

    def stop(self):
        self.is_running = False

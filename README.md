# P3-Project-AAUSAT

## Description

The P3-Project-AAUSAT is an innovative project developed by students at Aalborg University. This project is designed to facilitate communication between a ground station system and a satellite using an ESP32 module, alongside a web interface for command and control. The system is structured into distinct components, each responsible for specific tasks such as managing database interactions, executing satellite commands, and streaming video content.

## Project Structure

The project is organized into four main directories, each containing files and subdirectories for their specific functionalities:

### 📦 GS-System
The Ground Station System (GS-System) directory contains the core scripts and requirements for the ground station's operation.
- `helper_functions`: Directory containing utility functions.
- `main.py`: The main Python script for the GS-System operations.
- `requirements.txt`: A file listing all Python dependencies required by the GS-System.

### ESP32
This directory houses the code that runs on the ESP32 module, facilitating satellite communication.
- `GS_easycomm2_controller`: Contains the `GS_easycomm2_controller.ino` script, the main program for the ESP32. Requires a serial connection to a Raspberry Pi to function.

### Frontend
The Frontend directory includes all the necessary files for the web interface, allowing users to interact with the system via a web browser.
- `app.py`: Main Flask application script to run the web service. It connects to the RPI through serial communication when `serial_comm.py` is running with the "TUN" argument.
- `config.json`, `favicon.ico`, `helper_class.py`: Configuration and helper files for the Flask application.
- `static`: Contains static files like JavaScript (`script.js`) and CSS (`style.css`).
- `templates`: HTML templates for the web interface, including pages for auto tracking, manual control, and webcam streaming.

### RaspberryPI
The RaspberryPI directory contains scripts for video streaming, serial communication, and system utilities.
- `hls`: Scripts for hosting a CORS HTTP server (`cors_http_server.py`) and converting RTSP to HLS for webcam streaming (`rtsp_to_hls.sh`).
- `serial_comm.py`: The main script for communication with the ESP32 and socket connections. Supports "MAN" (manual control) and "TUN" (tunnel for web connection) arguments.
- `update_time.py`: Script to update the Raspberry Pi's system time.

### Global Configuration
- `config.json`: A global configuration file used by various components of the system.

## Getting Started

### Dependencies

Ensure you have Python 3.x installed on your system and the Arduino IDE for the ESP32 script. The project's dependencies are listed in the `requirements.txt` files located in the respective directories.

### Setup and Installation

1. **GS-System Setup**: Navigate to the GS-System directory and install the Python dependencies:
   ```bash
   cd GS-System
   pip install -r requirements.txt
   ```
2. **ESP32 Programming**: To program the ESP32, use the Arduino IDE to upload the `GS_easycomm2_controller.ino` script located in the ESP32/GS_easycomm2_controller directory. This script is essential for the ESP32 module's operation and requires a serial connection to a Raspberry Pi to work correctly.

3. **Frontend Setup**: The web interface is managed through the Frontend directory. To start the web service, run the `app.py` script. This requires Python to be installed on your system.
   ```bash
   cd Frontend
   python app.py
   ```
This will start the Flask-based web service, establishing a connection to the Raspberry Pi via serial communication. The connection is necessary for the web service to interact with the Ground Station System and requires that `serial_comm.py` is executed on the Raspberry Pi with the "TUN" argument to enable the tunneling feature for socket connections.

### Raspberry Pi Setup
The Raspberry Pi plays a critical role in the project, handling tasks from video streaming to serial communication with the ESP32. Each script in the RaspberryPI directory is designed for a specific function:
- `hls/cors_http_server.py`: This script sets up a CORS-enabled HTTP server for streaming video content.
- `hls/rtsp_to_hls.sh`: It converts RTSP video streams to HLS format, making it accessible for web streaming.
- `serial_comm.py`: The main script for serial communication with the ESP32, it also manages socket connections for the web interface. It can operate in two modes: "MAN" for manual control through the command line, and "TUN" for establishing a tunnel connection to the web service.
- `update_time.py`: Ensures the Raspberry Pi's clock is synchronized, which is crucial for timing-sensitive operations.

Setup and execution instructions are provided within each script. Follow these guidelines to ensure proper operation of your project components.

### Running the Project
Ensure the ESP32 module is correctly configured and connected to the Raspberry Pi. This setup is crucial for the seamless operation of the ESP32 scripts and their communication with the ground station system.

To start the web service and enable web-based control and monitoring, execute the `app.py` script within the Frontend directory:

```bash
cd Frontend
python app.py
```
Ensure the ESP32 module is correctly configured and connected to the Raspberry Pi. Proper setup is essential for the module's operation and its communication with the ground station system.

To initiate the web service for system control and monitoring, run the `app.py` script located in the Frontend directory:

```bash
cd Frontend
python app.py
```
This command launches the Flask application, providing a user-friendly web interface for system interaction. Through this interface, users can send commands, monitor system status, and receive updates in real-time. It's an essential component for facilitating easy access and control of the ground station system.

## How to Contribute

We welcome contributions from the community. Whether it's improving the codebase, adding new features, or fixing bugs, your contributions are valuable to us. Here's how you can contribute:

1. **Fork the Repository:** Start by forking the project repository to your GitHub account.
2. **Create a Feature Branch:** Create a branch in your forked repository for your contribution (`git checkout -b feature/YourFeatureName`).
3. **Commit Your Changes:** Make your changes in your feature branch and commit them (`git commit -am 'Add some feature'`).
4. **Push to the Branch:** Push your changes to your GitHub repository (`git push origin feature/YourFeatureName`).
5. **Submit a Pull Request:** Go back to the original project repository and submit a pull request from your feature branch to the main branch.

Before starting your contribution, please check the existing issues and pull requests to ensure that you're not duplicating work. For significant changes or new features, it's a good idea to open an issue first to discuss it with the project maintainers.

## License

The project is licensed under the MIT License. This license allows for free use, modification, and distribution of the project, ensuring it remains accessible and beneficial to the community. See the LICENSE file in the project repository for full license text.

## Acknowledgments

Our heartfelt thanks go out to all the contributors who have invested their time and effort into this project. Your contributions, big or small, play a crucial role in its success and continuous improvement.

## Contact Information

If you have any questions, feedback, or would like to contribute to the project, please don't hesitate to reach out. You can file an issue on GitHub for small queries or suggestions.

We're looking forward to seeing how you will contribute to making this project even better!




# File Structure:
```
📦 
│  ├─ GS-System
│  │  ├─ helper_functions
│  │  ├─ main.py
│  │  └─ requirements.txt
│  └─ backend-rpi_tunnel.py
├─ ESP32
│  └─ GS_easycomm2_controller
│     └─ GS_easycomm2_controller.ino
├─ Frontend
│  ├─ app
│  ├─ config.json
│  ├─ favicon.ico
│  ├─ helper_class.py
│  ├─ static
│  │  ├─ script.js
│  │  └─ styles
│  │     └─ style.css
│  └─ templates
│     ├─ autotrack
│     │  └─ autotrack.html
│     ├─ index.html
│     ├─ manual
│     │  └─ manual.html
│     └─ webcam
│        └─ webcam.html
├─ RaspberryPI
│  ├─ hls
│  │  ├─ cors_http_server.py
│  │  └─ rtsp_to_hls.sh
│  ├─ serial_comm.py
│  └─ update_time.py
└─ config.json
```

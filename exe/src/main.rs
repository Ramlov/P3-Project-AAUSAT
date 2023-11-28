use std::process::Command;
use std::env;

fn main() {
    // Path to the app.py file
    let app_path = "/Backend/interface/app.py";

    // Command to run the Flask backend
    let flask_command = Command::new("python")
        .arg(app_path)
        .spawn();

    match flask_command {
        Ok(_) => {
            // Determine the operating system
            let os = env::consts::OS;

            // Declare browser_command as mutable
            let mut browser_command: Command;

            // Command to open the web browser
            browser_command = match os {
                "linux" | "macos" => {
                    let mut cmd = Command::new("xdg-open");
                    cmd.arg("http://127.0.0.1:50005");
                    cmd
                }
                "windows" => {
                    let mut cmd = Command::new("cmd");
                    cmd.arg("/C").arg("start").arg("http://127.0.0.1:50005");
                    cmd
                }
                _ => {
                    eprintln!("Unsupported operating system: {}", os);
                    return;
                }
            };

            match browser_command.spawn() {
                Ok(_) => println!("Web browser opened successfully."),
                Err(err) => eprintln!("Error opening web browser: {}", err),
            }
        }
        Err(err) => eprintln!("Error running Flask backend: {}", err),
    }
}

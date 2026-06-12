// Modified to force tauri/cargo context recompilation and pack new app icon assets.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    tauri::Builder::default()
        .plugin(tauri_plugin_notification::init())
        .setup(|app| {
            // Under production execution, Tauri launches the sidecar binary:
            // let sidecar_command = app.handle().sidecar("ergolearn-backend");
            // if let Ok(sidecar) = sidecar_command {
            //     let (mut rx, mut tx) = sidecar.spawn().expect("failed to spawn sidecar");
            //     // Manage IPC streaming or process handle here
            // }
            
            println!("Tauri main thread successfully initialized.");
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

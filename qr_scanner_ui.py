import customtkinter as ctk
import cv2
from PIL import Image, ImageTk
import threading
import time
import sys

# Configure appearance
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class QRScannerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Fresher Induction - QR Code Scanner")
        self.geometry("1000x600")
        
        # Data storage
        self.scanned_ids = set()
        self.last_scan_time = 0
        self.scan_cooldown = 3.0  # Seconds between scans for same code (if we allowed re-scan, but we don't)
        
        # Grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)  # Sidebar
        self.grid_rowconfigure(0, weight=1)

        # --- Left Side: Camera Feed ---
        self.camera_frame = ctk.CTkFrame(self, corner_radius=10)
        self.camera_frame.grid(row=0, column=0, padx=20, pady=20, sticky="nsew")
        self.camera_frame.grid_rowconfigure(0, weight=1)
        self.camera_frame.grid_columnconfigure(0, weight=1)

        self.camera_label = ctk.CTkLabel(self.camera_frame, text="Starting Camera...", text_color="gray")
        self.camera_label.grid(row=0, column=0, sticky="nsew")

        # --- Right Side: Info Panel ---
        self.info_frame = ctk.CTkFrame(self, width=300, corner_radius=10)
        self.info_frame.grid(row=0, column=1, padx=(0, 20), pady=20, sticky="nsew")
        self.info_frame.grid_propagate(False) # Fix width

        # Status Header
        self.status_label = ctk.CTkLabel(self.info_frame, text="Ready to Scan", font=("Roboto Medium", 20), text_color="#3B8ED0")
        self.status_label.pack(pady=(30, 10), padx=20)

        # Student Details Container
        self.details_container = ctk.CTkFrame(self.info_frame, fg_color="transparent")
        self.details_container.pack(fill="x", padx=20, pady=10)

        self.lbl_name = self.create_detail_label("Name", "---")
        self.lbl_id = self.create_detail_label("ID", "---")
        self.lbl_branch = self.create_detail_label("Branch", "---")

        # History List
        ctk.CTkLabel(self.info_frame, text="Session History", font=("Roboto Medium", 16)).pack(pady=(30, 10), padx=20, anchor="w")
        self.history_textbox = ctk.CTkTextbox(self.info_frame, height=200)
        self.history_textbox.pack(fill="x", padx=20, pady=10)
        self.history_textbox.configure(state="disabled")

        # Reset Button
        self.reset_btn = ctk.CTkButton(self.info_frame, text="Reset Session", command=self.reset_session, fg_color="#C0392B", hover_color="#E74C3C")
        self.reset_btn.pack(pady=20, side="bottom")

        # --- Camera Setup ---
        self.cap = cv2.VideoCapture(0)
        self.detector = cv2.QRCodeDetector()
        self.running = True
        
        self.update_camera()

    def create_detail_label(self, title, value):
        frame = ctk.CTkFrame(self.details_container, fg_color="transparent")
        frame.pack(fill="x", pady=5)
        ctk.CTkLabel(frame, text=title, font=("Roboto", 12), text_color="gray").pack(anchor="w")
        lbl = ctk.CTkLabel(frame, text=value, font=("Roboto Medium", 14))
        lbl.pack(anchor="w")
        return lbl

    def reset_session(self):
        self.scanned_ids.clear()
        self.history_textbox.configure(state="normal")
        self.history_textbox.delete("0.0", "end")
        self.history_textbox.configure(state="disabled")
        self.update_status("Session Reset", "#3B8ED0")
        self.clear_details()

    def clear_details(self):
        self.lbl_name.configure(text="---")
        self.lbl_id.configure(text="---")
        self.lbl_branch.configure(text="---")

    def update_status(self, text, color):
        self.status_label.configure(text=text, text_color=color)

    def parse_qr_data(self, data):
        # Expected format:
        # Name: XXX
        # ID: XXX
        # Branch: XXX
        info = {}
        try:
            lines = data.split('\n')
            for line in lines:
                if ": " in line:
                    key, val = line.split(": ", 1)
                    info[key.strip()] = val.strip()
            return info
        except:
            return None

    def update_camera(self):
        if not self.running:
            return

        ret, frame = self.cap.read()
        if ret:
            # Detect QR Code
            data, bbox, _ = self.detector.detectAndDecode(frame)

            # Draw box if detected
            if bbox is not None and len(bbox) > 0:
                # Convert bbox to int for drawing
                bbox = bbox.astype(int)
                for i in range(len(bbox)):
                    pt1 = tuple(bbox[i][0])
                    pt2 = tuple(bbox[(i+1) % len(bbox)][0])
                    cv2.line(frame, pt1, pt2, (0, 255, 0), 2)
                
                if data:
                    self.process_scan(data)

            # Convert to Tkinter compatible image
            cv2image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
            img = Image.fromarray(cv2image)
            
            # Resize image to fit the frame while maintaining aspect ratio
            frame_width = self.camera_frame.winfo_width()
            frame_height = self.camera_frame.winfo_height()
            
            # Avoid division by zero on startup
            if frame_width > 1 and frame_height > 1:
                img_ratio = img.width / img.height
                frame_ratio = frame_width / frame_height
                
                if img_ratio > frame_ratio:
                    new_width = frame_width
                    new_height = int(new_width / img_ratio)
                else:
                    new_height = frame_height
                    new_width = int(new_height * img_ratio)
                    
                img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            imgtk = ImageTk.PhotoImage(image=img)
            self.camera_label.configure(image=imgtk, text="")
            self.camera_label.image = imgtk  # Keep reference

        self.after(10, self.update_camera)

    def process_scan(self, data):
        current_time = time.time()
        
        # Debounce to prevent rapid firing on same frame
        if current_time - self.last_scan_time < 2.0:
            return

        parsed = self.parse_qr_data(data)
        if not parsed or 'ID' not in parsed:
            # Invalid QR
            return

        student_id = parsed['ID']
        
        if student_id in self.scanned_ids:
            self.update_status("ALREADY SCANNED!", "#E74C3C") # Red
            self.last_scan_time = current_time
            # Optional: Play error sound
        else:
            # New Scan
            self.scanned_ids.add(student_id)
            self.last_scan_time = current_time
            
            # Update UI
            self.update_status("SCAN SUCCESS", "#2ECC71") # Green
            
            name = parsed.get('Name', 'Unknown')
            branch = parsed.get('Branch', 'Unknown')
            
            self.lbl_name.configure(text=name)
            self.lbl_id.configure(text=student_id)
            self.lbl_branch.configure(text=branch)
            
            # Add to history
            self.history_textbox.configure(state="normal")
            self.history_textbox.insert("0.0", f"✔ {name} ({branch})\n")
            self.history_textbox.configure(state="disabled")

    def on_close(self):
        self.running = False
        if self.cap.isOpened():
            self.cap.release()
        self.destroy()

if __name__ == "__main__":
    app = QRScannerApp()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()

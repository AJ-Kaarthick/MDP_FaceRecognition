import customtkinter as ctk
import cv2
from PIL import Image, ImageTk
from .camera import CameraManager
from .logic import SecuritySystem

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.geometry("1100x800")
        self.title("Smart Security System")
        ctk.set_appearance_mode("Light")
        
        self.camera = CameraManager()
        self.logic = SecuritySystem()
        
        # Grid Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=300, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        self.logo_label = ctk.CTkLabel(self.sidebar, text="SECURE\nVISION", font=ctk.CTkFont(size=28, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 10))
        
        self.status_label = ctk.CTkLabel(self.sidebar, text="Status: IDLE", font=ctk.CTkFont(size=16))
        self.status_label.grid(row=1, column=0, padx=20, pady=10)
        
        self.attempts_label = ctk.CTkLabel(self.sidebar, text="Attempts: 5", text_color="green", font=ctk.CTkFont(size=18, weight="bold"))
        self.attempts_label.grid(row=2, column=0, padx=20, pady=10)
        
        self.users_label = ctk.CTkLabel(self.sidebar, text=f"Users: {self.logic.user_manager.get_user_count()}", font=ctk.CTkFont(size=14))
        self.users_label.grid(row=3, column=0, padx=20, pady=10)
        
        self.instructions = ctk.CTkLabel(self.sidebar, text="STEPS:\n1. Register User [R]\n2. Add Gestures [G]\n3. Verify Access\n(Face + Gesture)\n\n[ESC] to Quit", justify="left", font=ctk.CTkFont(size=14))
        self.instructions.grid(row=4, column=0, padx=20, pady=30, sticky="w")

        # Main Video Area
        self.video_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.video_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        self.video_label = ctk.CTkLabel(self.video_frame, text="")
        self.video_label.pack(fill="both", expand=True)

        # Start Systems
        self.camera.start()
        
        # Key Bindings
        self.bind('<Key>', self.on_key)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Main Loop
        self.update_feed()

    def on_key(self, event):
        key = event.keysym.lower()
        if key == "escape":
            self.on_close()
            return
            
        action = self.logic.handle_input(key)
        
        if action == "quit":
            self.on_close()
        elif action == "input_name":
            # Use CTkInputDialog
            dialog = ctk.CTkInputDialog(text="Enter User Name:", title="Registration")
            name = dialog.get_input()
            if name:
                self.logic.start_registration_capture(name)
            else:
                self.logic.state = "IDLE"

    def update_feed(self):
        frame = self.camera.get_frame()
        if frame is not None:
            # 1. Update Logic
            frame = self.logic.update(frame)
            
            # 2. Update Sidebar Stats
            self.status_label.configure(text=f"Status: {self.logic.state}")
            color = "#008000" if self.logic.attempts > 2 else "#b30000" # Darker green/red for light mode
            self.attempts_label.configure(text=f"Attempts: {self.logic.attempts}", text_color=color)
            self.users_label.configure(text=f"Users: {self.logic.user_manager.get_user_count()}")
            
            # 3. Draw HUD on Frame (OpenCV)
            h, w, _ = frame.shape
            
            # Main Message
            msg_color = (0, 180, 0) # Darker Green
            if self.logic.state == "LOCKED" or self.logic.state == "ACCESS_DENIED":
                msg_color = (0, 0, 180) # Darker Red
            elif self.logic.state == "VERIFIED":
                msg_color = (0, 180, 180) # Darker Cyan/Yellow (BGR)
                
            cv2.putText(frame, self.logic.message, (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.2, msg_color, 3)
            # Sub message in Black as requested
            cv2.putText(frame, self.logic.sub_message, (30, 90), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
            
            # 4. Convert to Tkinter Image
            img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img_pil = Image.fromarray(img)
            
            # Resize logic to fit window
            display_w = self.video_label.winfo_width()
            display_h = self.video_label.winfo_height()
            
            # Only resize if dimensions are valid and reasonable
            if display_w > 50 and display_h > 50:
                 img_pil = img_pil.resize((display_w, display_h), Image.Resampling.LANCZOS)
            
            imgtk = ImageTk.PhotoImage(image=img_pil)
            self.video_label.configure(image=imgtk)
            self.video_label.imgtk = imgtk # Keep ref
            
        self.after(30, self.update_feed)

    def on_close(self):
        self.camera.stop()
        self.destroy()

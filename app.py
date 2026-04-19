import customtkinter as ctk
import cv2
import threading
import time
import os
from PIL import Image, ImageTk
from tkinter import filedialog, messagebox

from core.detector import SignDetector
from core.reflectivity import ReflectivityAnalyzer as RA
from core.gps import GPSProvider
from utils.file_manager import FileManager as FM

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("SafeSight AI — Traffic Sign Visibility Analyzer")
        self.geometry("1320x800")
        self.minsize(1100, 700)

        self.cap = None
        self.running = False
        self.detector = None
        self.gps = GPSProvider()
        self.logger = None
        self.csv_dir = "./logs"
        self.img_dir = "./detections"
        self.save_img = False
        self._frame = None
        self._det_count = 0
        self._fps = 0.0
        
        # Workspace internals
        self.master_workspace_dir = None
        
        # New Video writer internals
        self.out_video_path = None
        self.video_writer = None
        self.total_frames = 0
        self.processed_frames = 0
        self.is_live_recording = False
        self.vid_fps = 30.0
        
        # Image processing internals
        self.image_list = []
        self.current_img_idx = 0
        
        self._img_save_times = {}
        self._track_cache = {}  

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._quit)

    def _build_ui(self):
        # Strict 2-column layout: Left Sidebar
        sb = ctk.CTkFrame(self, width=280, corner_radius=0, fg_color="#000000")
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)
        self.sb = sb

        # Title Area
        # Removed the emoji from the text natively to prevent visual centering shift
        ctk.CTkLabel(sb, text="SafeSight AI", font=("Georgia", 32, "bold"), text_color="#ffffff").pack(pady=(28, 2))
        ctk.CTkLabel(sb, text="Traffic Sign Visibility Analyzer", font=("Segoe UI", 14), text_color="#cccccc").pack(pady=(0, 25))

        self._divider(sb)
        self._header(sb, "SELECT MODE")

        self.btn_vid = ctk.CTkButton(sb, text="🎬  Process Video File", command=self._on_video, height=44, font=("Segoe UI", 14, "bold"), fg_color="#171717", hover_color="#262626", corner_radius=10)
        self.btn_vid.pack(padx=24, pady=(12, 6), fill="x")

        self.btn_img = ctk.CTkButton(sb, text="🖼  Process Images File", command=self._on_image, height=44, font=("Segoe UI", 14, "bold"), fg_color="#171717", hover_color="#262626", corner_radius=10)
        self.btn_img.pack(padx=24, pady=(0, 6), fill="x")

        self.btn_live = ctk.CTkButton(sb, text="📷  Live Camera Feed", command=self._on_live, height=44, font=("Segoe UI", 14, "bold"), fg_color="#171717", hover_color="#262626", corner_radius=10)
        self.btn_live.pack(padx=24, pady=(0, 6), fill="x")

        self._divider(sb)
        self._header(sb, "OUTPUT SETTINGS")

        self.lbl_csv = ctk.CTkLabel(sb, text=f"📄  CSV Folder: {self.csv_dir}", font=("Segoe UI", 11), text_color="#a3a3a3", wraplength=230, justify="left")
        self.lbl_csv.pack(padx=24, pady=(8, 4), anchor="w")

        self._divider(sb)
        self._header(sb, "IMAGE CAPTURE")

        self.sw_var = ctk.BooleanVar(value=False)
        self.sw = ctk.CTkSwitch(sb, text="Save Detected Images", variable=self.sw_var, command=self._on_save_toggle, font=("Segoe UI", 13), progress_color="#ff1a1a")
        self.sw.pack(padx=24, pady=(8, 4), anchor="w")

        self.lbl_img = ctk.CTkLabel(sb, text=f"🖼  /detections", font=("Segoe UI", 11), text_color="#a3a3a3", wraplength=230, justify="left")
        self.lbl_img.pack(padx=24, pady=(0, 4), anchor="w")

        self._divider(sb)

        self.btn_stop = ctk.CTkButton(sb, text="⏹ Start Processing", command=self._stop, height=44, font=("Segoe UI", 14, "bold"), fg_color="#b30000", hover_color="#cc0000", corner_radius=10, state="disabled")
        self.btn_stop.pack(padx=24, pady=(20, 6), fill="x")

        legend = ctk.CTkFrame(sb, fg_color="transparent")
        legend.pack(pady=(15, 0), padx=24, fill="x")
        ctk.CTkLabel(legend, text="● Poor", font=("Segoe UI", 11, "bold"), text_color="#ff4444").pack(side="left", padx=(0, 8))
        ctk.CTkLabel(legend, text="● Moderate", font=("Segoe UI", 11, "bold"), text_color="#ffff44").pack(side="left", padx=(0, 8))
        ctk.CTkLabel(legend, text="● Good", font=("Segoe UI", 11, "bold"), text_color="#44ff44").pack(side="left")

        # Strict 2-column layout: Right Main Area
        main = ctk.CTkFrame(self, corner_radius=0, fg_color="#0a0a0a")
        main.pack(side="right", fill="both", expand=True)
        self.main = main

        self.video_lbl = ctk.CTkLabel(main, text="Select a mode to begin\n\n🎬 Video   ·   📷 Camera   ·   🖼 Images", font=("Segoe UI", 24), text_color="#3f3f46")
        self.video_lbl.pack(fill="both", expand=True)

        self.btn_prev = ctk.CTkButton(main, text="<", width=40, height=40, font=("Segoe UI", 20, "bold"), fg_color="#121212", hover_color="#262626", corner_radius=20, command=self._prev_img)
        self.btn_next = ctk.CTkButton(main, text=">", width=40, height=40, font=("Segoe UI", 20, "bold"), fg_color="#121212", hover_color="#262626", corner_radius=20, command=self._next_img)

        stats = ctk.CTkFrame(main, height=38, corner_radius=0, fg_color="#000000")
        stats.pack(fill="x", side="bottom")
        stats.pack_propagate(False)

        self.lbl_stats = ctk.CTkLabel(stats, text="Detections: 0   ·   FPS: --", font=("Segoe UI", 12), text_color="#a3a3a3")
        self.lbl_stats.pack(side="left", padx=16)

        self.lbl_gps_bar = ctk.CTkLabel(stats, text="📍 GPS: —", font=("Segoe UI", 12), text_color="#a3a3a3")
        self.lbl_gps_bar.pack(side="right", padx=16)
        
        # Placed directly inside bottom status bar to maximize video visibility
        self.center_stats = ctk.CTkFrame(stats, fg_color="transparent")
        self.center_stats.place(relx=0.5, rely=0.5, anchor="center")

        self.box_left = ctk.CTkFrame(self.center_stats, fg_color="#121212", border_width=1, border_color="#262626", corner_radius=6, height=28)
        self.box_left.pack(side="left", padx=5)

        self.lbl_progress = ctk.CTkLabel(self.box_left, text="Select Option to Start Processing", font=("Segoe UI", 12, "bold"), text_color="#a3a3a3")
        self.lbl_progress.pack(side="left", padx=(10, 10), pady=2)
        
        self.progress_bar = ctk.CTkProgressBar(self.box_left, width=120, height=6, corner_radius=3, progress_color="#ffffff", fg_color="#262626")
        self.progress_bar.set(0)

        self.btn_get_vid = ctk.CTkButton(self.center_stats, text="▶ Get Processed Video", font=("Segoe UI", 12, "bold"), 
                                         fg_color="#121212", hover_color="#262626", text_color="#ffffff", border_width=1, border_color="#262626", corner_radius=6, height=28, command=self._play_processed, state="disabled")
        self.btn_get_vid.pack(side="left", padx=5)

    def _header(self, parent, text):
        ctk.CTkLabel(parent, text=text, font=("Segoe UI", 11, "bold"), text_color="#ffffff").pack(anchor="w", padx=24, pady=(4, 0))

    def _divider(self, parent):
        ctk.CTkFrame(parent, height=1, fg_color="#262626").pack(fill="x", padx=20, pady=12)

    def _ensure_workspace(self):
        if not self.master_workspace_dir:
            from tkinter import messagebox
            messagebox.showinfo("Workspace Setup", "Please select a Master Workspace directory. All future runs will be saved inside sequential folders here automatically.")
            d = filedialog.askdirectory(title="Select Master Workspace Directory")
            if not d:
                return False
            self.master_workspace_dir = d

        idx = 1
        while True:
            ws_name = "workspace" if idx == 1 else f"workspace({idx})"
            ws_path = os.path.join(self.master_workspace_dir, ws_name)
            if not os.path.exists(ws_path):
                break
            idx += 1
            
        os.makedirs(ws_path)
        self.csv_dir = os.path.join(ws_path, "csv")
        os.makedirs(self.csv_dir)
        
        self.img_dir = os.path.join(ws_path, "detections")
        if self.save_img:
            os.makedirs(self.img_dir)
            
        out_dir = os.path.join(ws_path, "output")
        os.makedirs(out_dir)
        self.out_video_path = os.path.join(out_dir, "processed_video.mp4")

        self.lbl_csv.configure(text=f"📄  CSV Folder: {self.csv_dir}")
        self.lbl_img.configure(text=f"🖼  Detections: {self.img_dir}")
        
        from core.logger import CSVLogger
        csv_path = FM.csv_path(self.csv_dir)
        self.logger = CSVLogger(csv_path)
        return True

    def _on_save_toggle(self):
        self.save_img = self.sw_var.get()
        if self.save_img and self.master_workspace_dir:
            FM.ensure(self.img_dir)

    def _on_video(self):
        path = filedialog.askopenfilename(
            title="Select Source Video File",
            filetypes=[("Video", "*.mp4 *.avi *.mov *.mkv *.wmv"), ("All", "*.*")])
        if not path:
            return
            
        if not self._ensure_workspace():
            return

        self.update()
        self._init_detector()
        self.cap = cv2.VideoCapture(path)
        if not self.cap.isOpened():
            messagebox.showerror("Error", "Cannot open video file.")
            return
            
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.processed_frames = 0
        self.lbl_progress.configure(text="Processing... 0%", text_color="#a3a3a3")
        self.progress_bar.set(0)
        self.lbl_progress.pack_forget()
        self.progress_bar.pack_forget()
        self.lbl_progress.pack(side="left", padx=(10, 5), pady=2)
        self.progress_bar.pack(side="left", padx=(0, 10))

        # Video Writer init
        fps = self.cap.get(cv2.CAP_PROP_FPS) or 30.0
        fmt = cv2.VideoWriter_fourcc(*'mp4v')
        self.video_writer = cv2.VideoWriter(self.out_video_path, fmt, fps, (1280, 720))
        self.vid_fps = fps
        self.is_live_recording = False

        self._start()

    def _on_live(self):
        cam_ok = messagebox.askyesno("Camera Permission", "SafeSight AI needs access to your Camera for live processing.\n\nAllow Camera access?")
        if not cam_ok:
            return
            
        self.location_allowed = messagebox.askyesno("Location Permission", "Do you want to enable accurate GPS Tracking to log coordinates alongside detections?")
            
        if not self._ensure_workspace():
            return
            
        self.update()
        self._init_detector()
        # Use DirectShow backend and set buffersize to 1 to prevent queue stacking (real-time sync)
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.total_frames = 0
        self.processed_frames = 0
        if not self.cap.isOpened():
            messagebox.showerror("Error", "Cannot access camera.\nCheck permissions or device.")
            return
            
        self.lbl_progress.configure(text="●  Live Processing...", text_color="#ff4444")
        self.progress_bar.set(0)
        self.lbl_progress.pack_forget()
        self.progress_bar.pack_forget()
        self.lbl_progress.pack(side="left", padx=10, pady=2)

        # Video Writer init
        fps = self.cap.get(cv2.CAP_PROP_FPS)
        if not fps or fps <= 0 or fps >= 120:
            fps = 30.0
        fmt = cv2.VideoWriter_fourcc(*'mp4v')
        self.video_writer = cv2.VideoWriter(self.out_video_path, fmt, fps, (1280, 720))
        self.vid_fps = fps
        self.is_live_recording = True

        if self.location_allowed:
            self.gps.start()
        self._start()

    def _init_detector(self):
        if not self.detector:
            try:
                self.detector = SignDetector()
            except Exception as e:
                messagebox.showerror("Model Error", f"Failed to load YOLOv8:\n{e}")
                raise

    def _start(self):
        self.running = True
        self._img_save_times = {}
        self.btn_vid.configure(state="disabled")
        self.btn_live.configure(state="disabled")
        self.btn_img.configure(state="disabled")
        self.btn_stop.configure(text="⏹ Stop Processing", state="normal")
        self.btn_get_vid.configure(state="disabled")
        threading.Thread(target=self._process_loop, daemon=True).start()
        self._update_display()

    def _process_loop(self):
        prev_t = time.time()
        start_live_time = None
        frames_written = 0
        while self.running:
            ret, frame = self.cap.read()
            if not ret:
                self.running = False
                break
                
            if getattr(self, 'is_live_recording', False) and start_live_time is None:
                start_live_time = time.time()
                
            self.processed_frames += 1

            # Frame Preprocessing
            frame = cv2.resize(frame, (1280, 720))
            
            # Apply CLAHE contrast enhancement
            lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            cl = clahe.apply(l)
            limg = cv2.merge((cl, a, b))
            contrast_frame = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)

            dets = self.detector.detect(contrast_frame)
            lat, lon = self.gps.coords()
            
            current_track_ids = set()
            for d in dets:
                tid = d['track_id']
                x1, y1, x2, y2 = d['bbox']
                roi = contrast_frame[y1:y2, x1:x2]
                if roi.size == 0:
                    continue
                    
                area = (x2 - x1) * (y2 - y1)
                
                if tid != -1:
                    sc = RA.score(roi)
                    
                    if tid in self._track_cache:
                        cached = self._track_cache[tid]
                        prev_sc = cached.get('sc', 0)
                        bad_age = cached.get('bad_age', 0)
                        good_age = cached.get('good_age', 0)
                        locked_good = cached.get('locked_good', False)

                        # Standard gentle smoothing to prevent huge 1-frame spikes
                        sc = round((sc * 0.4) + (prev_sc * 0.6), 3)

                        if locked_good:
                            sc = prev_sc
                            cls = 'Good'
                        else:
                            cls = RA.classify(sc)
                            if cls == 'Good':
                                good_age += 1
                                bad_age = 0
                                if good_age >= 15:
                                    locked_good = True
                            elif cls in ('Poor', 'Moderate'):
                                bad_age += 1
                                good_age = 0
                    else:
                        cls = RA.classify(sc)
                        bad_age = 1 if cls in ('Poor', 'Moderate') else 0
                        good_age = 1 if cls == 'Good' else 0
                        locked_good = False

                    if locked_good:
                        display_cls = 'Good'
                    else:
                        display_cls = cls if bad_age >= 10 else 'Good'

                    self._track_cache[tid] = {
                        'd': d, 'sc': sc, 'cls': cls, 'display_cls': display_cls,
                        'missed': 0, 'bad_age': bad_age, 'good_age': good_age, 'locked_good': locked_good
                    }
                    current_track_ids.add(tid)

            results = []
            # Gather tracked results, decay those missed
            for tid, cached in list(self._track_cache.items()):
                if tid not in current_track_ids:
                    cached['missed'] += 1
                    if cached['missed'] > 5:  # maintain drop for 5 frames
                        del self._track_cache[tid]
                        continue
                results.append((cached['d'], cached['sc'], cached['display_cls']))
                
            # Bring in untracked items
            for d in dets:
                if d['track_id'] == -1:
                    x1, y1, x2, y2 = d['bbox']
                    roi = contrast_frame[y1:y2, x1:x2]
                    if roi.size > 0:
                        sc = RA.score(roi)
                        results.append((d, sc, 'Good'))

            for d, sc, cls in results:
                x1, y1, x2, y2 = d['bbox']
                clr = RA.color(cls)

                cv2.rectangle(frame, (x1, y1), (x2, y2), clr, 2)

                txt = f"{d['label']} | {cls}: {sc}"
                (tw, th), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, 0.50, 2)
                lbl_y = y1 - 10
                if lbl_y < th + 8:
                    lbl_y = y2 + th + 10

                cv2.rectangle(frame, (x1, lbl_y - th - 6),
                              (x1 + tw + 10, lbl_y + 6), clr, -1)
                cv2.putText(frame, txt, (x1 + 5, lbl_y),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 0, 0), 2)

                if cls in ('Poor', 'Moderate'):
                    if self.is_live_recording and getattr(self, 'location_allowed', False):
                        gps_t = f"GPS: {lat},{lon}"
                        cv2.putText(frame, gps_t, (x1, lbl_y + 20),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.38, clr, 1)

            h, w = frame.shape[:2]
            if self.is_live_recording and getattr(self, 'location_allowed', False):
                gps_disp = f"GPS: {lat}, {lon}"
                (gtw, gth), _ = cv2.getTextSize(gps_disp, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                gx = w - gtw - 18
                cv2.rectangle(frame, (gx - 8, 6), (w - 8, 36), (30, 30, 50), -1)
                cv2.putText(frame, gps_disp, (gx, 28),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            for d, sc, cls in results:
                if cls in ('Poor', 'Moderate'):
                    if self.logger:
                        self.logger.log(d['label'], sc, lat, lon)

                    if self.save_img:
                        now_t = time.time()
                        k = d['label']
                        if k not in self._img_save_times or (now_t - self._img_save_times[k]) >= 1.0:
                            self._img_save_times[k] = now_t
                            p = FM.img_path(d['label'], lat, lon, self.img_dir)
                            cv2.imwrite(p, frame)

            now = time.time()
            self._fps = 1.0 / max(now - prev_t, 0.001)
            prev_t = now
            self._frame = frame
            self._det_count = len(results)
            
            if self.video_writer:
                if getattr(self, 'is_live_recording', False) and start_live_time is not None:
                    elapsed = time.time() - start_live_time
                    expected = int(elapsed * self.vid_fps)
                    if frames_written == 0 and expected == 0:
                        expected = 1
                    while frames_written < expected:
                        self.video_writer.write(frame)
                        frames_written += 1
                else:
                    self.video_writer.write(frame)

    def _update_display(self):
        if self._frame is not None:
            f = self._frame.copy()
            dw = max(self.main.winfo_width(), 640)
            dh = max(self.main.winfo_height() - 42, 400)
            fh, fw = f.shape[:2]
            scale = min(dw / fw, dh / fh)
            nw, nh = int(fw * scale), int(fh * scale)
            f = cv2.resize(f, (nw, nh))

            rgb = cv2.cvtColor(f, cv2.COLOR_BGR2RGB)
            img = Image.fromarray(rgb)
            photo = ImageTk.PhotoImage(img)
            self.video_lbl.configure(image=photo, text="")
            self.video_lbl._photo = photo

            self.lbl_stats.configure(text=f"Detections: {self._det_count}   ·   FPS: {self._fps:.1f}")
            if self.is_live_recording and getattr(self, 'location_allowed', False):
                lat, lon = self.gps.coords()
                self.lbl_gps_bar.configure(text=f"📍 GPS: {lat}, {lon}")
                
                if not self.gps.gps_enabled:
                    if not getattr(self, '_gps_warning_shown', False):
                        self._gps_warning_shown = True
                        self._show_gps_warning()
                else:
                    self._gps_warning_shown = False
            else:
                self.lbl_gps_bar.configure(text="")
            
            if self.total_frames > 0:
                pct = int((self.processed_frames / self.total_frames) * 100)
                self.progress_bar.set(self.processed_frames / self.total_frames)
                self.lbl_progress.configure(text=f"Processing... {pct}%")
            else:
                dot = "●" if (int(time.time() * 2) % 2) == 0 else "○"
                self.lbl_progress.configure(text=f"{dot}  Live Processing...")

        if self.running:
            self.after(30, self._update_display)
        else:
            self._cleanup()

    def _on_image(self):
        popup = ctk.CTkToplevel(self)
        popup.title("Select Image Mode")
        popup.geometry("340x160")
        popup.resizable(False, False)
        popup.transient(self)
        popup.grab_set()

        ctk.CTkLabel(popup, text="What would you like to process?", font=("Segoe UI", 16, "bold")).pack(pady=(20, 15))
        
        btn_frame = ctk.CTkFrame(popup, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20)
        
        def _single():
            popup.destroy()
            self._handle_single_image()
            
        def _multiple():
            popup.destroy()
            self._handle_multiple_images()
            
        ctk.CTkButton(btn_frame, text="Single Image", command=_single, height=36, font=("Segoe UI", 13, "bold"), fg_color="#171717", hover_color="#262626").pack(side="left", padx=5, expand=True)
        ctk.CTkButton(btn_frame, text="Multiple Images", command=_multiple, height=36, font=("Segoe UI", 13, "bold"), fg_color="#171717", hover_color="#262626").pack(side="right", padx=5, expand=True)

    def _handle_single_image(self):
        path = filedialog.askopenfilename(title="Select Source Image", filetypes=[("Image", "*.jpg *.jpeg *.png *.bmp")])
        if not path:
            return
        dest_dir = filedialog.askdirectory(title="Select Destination to Save Processed Image")
        if not dest_dir:
            return
            
        self.update()
        self._init_detector()
        
        self.btn_prev.place_forget()
        self.btn_next.place_forget()
        self.image_list = []
        
        fname = os.path.basename(path)
        dest_path = os.path.join(dest_dir, fname)
        
        self.lbl_progress.configure(text="Processing Image...", text_color="#a3a3a3")
        self.lbl_progress.pack_forget()
        self.progress_bar.pack_forget()
        self.lbl_progress.pack(side="left", padx=(10, 10), pady=2)
        
        self.update()
        
        proc_img, dets_count = self._process_single_frame_no_tracking(path)
        if proc_img is not None:
            cv2.imwrite(dest_path, proc_img)
            self._display_still_image(proc_img)
            self.lbl_stats.configure(text=f"Detections: {dets_count}   ·   FPS: --")
            self.lbl_gps_bar.configure(text="")
            self.lbl_progress.configure(text="Processing complete. Image saved.")
        else:
            messagebox.showerror("Error", "Could not load the image.")

    def _handle_multiple_images(self):
        src_dir = filedialog.askdirectory(title="Select Source Folder")
        if not src_dir:
            return
        dest_parent = filedialog.askdirectory(title="Select Destination Folder")
        if not dest_parent:
            return
            
        self.update()
        self._init_detector()
        self.btn_prev.place_forget()
        self.btn_next.place_forget()
        
        valid_exts = ('.jpg', '.jpeg', '.png', '.bmp')
        files = [os.path.join(src_dir, f) for f in os.listdir(src_dir) if f.lower().endswith(valid_exts)]
        if not files:
            messagebox.showinfo("Info", "No valid images found in the selected folder.")
            return
            
        dest_dir = os.path.join(dest_parent, "processed_images")
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
            
        self.lbl_progress.configure(text="Processing... 0%")
        self.progress_bar.set(0)
        self.lbl_progress.pack_forget()
        self.progress_bar.pack_forget()
        self.lbl_progress.pack(side="left", padx=(10, 5), pady=2)
        self.progress_bar.pack(side="left", padx=(0, 10))
        
        self.image_list = []
        self.current_img_idx = 0
        self.total_frames = len(files)
        
        self.btn_vid.configure(state="disabled")
        self.btn_live.configure(state="disabled")
        self.btn_img.configure(state="disabled")
        self.btn_stop.configure(text="⏹ Stop Processing", state="normal")
        
        def _process_task():
            self.running = True
            for idx, path in enumerate(files):
                if not self.running:
                    break
                proc, _ = self._process_single_frame_no_tracking(path)
                if proc is not None:
                    fname = os.path.basename(path)
                    out_path = os.path.join(dest_dir, fname)
                    cv2.imwrite(out_path, proc)
                    self.image_list.append(out_path)
                
                pct = int(((idx+1) / self.total_frames) * 100)
                self.progress_bar.set((idx+1) / self.total_frames)
                self.lbl_progress.configure(text=f"Processing... {pct}%")
                
            self.running = False
            self.lbl_progress.configure(text=f"Processing complete. {len(self.image_list)} images saved.")
            self.progress_bar.set(1.0)
            
            self.btn_vid.configure(state="normal")
            self.btn_live.configure(state="normal")
            self.btn_img.configure(state="normal")
            self.btn_stop.configure(text="⏹ Start Processing", state="disabled")
            
            if self.image_list:
                self.after(0, self._setup_multiple_viewer)
                
        threading.Thread(target=_process_task, daemon=True).start()

    def _setup_multiple_viewer(self):
        if not self.image_list:
            return
        self.current_img_idx = 0
        self._load_current_list_image()
        self.btn_prev.place(relx=0.04, rely=0.5, anchor="center")
        self.btn_next.place(relx=0.96, rely=0.5, anchor="center")
        
    def _load_current_list_image(self):
        if not self.image_list:
            return
        path = self.image_list[self.current_img_idx]
        img = cv2.imread(path)
        if img is not None:
            self._display_still_image(img)
            self.lbl_stats.configure(text=f"Image {self.current_img_idx + 1} of {len(self.image_list)}")
            self.lbl_gps_bar.configure(text="")

    def _prev_img(self):
        if self.image_list and self.current_img_idx > 0:
            self.current_img_idx -= 1
            self._load_current_list_image()

    def _next_img(self):
        if self.image_list and self.current_img_idx < len(self.image_list) - 1:
            self.current_img_idx += 1
            self._load_current_list_image()

    def _display_still_image(self, f):
        f = f.copy()
        dw = max(self.main.winfo_width(), 640)
        dh = max(self.main.winfo_height() - 42, 400)
        fh, fw = f.shape[:2]
        scale = min(dw / fw, dh / fh)
        nw, nh = int(fw * scale), int(fh * scale)
        f = cv2.resize(f, (nw, nh))

        rgb = cv2.cvtColor(f, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(rgb)
        photo = ImageTk.PhotoImage(img)
        self.video_lbl.configure(image=photo, text="")
        self.video_lbl._photo = photo

    def _process_single_frame_no_tracking(self, path):
        frame = cv2.imread(path)
        if frame is None:
            return None, 0
            
        frame = cv2.resize(frame, (1280, 720))
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        cl = clahe.apply(l)
        limg = cv2.merge((cl, a, b))
        contrast_frame = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
        
        dets = self.detector.detect(contrast_frame)
        count = 0
        for d in dets:
            x1, y1, x2, y2 = d['bbox']
            roi = contrast_frame[y1:y2, x1:x2]
            if roi.size == 0:
                continue
            sc = RA.score(roi)
            cls = RA.classify(sc)
            clr = RA.color(cls)
            
            cv2.rectangle(frame, (x1, y1), (x2, y2), clr, 2)
            txt = f"{d['label']} | {cls}: {sc}"
            (tw, th), _ = cv2.getTextSize(txt, cv2.FONT_HERSHEY_SIMPLEX, 0.50, 2)
            lbl_y = y1 - 10
            if lbl_y < th + 8:
                lbl_y = y2 + th + 10

            cv2.rectangle(frame, (x1, lbl_y - th - 6),
                          (x1 + tw + 10, lbl_y + 6), clr, -1)
            cv2.putText(frame, txt, (x1 + 5, lbl_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.50, (0, 0, 0), 2)
            count += 1
            
        return frame, count

    def _stop(self):
        self.running = False
        self.gps.stop()

    def _cleanup(self):
        if self.cap:
            self.cap.release()
            self.cap = None
        if self.video_writer:
            self.video_writer.release()
            self.video_writer = None
            
        self.btn_vid.configure(state="normal")
        self.btn_live.configure(state="normal")
        self.btn_img.configure(state="normal")
        self.btn_stop.configure(text="⏹ Start Processing", state="disabled")
        
        if self.out_video_path and os.path.exists(self.out_video_path):
            self.btn_get_vid.configure(state="normal")
            if self.total_frames > 0:
                self.lbl_progress.configure(text="Processing... 100% (Completed)", text_color="#a3a3a3")
                self.progress_bar.set(1.0)
            else:
                self.lbl_progress.configure(text="Live Video Saved to Workspace", text_color="#a3a3a3")
                self.progress_bar.set(1.0)
                
    def _play_processed(self):
        if self.out_video_path and os.path.exists(self.out_video_path):
            try:
                os.startfile(self.out_video_path)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to play video: {e}")

    def _show_gps_warning(self):
        if hasattr(self, 'gps_popup') and self.gps_popup is not None and self.gps_popup.winfo_exists():
            return
            
        self.gps_popup = ctk.CTkToplevel(self)
        self.gps_popup.title("Location Disabled")
        self.gps_popup.geometry("380x180")
        self.gps_popup.resizable(False, False)
        self.gps_popup.attributes("-topmost", True)
        
        ctk.CTkLabel(self.gps_popup, text="GPS / Location is Disabled", font=("Segoe UI", 16, "bold"), text_color="#ff4444").pack(pady=(20, 10))
        ctk.CTkLabel(self.gps_popup, text="Please turn on GPS/Location in your laptop settings\nto receive accurate coordinates.", font=("Segoe UI", 13)).pack(padx=20, pady=(0, 20))
        
        def _close():
            self.gps_popup.destroy()
            
        ctk.CTkButton(self.gps_popup, text="OK", command=_close, width=100, fg_color="#171717", hover_color="#262626").pack()

    def _quit(self):
        self.running = False
        self.gps.stop()
        if self.cap:
            self.cap.release()
        self.destroy()


if __name__ == "__main__":
    app = App()
    app.mainloop()
